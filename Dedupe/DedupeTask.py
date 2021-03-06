# This file is part of VertNet: https://github.com/VertNet/dedupe
#
# VertNet is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# VertNet is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with VertNet.  If not, see: http://www.gnu.org/licenses

"""Report API.

This method generates a report informing of potential duplicates in the
provided data set. It does not add any flagging field nor deletes the potential
duplicated records.

Usage:
    Send a POST request to the handler providing the set of records in the body
    of the request. Records must be provided in JSON format.

"""

import os
import csv
import json
import hashlib
import logging
from StringIO import StringIO
from datetime import datetime

from google.appengine.api import namespace_manager, memcache, mail, taskqueue
import cloudstorage as gcs
import webapp2

from config import *

LAST_UPDATED = '2016-08-05T13:15:56+CEST'
API_VERSION = 'search 2016-08-05T13:15:56+CEST'

IS_DEV = os.environ.get('SERVER_SOFTWARE', '').startswith('Development')
if IS_DEV:
    QUEUE_NAME = 'default'
else:
    QUEUE_NAME = 'apitracker'


class DedupeTask(webapp2.RequestHandler):
    """
Instance attributes:

- action: Type of action to perform on the file
- cityLatLong: Coordinates of the city of the request
- col: position of the "recordedBy" field in the file
- content_type: Content-Type header of the request
- country: Code of the country of the request
- dat: position of the "eventDate" field in the file
- delimiter: field delimiter, accordint to content_type variable
- dupe_ref: position of the original record (for flagging)
- duplicate_ids: list of values of the "id" field in duplicate records,
                 for strict duplicates
- duplicate_order: position of the original-duplicate pair of records,
                 for strict duplicates
- duplicates: List with types of duplicates to find (strict, partial, all...)
- email: email address to send notifications to
- extension: file extension (.txt for tab-delimited, .csv for comma-separated)
- file: file-object sent by the user in the POST body
- file_name: full name of the Google Cloud Storage object (bucket + file path)
- file_url: full URL to allow external access to the Google Cloud Storage file
- headers: field names of the sent file
- headers_lower: lowercase version of self.headers
- id_field: field used as "id" for the record
- idx: position of the id_field
- is_dupe: keep track of whether the current record is not a duplicate (0),
           is a strict duplicate (1) or a partial duplicate (2)
- loc: position of the "locality" field in the file
- partial_duplicate_ids: list of values of the "id" field in duplicate records,
                         for partial duplicates
- partial_duplicates: number of partial duplicates found
- partial_duplicates_order: position of the original-duplicate pair of records
                            for partial duplicates
- previous_namespace: Default namespace
- reader: csv-reader object
- records: number of records processed, also position indicator
- report: final report to be delivered to the user
- request_namespace: Namespace for the current request
- sci: position of the "scientificName" field in the file
- strict_duplicates: number of strict duplicates found
- user_agent: User-Agent header of the request
- warnings: list conaining all warnings generated during the process
"""

    def _err(self, err_code=500, err_message="", err_explain=""):
        """Return a custom error message along with the error code."""
        self.error(err_code)
        resp = {
            "status": "error",
            "error": err_message,
            "message": err_explain
        }
        logging.error(err_message)
        logging.error(err_explain)
        self.response.headers['Content-Type'] = "application/json"
        self.response.write(json.dumps(resp)+"\n")

        # Send email to admin with details
        mail.send_mail(
            sender=EMAIL_SENDER,
            to=ADMIN,
            subject="[VN-dedupe] Dedupe error",
            body="""Hey,

Something went wrong with a deduplication request. Here are the details:

File UUID:     %s
Date-time:     %s
Error:         %s
Error explain: %s
User:          %s
Content-Type:  %s
Action:        %s
Duplicates:    %s

""" % (self.request_namespace, datetime.now(), err_message, err_explain,
                self.email, self.content_type, self.action, self.duplicates))

        # Send email to user
        msg = """Hello,

This is a notification email to inform you that something went wrong with the
de-duplication of your file. The application's administrators have been
notified. If you want to contact them directly, please send an email to %s or
visit the following webpage to submit an issue:

https://www.github.com/VertNet/dedupe/issues

Sorry for the inconvenience, and thanks for your understanding.
""" % ADMIN
        self.send_email_notification(msg)

        # Log the error
        params = dict(
            latlon=self.latlon, country=self.country, status="error",
            user_agent=self.user_agent, warnings=self.warnings,
            error=err_message, email=self.email, action=self.action,
            duplicates=self.duplicates,
            loc=self.headers[self.loc], sci=self.headers[self.sci],
            dat=self.headers[self.dat], col=self.headers[self.col],
            id_field=self.id_field, namespace=self.request_namespace,
            content_type=self.content_type, file_size=self.file_size
        )
        taskqueue.add(
            url='/service/v0/log',
            payload=json.dumps(params),
            queue_name=QUEUE_NAME
        )
        logging.info("Logging enqueued")
        return

    def send_email_notification(self, msg):
        """Send email to user with success/failure notification."""

        if msg == "success":

            # Assign email subject
            subject = EMAIL_SUCCESS_SUBJECT

            # Build explanation note for email
            if self.action == "flag":
                action_description = ACTION_FLAG
            elif self.action == "remove":
                action_description = ACTION_REMOVE

            # Create email body
            body = EMAIL_SUCCESS_BODY.format(
                self.file_url,
                action_description,
                json.dumps(self.report, sort_keys=True, indent=4))

        else:
            subject = EMAIL_ERROR_SUBJECT
            body = msg

        # Send email
        sender = EMAIL_SENDER
        to = self.email
        mail.send_mail(sender=sender, to=to, subject=subject, body=body)

        return

    def check_strict_dupes(self, row):
        """Check if the provided record is a strict duplicate of a previous
one."""
        # Calculate md5 hash
        k = hashlib.md5(str(row)).hexdigest()
        # Check if hash exists in memcache
        dupe = memcache.get(k, namespace=self.request_namespace)
        # If exists, STRICT_DUPE
        if dupe is not None:
            self.is_dupe = STRICT_DUPE
            self.strict_duplicates += 1
            self.dupe_ref = dupe
            self.duplicate_order.add((dupe, self.records))
            if self.id_field is not None:
                self.duplicate_ids.add(row[self.idx])
            return 1
        # Otherwise, store key in memcache
        else:
            memcache.set(k, self.records, namespace=self.request_namespace)
            return 0

    def check_partial_dupes(self, row):
        """Check if the provided record is a partial duplicate of a previous
one."""
        # Build id string
        pk = "|".join([row[self.loc], row[self.sci],
                       row[self.col], row[self.dat]])
        # Check if key exists in memcache
        pdupe = memcache.get(pk, namespace=self.request_namespace)
        # If exists, PARTIAL_DUPE
        if pdupe is not None:
            self.is_dupe = PARTIAL_DUPE
            self.partial_duplicates += 1
            self.dupe_ref = pdupe
            self.partial_duplicates_order.add((pdupe, self.records))
            if self.id_field is not None:
                self.partial_duplicate_ids.add(row[self.idx])
            return 1
        # Otherwise, store key in memcache
        else:
            memcache.set(pk, self.records,
                         namespace=self.request_namespace)
            return 0

    def handle_row(self, row):
        """Handle row according to check result and action type:
- No duplicate and action is remove or flag: write row
- Duplicate and action is remove: skip writing row
- Duplicate and action is flag: update record and write row
"""

        # If action is remove and is duplicate, or action is report, omit write
        if (self.action == "remove" and self.is_dupe != NO_DUPE) \
                or self.action == "report":
            pass

        # Otherwise, write row
        else:
            # If action is flag, add three flag fields to row
            if self.action == "flag":
                row.append(bool(self.is_dupe))
                row.append(self.is_dupe if self.is_dupe > 0 else None)
                row.append(self.dupe_ref)

            try:  # Workaround to handle proper conversion
                si = StringIO()
                cw = csv.writer(si, delimiter=self.delimiter)
                cw.writerow(row)
                self.f.write(si.getvalue())
            except Exception, e:
                logging.warning("Something went wrong writing a row\n"
                                "f: %s\nrow: %s\nerror: %s" %
                                (self.file_name, row, e))
                self.warnings.append("Could not write record %s in new file" %
                                     self.records)

    def post(self):
        """Main function. Parse the file for duplicates."""

        # Initialize variables from request
        self.latlon = self.request.get("latlon", None)
        self.country = self.request.get("country", None)
        self.user_agent = self.request.get("user_agent", None)
        self.email = self.request.get("email", None)
        self.request_namespace = self.request.get("request_namespace", None)
        self.request_namespace = str(self.request_namespace)
        self.previous_namespace = self.request.get("previous_namespace", None)
        self.content_type = self.request.get("content_type", None)
        self.delimiter = str(self.request.get("delimiter", None))
        self.extension = self.request.get("extension", None)
        self.action = self.request.get("action", None)
        self.duplicates = self.request.get("duplicates", None)
        self.file_path = str(self.request.get("file_path", None))
        self.file_name = str(self.request.get("file_name", None))
        self.headers = json.loads(self.request.get("headers", None))
        self.headers_lower = [x.lower() for x in self.headers]
        self.loc = int(self.request.get("loc", None))
        self.sci = int(self.request.get("sci", None))
        self.dat = int(self.request.get("dat", None))
        self.col = int(self.request.get("col", None))
        self.id_field = self.request.get("id_field", None)

        # Switch to request namespace
        namespace_manager.set_namespace(self.request_namespace)
        logging.info("Switched to namespace %s" % self.request_namespace)

        # Transform "all" in list of elements for duplicate types
        if self.duplicates == "all":
            self.duplicates = [x for x in ALLOWED_DUPLICATES if x is not "all"]

        # Store file size for logging
        self.file_size = gcs.stat(self.file_name).st_size
        logging.info("File size: %s" % self.file_size)

        # Get file from GCS
        try:
            self.file = gcs.open(self.file_name)
        except Exception, e:
            self._err(500, "Could not open uploaded file", e)
            return
        self.reader = csv.reader(self.file, delimiter=self.delimiter)

        # Initialize warnings
        self.warnings = []

        # Initialize report values
        self.records = 0
        self.strict_duplicates = 0
        self.duplicate_order = set()
        self.partial_duplicates = 0
        self.partial_duplicates_order = set()

        # Calculating "id" field position, if exists
        if self.id_field is not None:
            self.idx = self.headers_lower.index(self.id_field.lower())
            logging.info("Using %s as 'id' field" % self.id_field)
            logging.info("'id' field in position %s" % self.idx)
            self.duplicate_ids = set()
            self.partial_duplicate_ids = set()

        # Create response file in GCS
        if self.action != "report":
            self.file_name = "/".join(["", BUCKET, self.request_namespace])
            self.file_name = "%s/modif.%s" % (self.file_path, self.extension)

            # Open file
            try:
                self.f = gcs.open(self.file_name, 'w',
                                  content_type=self.content_type)
                logging.info("Created GCS file in %s" % self.file_name)
            except Exception, e:
                self._err(500, "Could not open result file", e)

            # Write headers
            if self.action == "flag":
                self.headers += ["isDuplicate", "duplicateType", "duplicateOf"]
            try:
                self.f.write(str(self.delimiter.join(self.headers)))
                self.f.write("\n")
                logging.info("Successfully wrote headers in file")
            except Exception, e:
                self._err(500, "Could not write headers in result file", e)

        # Parse records
        for row in self.reader:
            self.records += 1
            self.is_dupe = NO_DUPE
            self.dupe_ref = None

            # Check for strict duplicates
            if "strict" in self.duplicates and self.is_dupe == NO_DUPE:
                self.check_strict_dupes(row)

            # Check for partial duplicates
            if "partial" in self.duplicates and self.is_dupe == NO_DUPE:
                self.check_partial_dupes(row)

            ##
            # TODO: More type of duplicates will be added here
            ##

            # Handle row according to check result and action type
            self.handle_row(row)

        # Close file when finished parsing records
        if self.action != "report":
            try:
                self.f.close()
                self.file_url = "https://storage.googleapis.com%s" %\
                                self.file_name
                logging.info("Successfully created file %s" % self.file_name)
            except Exception, e:
                self._err(500, "Could not close result file", e)

        # TODO: Update report
        #   - Make concise report for email and longer as attachment

        # Build report skeleton
        self.report = {
            "email": self.email,
            "records": self.records,
            "fields": len(self.headers),
        }

        # Add warning info
        if len(self.warnings) > 0:
            self.report['warnings'] = self.warnings

        # Build strict_duplicates
        sd = {
            "count": self.strict_duplicates
        }

        if self.strict_duplicates > 0:
            sd["index_pairs"] = list(self.duplicate_order)
            if self.id_field is not None:
                sd["ids"] = list(self.duplicate_ids)

        # Add duplicates to report
        self.report["strict_duplicates"] = sd

        # Build partial_duplicates
        pd = {
            "count": self.partial_duplicates
        }

        if self.partial_duplicates > 0:
            pd["index_pairs"] = list(self.partial_duplicates_order)
            if self.id_field is not None:
                pd["ids"] = list(self.partial_duplicate_ids)

        # Add partial duplicates to report
        self.report["partial_duplicates"] = pd

        # Add file URL to response
        if self.action != "report":
            self.report["file_url"] = self.file_url

        # Send notification to user
        self.send_email_notification("success")

        # Return to default namespace
        namespace_manager.set_namespace(self.previous_namespace)

        # Add entry to log
        params = dict(
            latlon=self.latlon, country=self.country, status="success",
            user_agent=self.user_agent, warnings=self.warnings, error=None,
            email=self.email, action=self.action, duplicates=self.duplicates,
            loc=self.headers[self.loc], sci=self.headers[self.sci],
            dat=self.headers[self.dat], col=self.headers[self.col],
            id_field=self.id_field, namespace=self.request_namespace,
            content_type=self.content_type, file_size=self.file_size,
            records=self.records, fields=len(self.headers),
            strict_duplicates=self.strict_duplicates, api_version=API_VERSION,
            partial_duplicates=self.partial_duplicates
        )
        taskqueue.add(
            url='/service/v0/log',
            payload=json.dumps(params),
            queue_name=QUEUE_NAME
        )
        logging.info("Logging enqueued")

        # Build response
        resp = self.report
        self.response.headers['Content-Type'] = "application/json"
        self.response.write(json.dumps(resp)+"\n")
        return

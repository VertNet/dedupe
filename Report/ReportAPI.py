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
import uuid
import hashlib
import logging
from StringIO import StringIO

from google.appengine.api import namespace_manager, memcache, mail
import cloudstorage as gcs
import webapp2

LAST_UPDATED = ''
REPORT_VERSION = ''

IS_DEV = os.environ.get('SERVER_SOFTWARE', '').startswith('Development')

if IS_DEV:
    QUEUE_NAME = 'default'
else:
    QUEUE_NAME = 'dedupes'

_ALLOWED_ACTIONS = ["report", "flag", "remove"]
_ALLOWED_TYPES = ["text/csv", "text/tab-separated-values"]
_LOC = "locality"
_SCI = "scientificName"
_COL = "recordedBy"
_DAT = "eventDate"
_BUCKET = "vn-dedupe"
_NO_DUPE = 0
_STRICT_DUPE = 1
_PARTIAL_DUPE = 2
_EMAIL_SENDER = "VertNet Tools - De-duplication <javier.otegui@gmail.com>"


class ReportApi(webapp2.RequestHandler):
    """
Instance attributes:

- action: Type of action to perform on the file
- cityLatLong: Coordinates of the city of the request
- col: position of the "recordedBy" field in the file
- content_type: Content-Type header of the request
- country: Code of the country of the request
- dat: position of the "eventDate" field in the file
- delimiter: field delimiter, accordint to content_type variable
- duplicate_ids: list of values of the "id" field in duplicate records,
                 for strict duplicates
- duplicate_order: position of the original-duplicate pair of records,
                 for strict duplicates
- duplicates: number of strict duplicates found
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
- user_agent: User-Agent header of the request
- warnings: list conaining all warnings generated during the process
"""
    def __init__(self, request, response):

        # Get request headers
        self.cityLatLong = request.headers.get('X-AppEngine-CityLatLong')
        self.country = request.headers.get('X-AppEngine-Country')
        self.user_agent = request.headers.get('User-Agent')

        # Handle namespace for this request
        self.previous_namespace = namespace_manager.get_namespace()
        self.request_namespace = str(uuid.uuid4())
        namespace_manager.set_namespace(self.request_namespace)
        logging.info("Switched to namespace %s" % self.request_namespace)

        # Initialize response
        logging.info('Initializing Report with headers %s' % request.headers)
        self.initialize(request, response)
        return

    def _err(self, err_code=500, err_message="", err_explain=""):
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
        return

    def get(self):
        err_message = "Method not allowed"
        err_explain = "Only POST requests are allowed"
        self._err(405, err_message, err_explain)
        return

    def post(self):

        # Initialize warnings
        self.warnings = []

        # Check email exists in parameters
        self.email = self.request.get("email", None)
        if self.email is None:
            self.error(400)
            err_message = "Please provide an email address"
            logging.error(err_message)
            resp = {
                "status": "error",
                "error": err_message
            }
            self.response.write(json.dumps(resp)+"\n")
            return

        # Determine file format via 'Content-Type'
        self.content_type = self.request.headers['Content-Type']
        logging.info("Content-Type: %s" % self.content_type)

        if self.content_type == "application/x-www-form-urlencoded":
            err_explain = "'Content-Type' is a required header for the" \
                          " proper working of the API." \
                          " Please read the documentation for examples on" \
                          " how to set this parameter"
            self._err(400, "No 'Content-Type' was provided", err_explain)
            return

        # Establish field separator based on Content-Type
        if self.content_type == "text/csv":
            self.delimiter = ","
            self.extension = ".csv"
        elif self.content_type == "text/tab-separated-values":
            self.delimiter = "\t"
            self.extension = ".txt"
        else:
            err_explain = "The value of 'Content-Type' is not among the" \
                          " accepted values for this header. Should be one" \
                          " of: %s" % ", ".join(_ALLOWED_TYPES)
            self._err(400, "Wrong 'Content-Type' header", err_explain)
            return

        # Determine action ("report" by default)
        self.action = self.request.get("action", "report")
        if self.action not in _ALLOWED_ACTIONS:
            err_explain = "Action %s is not valid. Should be one of: %s" % (
                self.action, ", ".join(_ALLOWED_ACTIONS))
            self._err(400, "Action not allowed", err_explain)
            return
        logging.info("Action: %s" % self.action)

        # Get content from request body
        self.file = self.request.body_file.file

        # Initialize parsing
        self.reader = csv.reader(self.file, delimiter=self.delimiter)
        self.headers = self.reader.next()
        self.headers_lower = [x.lower() for x in self.headers]

        # Check if proper field delimiter
        if len(self.headers) == 1:
            err_explain = "The system ended up with 1-field rows. Please" \
                          " check the 'Content-Type' parameter"
            self._err(400, "Wrong 'Content-Type' header", err_explain)
            return

        # Get positions for partial duplicates
        self.loc = self.headers_lower.index(_LOC.lower())
        self.sci = self.headers_lower.index(_SCI.lower())
        self.col = self.headers_lower.index(_COL.lower())
        self.dat = self.headers_lower.index(_DAT.lower())

        # Initialize report values
        self.records = 0
        self.duplicates = 0
        self.duplicate_order = set()
        self.partial_duplicates = 0
        self.partial_duplicates_order = set()

        # Check "id" parameter
        self.id_field = self.request.get("id", None)
        # If not given
        if self.id_field is None:
            # Find "id" field
            if 'id' in self.headers_lower:
                self.id_field = 'id'
            # Otherwise find "occurrenceid" field
            elif 'occurrenceid' in self.headers_lower:
                self.id_field = 'occurrenceid'
            # Otherwise, show warning and don't show "id"-related info
            else:
                warning_msg = "No 'id' field could be determined"
                self.warnings.append(warning_msg)
                logging.warning(warning_msg)
                self.id_field = None
        # Otherwise, check if field exists in headers
        elif self.id_field.lower() not in self.headers_lower:
            self._err(400, "Couldn't find field '%s'" % self.id_field)
            return

        # Calculating "id" field position, if exists
        if self.id_field is not None:
            self.idx = self.headers_lower.index(self.id_field.lower())
            logging.info("Using %s as 'id' field" % self.id_field)
            logging.info("'id' field in position %s" % self.idx)
            self.duplicate_ids = set()
            self.partial_duplicate_ids = set()

        # Open file in GCS
        if self.action != "report":
            self.file_name = "/".join(["", _BUCKET, self.request_namespace])
            self.file_name = self.file_name + self.extension
            try:
                self.f = gcs.open(self.file_name, 'w',
                                  content_type=self.content_type)
                logging.info("Open GCS file in %s" % self.file_name)
                self.f.write(self.delimiter.join(self.headers))
                self.f.write("\n")
                logging.info("Successfully wrote headers in file")
            except Exception, e:
                logging.error("Something went wrong opening the file:\n"
                              "f: %s\nerror: %s" % (self.file_name, e))

        # Parse records
        for row in self.reader:
            self.records += 1
            self.is_dupe = _NO_DUPE

            # Strict duplicates
            # Calculate md5 hash
            k = hashlib.md5(str(row)).hexdigest()
            # Check if hash exists in memcache
            dupe = memcache.get(k, namespace=self.request_namespace)
            if dupe is not None:
                self.is_dupe = _STRICT_DUPE
                self.duplicates += 1
                self.duplicate_order.add((dupe, self.records))
                if self.id_field is not None:
                    self.duplicate_ids.add(row[self.idx])
            else:
                # Add key to memcache
                memcache.set(k, self.records, namespace=self.request_namespace)
                # look for partial dupe
                # Build id string
                pk = "|".join([row[self.loc], row[self.sci],
                               row[self.col], row[self.dat]])
                # Check if key exists in memcache
                pdupe = memcache.get(pk, namespace=self.request_namespace)
                if pdupe is not None:
                    self.is_dupe = _PARTIAL_DUPE
                    self.partial_duplicates += 1
                    self.partial_duplicates_order.add((pdupe, self.records))
                    if self.id_field is not None:
                        self.partial_duplicate_ids.add(row[self.idx])
                else:
                    memcache.set(pk, self.records,
                                 namespace=self.request_namespace)

            if self.action != "report":
                # Write row if no duplicate
                if self.is_dupe == 0:
                    try:
                        # Workaround to handle proper conversion
                        si = StringIO()
                        cw = csv.writer(si, delimiter=self.delimiter)
                        cw.writerow(row)
                        self.f.write(si.getvalue())
                        # self.f.write(row)
                        logging.info("Wrote line in %s" % self.file_name)
                    except Exception, e:
                        logging.error("Something went wrong writing a row\n"
                                      "f: %s\nrow: %s\nerror: %s" %
                                      (self.file_name, row, e))
                # Write row with flag if action="flag"
                elif self.action == "flag":
                    # TODO
                    logging.warning("Should have written row %s here"
                                    % self.record)

        # Close file
        if self.action != "report":
            try:
                self.f.close()
                self.file_url = "https://storage.googleapis.com%s" %\
                                self.file_name
                logging.info("Successfully created file %s" % self.file_name)
            except Exception, e:
                logging.error("Something went wrong creating the file\n"
                              "f: %s\nerror: %s" % (self.file_name, e))

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
            "count": self.duplicates
        }

        if self.duplicates > 0:
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

        # Send email to user
        if self.action != "report":

            # Build explanation note for email
            if self.action == "flag":
                action_description = """
Since you selected the "flag" option, the system has added some new fields to
the dataset you provided. <field explanation here>.
"""
            elif self.action == "remove":
                action_description = """
Since you selected the "remove" option, the system has deleted the duplicate
rows, so you should see the dataset has now fewer records. Please check out the
report below to find more information about the removed records.
"""
            subject = "Your de-duplicated file is ready"
            sender = _EMAIL_SENDER
            to = self.email
            body = """Hello,

This is a notification email to inform you that the file you sent to the
VertNet de-duplication API is ready and available for download here (link
available for 24h):

{}
{}

Finally, this is what the system has gathered from the de-duplication system:

{}

You can find more information on the de-duplication system here:

https://www.github.com/VertNet/dedupe

If you find any issue or complain, please report it here:

https://www.github.com/VertNet/dedupe/issues

Thank you for using our services. Best wishes,
The VertNet Team
http://www.vertnet.org
""".format(self.file_url, action_description, json.dumps(self.report,
                                                         sort_keys=True,
                                                         indent=4))

            mail.send_mail(sender=sender, to=to, subject=subject, body=body)

        # Return to default namespace
        namespace_manager.set_namespace(self.previous_namespace)

        # Build response
        resp = self.report
        self.response.headers['Content-Type'] = "application/json"
        self.response.write(json.dumps(resp)+"\n")
        return

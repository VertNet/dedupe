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

TODO: add documentation on usage here

"""

import csv
import json
import uuid
import logging

from google.appengine.api import namespace_manager, taskqueue
import cloudstorage as gcs
import webapp2

from config import *

LAST_UPDATED = ''
REPORT_VERSION = ''


class DedupeApi(webapp2.RequestHandler):
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
    def __init__(self, request, response):

        # Get request headers
        self.cityLatLong = request.headers.get('X-AppEngine-CityLatLong')
        self.country = request.headers.get('X-AppEngine-Country')
        self.user_agent = request.headers.get('User-Agent')

        # Handle namespace for this request
        self.previous_namespace = namespace_manager.get_namespace()
        self.request_namespace = str(uuid.uuid4())

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

        # Check email exists in parameters
        self.email = self.request.get("email", None)
        if self.email is None:
            self._err(400, "Please provide an email address")
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
            self.extension = "csv"
        elif self.content_type == "text/tab-separated-values":
            self.delimiter = "\t"
            self.extension = "txt"
        else:
            err_explain = "The value of 'Content-Type' is not among the" \
                          " accepted values for this header. Should be one" \
                          " of: %s" % ", ".join(ALLOWED_TYPES)
            self._err(400, "Wrong 'Content-Type' header", err_explain)
            return

        # Determine action ("flag" by default)
        self.action = self.request.get("action", "flag")
        if self.action not in ALLOWED_ACTIONS:
            err_explain = "Action %s is not valid. Should be one of: %s" % (
                self.action, ", ".join(ALLOWED_ACTIONS))
            self._err(400, "Action not allowed", err_explain)
            return
        logging.info("Action: %s" % self.action)

        # Determine duplicate types to be checked ("all" by default)
        self.duplicates = self.request.get("duplicates", "all")
        if self.duplicates not in ALLOWED_DUPLICATES:
            err_explain = "Value of 'duplicates' parameter %s is not valid."
            err_explain += " Should be one of: %s"
            err_explain = err_explain % (
                self.duplicates, ", ".join(ALLOWED_DUPLICATES)
            )
            self._err(400, "Duplicate detection type not allowed", err_explain)
            return

        # Transform "all" in list of elements for duplicate types
        if self.duplicates == "all":
            self.duplicates = [x for x in ALLOWED_DUPLICATES if x is not "all"]

        # Get content from request body
        self.body_file = self.request.body_file
        self.file = self.body_file.file

        # Sniff headers
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
        self.loc = self.headers_lower.index(LOC.lower())
        self.sci = self.headers_lower.index(SCI.lower())
        self.col = self.headers_lower.index(COL.lower())
        self.dat = self.headers_lower.index(DAT.lower())

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

        # Store original file in GCS
        self.file_path = "/".join(["", BUCKET, self.request_namespace])
        self.file_name = "%s/orig.%s" % (self.file_path, self.extension)
        try:
            f = gcs.open(self.file_name, 'w', content_type=self.content_type)
            logging.info("File %s created" % self.file_name)
            f.write(self.file.read())
            logging.info("Successfully wrote file to GCS")
            f.close()
            logging.info("File closed")
        except Exception, e:
            logging.error("Something went wrong opening the file:\n"
                          "f: %s\nerror: %s" % (self.file_name, e))

        # Launch async task with parameters
        params = {
            "email": self.email,
            "request_namespace": self.request_namespace,
            "previous_namesapce": self.previous_namespace,
            "content_type": self.content_type,
            "delimiter": self.delimiter,
            "extension": self.extension,
            "action": self.action,
            "duplicates": self.duplicates,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "headers": self.headers,
            "headers_lower": self.headers_lower,
            "loc": self.loc,
            "sci": self.sci,
            "dat": self.dat,
            "col": self.col,
            "id_field": self.id_field
        }
        taskqueue.add(
                url=TASKURL,
                params=params
            )

        # Build response
        resp = "{}"
        self.response.headers['Content-Type'] = "application/json"
        self.response.write(json.dumps(resp)+"\n")
        return

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

from google.appengine.api import namespace_manager, memcache
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


class ReportApi(webapp2.RequestHandler):
    """."""
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
            delimiter = ","
        elif self.content_type == "text/tab-separated-values":
            delimiter = "\t"
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
        reader = csv.reader(self.file, delimiter=delimiter)
        self.headers = reader.next()
        self.headers_lower = [x.lower() for x in self.headers]

        # Check if proper field delimiter
        if len(self.headers) == 1:
            err_explain = "The system ended up with 1-field rows. Please" \
                          " check the 'Content-Type' parameter"
            self._err(400, "Wrong 'Content-Type' header", err_explain)
            return

        # Initialize report values
        self.records = 0
        self.duplicates = 0
        self.duplicate_order = set()

        # Check "id" parameter
        id_field = self.request.get("id", None)
        # If not given
        if id_field is None:
            # Find "id" field
            if 'id' in self.headers_lower:
                id_field = 'id'
            # Otherwise find "occurrenceid" field
            elif 'occurrenceid' in self.headers_lower:
                id_field = 'occurrenceid'
            # Otherwise, show warning and don't show "id"-related info
            else:
                warning_msg = "No 'id' field could be determined"
                self.warnings.append(warning_msg)
                logging.warning(warning_msg)
                id_field = None
        # Otherwise, check if field exists in headers
        elif id_field.lower() not in self.headers_lower:
            self._err(400, "Could not find field '%s' in headers" % id_field)
            return

        # Calculating "id" field position, if exists
        if id_field is not None:
            idx = self.headers_lower.index(id_field.lower())
            logging.info("Using %s as 'id' field" % id_field)
            logging.info("'id' field in position %s" % idx)
            self.duplicate_ids = set()

        # Parse records
        for row in reader:
            self.records += 1

            # Calculate md5 hash
            k = hashlib.md5(str(row)).hexdigest()

            # Check if hash exists in memcache
            dupe = memcache.get(k, namespace=self.request_namespace)
            if dupe is not None:
                self.duplicates += 1
                self.duplicate_order.add((dupe, self.records))
                if id_field is not None:
                    self.duplicate_ids.add(row[idx])
            else:
                memcache.set(k, self.records, namespace=self.request_namespace)

        # Build report
        report = {
            "email": self.email,
            "records": self.records,
            "fields": len(self.headers),
        }

        # Add warning info
        if len(self.warnings) > 0:
            report['warnings'] = self.warnings

        # Build strict_duplicates
        sd = {
            "count": self.duplicates
        }

        if self.duplicates > 0:
            sd["index_pairs"] = list(self.duplicate_order)
            if id_field is not None:
                sd["ids"] = list(self.duplicate_ids)

        # Add duplicates to report
        report["strict_duplicates"] = sd

        # Return to default namespace
        namespace_manager.set_namespace(self.previous_namespace)

        # Build response
        resp = report
        self.response.headers['Content-Type'] = "application/json"
        self.response.write(json.dumps(resp)+"\n")
        return

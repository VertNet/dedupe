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
        self.response.write(json.dumps(resp)+"\n")
        return

    def post(self):

        # Prepare output
        self.response.headers['Content-Type'] = "application/json"

        # Check email
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

        # Get content from request body
        self.file = self.request.body_file.file

        # Initialize parsing
        reader = csv.reader(self.file, delimiter="\t")
        self.headers = reader.next()
        self.headers_lower = [x.lower() for x in self.headers]
        self.records = 0
        self.duplicates = 0
        self.duplicate_ids = set()
        self.duplicate_order = set()

        # Check "id" parameter
        id_field = self.request.get("id", None)
        # If not given
        if id_field is None:
            if 'id' in self.headers_lower:
                id_field = 'id'
            # Otherwise find "occurrenceid" field
            elif 'occurrenceid' in self.headers_lower:
                id_field = 'occurrenceid'
            # Otherwise, show warning and use first field
            else:
                logging.warning("No 'id' field could be reliably determined")
                id_field = None
                idx = 0
        # Otherwise, check if field exists in headers
        elif id_field.lower() not in self.headers_lower:
            self.error(400)
            err_message = "Could not find field '%s' in headers" % id_field
            logging.error(err_message)
            resp = {
                "status": "error",
                "error": err_message
            }
            self.response.write(json.dumps(resp)+"\n")
            return

        # Calculating "id" field position
        idx = self.headers_lower.index(id_field.lower())
        logging.info("Using %s as 'id' field" % id_field)
        logging.info("'id' field in position %s" % idx)

        # Parse records
        for row in reader:
            self.records += 1

            # Calculate md5 hash
            k = hashlib.md5(str(row)).hexdigest()

            # Check if hash exists in memcache
            dupe = memcache.get(k, namespace=self.request_namespace)
            if dupe is not None:
                self.duplicates += 1
                self.duplicate_ids.add(row[idx])
                self.duplicate_order.add(self.records)
            else:
                memcache.set(k, True, namespace=self.request_namespace)

        metadata = {
            "email": self.email,
            "records": self.records,
            "fields": len(self.headers),
            # "headers": self.headers,
            "strict_duplicates": self.duplicates
        }

        if self.duplicates > 0:
            metadata["strict_duplicate_records"] = list(self.duplicate_order)
            metadata["strict_duplicate_ids"] = list(self.duplicate_ids)

        # TODO: flush memcache

        # Return to default namespace
        namespace_manager.set_namespace(self.previous_namespace)

        # Build response
        resp = metadata
        self.response.write(json.dumps(resp)+"\n")
        return

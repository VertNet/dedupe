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
import json
import logging

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
        self.cityLatLong = request.headers.get('X-AppEngine-CityLatLong')
        self.country = request.headers.get('X-AppEngine-Country')
        self.user_agent = request.headers.get('User-Agent')
        logging.info('Initializing Report with headers %s' % request.headers)
        self.initialize(request, response)
        return

    def post(self):
        self.response.headers['Content-Type'] = "application/json"
        resp = {
            "hello": "world"
        }
        self.response.write(json.dumps(resp)+"\n")
        return

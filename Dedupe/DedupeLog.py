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

import os
import json
import logging

from google.appengine.api import namespace_manager
import webapp2

from models import LogEntry

LAST_UPDATED = '2016-08-05T13:09:15+CEST'
LOGGER_VERSION = 'logger 2016-08-05T13:09:15+CEST'

IS_DEV = os.environ.get('SERVER_SOFTWARE', '').startswith('Development')
if IS_DEV:
    CLIENT = 'api-dev'
else:
    CLIENT = 'api-prod'


class DedupeLog(webapp2.RequestHandler):
    def post(self):

        # Move to logging default namespace
        previous_namespace = namespace_manager.get_namespace()
        namespace_manager.set_namespace('dedupe_log')
        current_namespace = namespace_manager.get_namespace()

        # Get parameters from request body
        params = json.loads(self.request.body)

        # Add "client" parameter
        params['client'] = CLIENT

        # Parse event coordinates
        latlon = params.pop('latlon')
        if latlon and latlon != "None":
            params['lat'], params['lon'] = map(float, latlon.split(","))
        else:
            params['lat'] = None
            params['lon'] = None

        # Build and store LogEntry entity in default namespace
        log_entry = LogEntry(**params)
        log_entry_key = log_entry.put()

        # Restore previous namespace
        namespace_manager.set_namespace(previous_namespace)

        # Send response and finish call
        resp = {
            "result": "success",
            "message": "new log entry successfully added",
            "namespace": current_namespace,
            "logger_version": LOGGER_VERSION,
            "log_entry_key": log_entry_key.id(),
            "log_entry": params
        }
        logging.info(resp)
        return

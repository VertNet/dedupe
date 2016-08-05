# This file is part of VertNet: https://github.com/VertNet/webapp
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

"""API method and service routing."""

import webapp2

# API methods
from Dedupe.DedupeAPI import DedupeApi
from Dedupe.DedupeTask import DedupeTask
from Dedupe.DedupeLog import DedupeLog

LAST_UPDATED = ''

routes = [

    # API methods
    webapp2.Route(r'/api/v0/dedupe', handler=DedupeApi),

    # Background service
    webapp2.Route(r'/service/v0/dedupe', handler=DedupeTask),

    # Logging service
    webapp2.Route(r'/service/v0/log', handler=DedupeLog)

]

handlers = webapp2.WSGIApplication(routes, debug=True)

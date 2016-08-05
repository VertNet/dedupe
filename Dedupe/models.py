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

from google.appengine.ext import ndb


class LogEntry(ndb.Model):

    # Event metadata
    lat = ndb.FloatProperty()
    lon = ndb.FloatProperty()
    country = ndb.StringProperty()
    user_agent = ndb.StringProperty()
    created_at = ndb.DateTimeProperty(auto_now_add=True)
    updated_at = ndb.DateTimeProperty(auto_now=True)
    status = ndb.StringProperty()
    warnings = ndb.StringProperty(repeated=True)
    error = ndb.StringProperty()
    api_version = ndb.StringProperty()
    client = ndb.StringProperty()

    # Dedupe parameters
    email = ndb.StringProperty()
    action = ndb.StringProperty()
    duplicates = ndb.StringProperty(repeated=True)
    loc = ndb.StringProperty()
    sci = ndb.StringProperty()
    dat = ndb.StringProperty()
    col = ndb.StringProperty()
    id_field = ndb.StringProperty()

    # File parameters
    namespace = ndb.StringProperty()
    content_type = ndb.StringProperty()
    file_size = ndb.IntegerProperty()
    records = ndb.IntegerProperty()
    fields = ndb.IntegerProperty()
    strict_duplicates = ndb.IntegerProperty()
    partial_duplicates = ndb.IntegerProperty()

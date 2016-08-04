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

IS_DEV = os.environ.get('SERVER_SOFTWARE', '').startswith('Development')

if IS_DEV:
    QUEUE_NAME = 'default'
else:
    QUEUE_NAME = 'dedupe'

TASKURL = "/service/v0/dedupe"
ALLOWED_ACTIONS = ["report", "flag", "remove"]
ALLOWED_TYPES = ["text/csv", "text/tab-separated-values"]
LOC = "locality"
SCI = "scientificName"
COL = "recordedBy"
DAT = "eventDate"
BUCKET = "vn-dedupe"
NO_DUPE = 0
STRICT_DUPE = 1
PARTIAL_DUPE = 2
EMAIL_SENDER = "VertNet Tools - De-duplication <javier.otegui@gmail.com>"

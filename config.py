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

# Task queue selection
IS_DEV = os.environ.get('SERVER_SOFTWARE', '').startswith('Development')
if IS_DEV:
    QUEUE_NAME = 'default'
else:
    QUEUE_NAME = 'dedupe'

# Allowed values for parameters and headers
ALLOWED_ACTIONS = ["report", "flag", "remove"]
ALLOWED_TYPES = ["text/csv", "text/tab-separated-values"]
ALLOWED_DUPLICATES = ["strict", "partial", "all"]

# Names of default fields for partial duplicate detection
LOC = "locality"
SCI = "scientificName"
COL = "recordedBy"
DAT = "eventDate"

# Codification of duplicate type
NO_DUPE = 0
STRICT_DUPE = 1
PARTIAL_DUPE = 2

# Other configuration variables
TASKURL = "/service/v0/dedupe"
BUCKET = "vn-dedupe"

# Email variables
ACTION_FLAG = """
Since you selected the "flag" option, the system has added some new fields to
the dataset you provided. <field explanation here>.
"""

ACTION_REMOVE = """
Since you selected the "remove" option, the system has deleted the duplicate
rows, so you should see the dataset has now fewer records. Please check out the
report below to find more information about the removed records.
"""

ADMIN = "javier.otegui@gmail.com"
EMAIL_SENDER = "VertNet Tools - De-duplication <javier.otegui@gmail.com>"
EMAIL_SUCCESS_SUBJECT = "Your de-duplicated file is ready"
EMAIL_ERROR_SUBJECT = "Something went wrong with the de-duplication process"
EMAIL_SUCCESS_BODY = """Hello,

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
"""

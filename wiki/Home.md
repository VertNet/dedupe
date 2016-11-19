VertNet's de-duplication service
===

This repository contains the code for [VertNet](http://www.vertnet.org)'s record **de-duplication** service.

The de-duplication service is an API accessed using HTTP that enables discovery and removal of several types of duplicated information in biodiversity data sets.

## Location, methods and versions

Currently, the service can be accessed via this base URL:

> http://dedupe.vertnet-portal.appspot.com/api/{version}/{method}

The following methods are currently available

| Method | Latest version | Documentation |
|:------:|:--------------:|---------------|
| `dedupe` | `v0` (alpha) | [https://www.github.com/VertNet/dedupe/wiki/Dedupe-API](https://www.github.com/VertNet/dedupe/wiki/Dedupe-API) |

# Other project repositories

* VertNet web portal: [https://github.com/VertNet/portal-web][vn-portal]
* VertNet API: [https://github.com/VertNet/api][vn-api]
* Harvesting: [https://github.com/VertNet/gulo][vn-gulo]
* Indexing: [https://github.com/VertNet/dwc-indexer][dwc-indexer]
* Toolkit: [https://github.com/VertNet/toolkit][vn-toolkit]
* Georeferencing calculator: [https://github.com/VertNet/georefcalculator][georef-calc]
* Geospatial Quality API: [https://github.com/VertNet/api-geospatial][vn-geoapi]
* Usage Statistics Generation: [https://github.com/VertNet/usagestats][vn-usagestats]
* BigQuery: [https://github.com/VertNet/bigquery][vn-bigquery]

# License

![](http://www.gnu.org/graphics/lgplv3-147x51.png)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, [see here](http://www.gnu.org/licenses/).

<!-- links -->
[vn-portal]: https://github.com/VertNet/portal-web
[vn-api]: https://github.com/VertNet/api
[vn-gulo]: https://github.com/VertNet/gulo
[dwc-indexer]: https://github.com/VertNet/dwc-indexer
[vn-toolkit]: https://github.com/VertNet/toolkit
[georef-calc]: https://github.com/VertNet/georefcalculator
[vn-geoapi]: https://github.com/VertNet/api-geospatial
[vn-usagestats]: https://github.com/VertNet/usagestats
[vn-bigquery]: https://github.com/VertNet/bigquery
[development]: https://github.com/VertNet/api/wiki/Development
[search-wiki]: https://github.com/VertNet/api/wiki/Search-API
[download-wiki]: https://github.com/VertNet/api/wiki/Download-API
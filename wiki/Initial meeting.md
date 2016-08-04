Initial meeting
===

RESTful API. Flag duplicates in trivial and non-trivial ways:

1. Trivial: actual duplicates
1. Non-trivial: potential duplicates, like herbarium duplicates, where locality, date, collector and taxon are the same

The result is the data set with flags. These flags indicate actual/potential duplicates. Also, add a "reason" field.

Workflow:

1. Submit a data set
1. Depending on the f(x) (or argument/s):
    1. Return a report
    1. Return the data set with flags
    1. Return the data set with no strict duplicates
    1. Return the data set with no duplicates, strict or not

Add an internal "id" to reference records: "Record id 5 is the same as record id 1".

If data set has "occurrenceID", use it.

First release, no fuzzy matching. Then, think about it for later releases

Check these out:

* [https://github.com/cyber4paleo/cyber4paleo.github.io/blob/master/_projects/team_paleoapi.md](https://github.com/cyber4paleo/cyber4paleo.github.io/blob/master/_projects/team_paleoapi.md)
* [https://github.com/cyber4paleo/cyber4paleo.github.io/blob/master/_projects/team_darwin.md](https://github.com/cyber4paleo/cyber4paleo.github.io/blob/master/_projects/team_darwin.md)
* [https://github.com/scottsfarley93/niche-API](https://github.com/scottsfarley93/niche-API)

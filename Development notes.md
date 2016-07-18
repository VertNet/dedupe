De-duplication service (dev notes)
===

<!-- MarkdownTOC -->

1. [Key points](#key-points)
1. [File extensions and `Content-Type` values](#file-extensions-and-content-type-values)
1. [Wild ideas](#wild-ideas)
1. [Initial meeting](#initial-meeting)
1. [Usage](#usage)
1. [How to handle content](#how-to-handle-content)
    1. [file on `POST` body](#file-on-post-body)
        1. [`self.request.body_file`](#selfrequestbody_file)
        1. [\(fixed\) Problem with newlines](#fixed-problem-with-newlines)
    1. [email on `querystring`](#email-on-querystring)
        1. [\(fixed\) body not read if email is read first](#fixed-body-not-read-if-email-is-read-first)
    1. [identify the 'id' field](#identify-the-id-field)
1. [How to find duplicates](#how-to-find-duplicates)
    1. [`memcache`](#memcache)
    1. [hashing](#hashing)
    1. [isolating requests](#isolating-requests)
    1. [is datastore better?](#is-datastore-better)
    1. [cleaning up namespaces](#cleaning-up-namespaces)
    1. [Final decision](#final-decision)
1. [How to build the report](#how-to-build-the-report)
1. [How to deliver results](#how-to-deliver-results)

<!-- /MarkdownTOC -->





<a name="key-points"></a>
# Key points

- Content of file must be sent via the `body` of the request
- Data will be read in streaming
- Email must be sent in the querystring, parameter `email`
- Name of the ID field should be sent in the querystring, parameter `id`
- Fields for partial duplicates will be sent in the querystring, parameter `fields`
- `Content-Type` and file extension will be used to determine file format, in that order. [See table below](#file-extensions-and-content-type-values) for examples.
- Each request will operate in its own `namespace`
- Full duplicates will be checked with `md5` hashes





<a name="file-extensions-and-content-type-values"></a>
# File extensions and `Content-Type` values

| File type | Extension | `Content-Type` |
|--------|----------------|---------------|
| CSV | `.csv` | `text/csv` |
| Tab separated | `.txt` | `text/tab-separated-values` |
| Tab separated | `.tsv` | `text/tab-separated-values` |
| DarwinCore Archive | `.zip` | `application/zip` |
| DarwinCore Archive (preferred) | `.zip` | `application/x-dwca` |
| JSON | `.json` | `application/json` |




<a name="wild-ideas"></a>
# Wild ideas

- Accept csv, txt, json and dwca (zip)





<a name="initial-meeting"></a>
# Initial meeting

RESTful API. Flag duplicates in trivial and non-trivial ways:

1. Trivial: actual duplicates
1. Non-trivial: potential duplicates, like herbarium duplicates, where locality, date, collector and taxon are the same

The result is the dataset with flags. These flags indicate actual/potential duplicates. Also, add a "reason" field.

Workflow:

1. Submit a dataset
1. Depending on the f(x) (or argument/s):
    1. Return a report
    1. Return the dataset with flags
    1. Return the dataset with no strict duplicates
    1. Return the dataset with no duplicates, strict or not

Add an internal "id" to reference records: "Record id 5 is the same as record id 1".

If dataset has "occurrenceID", use it.

First release, no fuzzy matching. Then, think about it for later releases

Check these out:

* [https://github.com/cyber4paleo/cyber4paleo.github.io/blob/master/_projects/team_paleoapi.md](https://github.com/cyber4paleo/cyber4paleo.github.io/blob/master/_projects/team_paleoapi.md)
* [https://github.com/cyber4paleo/cyber4paleo.github.io/blob/master/_projects/team_darwin.md](https://github.com/cyber4paleo/cyber4paleo.github.io/blob/master/_projects/team_darwin.md)
* [https://github.com/scottsfarley93/niche-API](https://github.com/scottsfarley93/niche-API)





<a name="usage"></a>
# Usage

Via `POST` requests, sending the content of the file in the body.

Methods:

Report:

```bash
curl -X POST -H "Content-Type: text/csv" --data-binary @file http://<service_url>/api/<version>/report?email=foo@bar.baz
```





<a name="how-to-handle-content"></a>
# How to handle content

<a name="file-on-post-body"></a>
## file on `POST` body

The first big problem is how to deal with file uploads. Since I'm building an API, I cannot provide a form for file uploads (that should be a client instead). Also, I cannot accept the path to a file and make the API "take" it from that path, so I guess **the content will have to go in the body of the request**.

I have been exploring how to properly store the data and it seems it will have to go to **cloud storage**, so I'd better create a new bucket for it. Other options were:

* The Blobstore: Google now recommends switching to cloud storage instead (see first line [here](https://cloud.google.com/appengine/docs/python/blobstore/))
* Streaming data: that would be nice for small files, but what if the data exceeds the 128Mb memory limit? Not an option, I'm afraid.

Still, in order to send big files to Cloud Storage, they need to go via instances, so the 128Mb limit still applies? **Let's try for now with data streaming**.

Primary way of sending data will be CSV|TXT. I'll also support JSON and DWCA.

<a name="selfrequestbody_file"></a>
### `self.request.body_file`

Looks like the `self.request` object has both a `body` and a `body_file` attributes, which hold the data content and the data as a (open) file-like object (`cStringIO.StringI`). This enables more memory-efficient data stream.

<a name="fixed-problem-with-newlines"></a>
### (fixed) Problem with newlines

It seems the `body` of the request comes with no newline whatsoever by default. I don't know if this is because of the AppEngine configuration not ready to handle `\n` characters as newlines or any other problem. Will have to investigate...

See [this question on StackOverflow](http://stackoverflow.com/questions/38328864/newlines-removed-in-post-request-body-google-app-engine/38330965)

It seems it had nothing to do with App Engine, but with `curl`. From the docs

> -d, --data <data>

>[...]

> If you start the data with the letter @, the rest should be a file name to read the data from, or - if you want curl to read the data from stdin. Multiple files can also be specified. Posting data from a file named 'foobar' would thus be done with --data @foobar. When --data is told to read from a file like that, carriage returns and newlines will be stripped out.

And

> --data-binary <data>

> (HTTP) This posts data exactly as specified with no extra processing whatsoever.

> If you start the data with the letter @, the rest should be a filename. Data is posted in a similar manner as --data-ascii does, except that newlines and carriage returns are preserved and conversions are never done.

So the `curl` call shouldn't use `-d`, but `--data-binary`.

<a name="email-on-querystring"></a>
## email on `querystring`

When the file is too large to be parsed in the typical request time, the ideal situation would be to send it to the background and send a notification email whenever finished. Email data can be sent in the `querystring`, so the request is:

```bash
curl -i -X POST --data-binary @file.csv <url>?email=foo@bar.baz
```

<a name="fixed-body-not-read-if-email-is-read-first"></a>
### (fixed) body not read if email is read first

I get the following error when adding a `self.request.get('email', None)` before parsing the body:

```
ERROR    2016-07-14 08:07:44,352 webapp2.py:1552] 'FakeCGIBody' object has no attribute 'file'
Traceback (most recent call last):
  File "/home/jotegui/dev/google-cloud-sdk/platform/google_appengine/lib/webapp2-2.5.2/webapp2.py", line 1535, in __call__
    rv = self.handle_exception(request, response, e)
  File "/home/jotegui/dev/google-cloud-sdk/platform/google_appengine/lib/webapp2-2.5.2/webapp2.py", line 1529, in __call__
    rv = self.router.dispatch(request, response)
  File "/home/jotegui/dev/google-cloud-sdk/platform/google_appengine/lib/webapp2-2.5.2/webapp2.py", line 1278, in default_dispatcher
    return route.handler_adapter(request, response)
  File "/home/jotegui/dev/google-cloud-sdk/platform/google_appengine/lib/webapp2-2.5.2/webapp2.py", line 1102, in __call__
    return handler.dispatch()
  File "/home/jotegui/dev/google-cloud-sdk/platform/google_appengine/lib/webapp2-2.5.2/webapp2.py", line 572, in dispatch
    return self.handle_exception(e, self.app.debug)
  File "/home/jotegui/dev/google-cloud-sdk/platform/google_appengine/lib/webapp2-2.5.2/webapp2.py", line 570, in dispatch
    return method(*args, **kwargs)
  File "/home/jotegui/Dropbox/Projects/VertNet/dedupe/Report/ReportAPI.py", line 97, in post
    self.file = self.request.body_file.file
AttributeError: 'FakeCGIBody' object has no attribute 'file'
```

I don't really know what does that mean, but it has to do with the addition of the previous line.

If I switch the order, then the file is stored but there is no line to read.

**OK, found it!** It has to do with the type of object that gets created by `WebOb` to store the value of the `body` content. If no `querystring` is provided, the parser detects the `body` object to be a file-like object and, therefore, assigns it to some sort of `cStringIO.StringI` object. But when adding the `querystring`, things get messed up. The `body` gets inserted into a `FakeCGIBody`, which doesn't have a `file` member, so the usual way of reading doesn't work.

How to fix it? Using a `Content-Type` header. If the request specifies a `Content-Type` of `text/csv` or `text/plain`, the `body` becomes a `LimitedLengthFile` object (with a `cStringIO.StringI` file object and a `maxlength` attribute). Now, I can safely use the `.file` propery again.

<a name="identify-the-id-field"></a>
## identify the 'id' field

A key component is the "id" field, because it will serve as an identifier for which record the duplicate is duplicate of. Both in the case of the report and the flag methods, each duplicate will show the id of the "original" record.

In principle, DWCAs will have either the `occurrenceid` or an `id` field, or an "id" can be determined from the `meta.xml` file. However, this might not be the case. I should offer a way of specifying the "id" field.

A first option, that overrides anything else, is to look for an `id` parameter in the `querystring`. If there is no such parameter, I can look for an `id` field, then an `occurrenceid` field.

But what if none is present? Should I throw a warning? Stop with an error? Go ahead with the first column? With no "id" reference, just the position in the record set?

So far, I made the API return a 400 error if the field specified as "id" is not among the headers. The only thing left here is to determine what to do when no suitable "id" field is present.





<a name="how-to-find-duplicates"></a>
# How to find duplicates

I found [this post on StackOverflow](http://stackoverflow.com/a/12937827/1379488) that shows how to use `set` for efficient duplicate flagging. This is good for small files, but what for bigger ones? What if the set grows beyond the max memory?

<a name="memcache"></a>
## `memcache`

`memcache` by itself won't work, since the `key` of each entry must not exceed 250 bytes (2K ascii characters). A sample subset of a dwca (with no long comment fields or remarks) shows a ~1300 bit mean length, so the 2K is really close.

<a name="hashing"></a>
## hashing

A nice option would be `memcache` with hashed lines... See [this post on StackOverflow](http://stackoverflow.com/a/29880709/1379488). It says that `md5` might be a good option. However, there's the remote possibility that two different lines produce the same hash. There's also `sha256`, which will reduce significantly the probability of overlapping because it produces a hash twice as long.

Still, an `md5` string is 128 bits and `sha256` takes 32b bytes (256 bits) per hash, and shared `memcache` doesn't guarantee availability... With `sha256`, 27 million records are transformed to 864MB, so even if it would fit in local memory, it won't work for GAE 128MB VMs, and shared `memcache` could be unreliable... I doubt we receive 27M rows in a single call. And we can always add a hard limit to the size of the file.

<a name="isolating-requests"></a>
## isolating requests

If I plan to use `memcache`, I should also prepend a string that uniquely identifies the request, so that sets from one request are not mixed with a different one. Or, better, [use `namespaces` to isolate `memcache` among requests](https://cloud.google.com/appengine/docs/python/multitenancy/#Python_App_Engine_APIs_that_use_namespaces).

<a name="is-datastore-better"></a>
## is datastore better?

Another option could be to calculate hashes and store them in the datastore, but "thanks" to the *eventual consistency*, I think this is not a good option... Nah, checking the docs reveals that the write throughput is ~ 1 commit / second. Definitely too slow for these purposes.

<a name="cleaning-up-namespaces"></a>
## cleaning up namespaces

I have been exploring how to delete `memcache` keys from a namespace and it seems there is no option for doing that, except to keep track of the keys and do a `delete_multi`. This is not a good option since it means using instance memory for memcache and effectively duplicating the key storage. However, [Comment #5 of this thread](https://code.google.com/p/googleappengine/issues/detail?id=3994#c5) says that there is actually no need of doing this, since unused keys will be removed eventually as memory is needed.

Also, there is no way of removing a `namespace` ([see the API reference](https://cloud.google.com/appengine/docs/python/refdocs/google.appengine.api.namespace_manager.namespace_manager)) but by removing all elements in that `namespace`. So I guess the cleaning of namespaces will be a slow and painful process where older `memcache` keys are slowly being deleted and, whenever the last key is removed, the `namespace` itself will disappear.

Therefore, no `namespace` cleanup.

<a name="final-decision"></a>
## Final decision

So, I guess the best option is to:

1. Create a temporary `namespace` for the request
1. Get the file
1. Read a line
1. Calculate the line hash with `md5`
1. Check if it already exists in `memcache`
    1. If so, add line data to report
    1. If not, add line hash to `memcache`
1. Repeat until end of file
1. Let `memcache` items and `namespace` die slow and painfully

<a name="how-to-build-the-report"></a>
# How to build the report

Duplicate pairs





<a name="how-to-deliver-results"></a>
# How to deliver results

Sometimes, it might take longer than the 60 second limit to return results. Maybe I can add a `try-catch` block to check for `DeadlineExceededError` and, if so, launch a task to continue working. In any case, the user should provide a notification email to be able to receive the results.
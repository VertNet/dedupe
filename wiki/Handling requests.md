# De-duplication service dev notes: Building requests

<!-- MarkdownTOC -->

1. [Example](#example)
    1. [cURL](#curl)
1. [Limitations](#limitations)
    1. [Method](#method)
    1. [Request size](#request-size)
1. [Headers](#headers)
    1. [`Content-Type`](#content-type)
1. [Parameters](#parameters)
    1. [`action`](#action)
    1. [`duplicates`](#duplicates)
    1. [`email`](#email)
    1. [`id`](#id)
    1. [`POST` body: file](#post-body-file)
1. [Problems](#problems)
    1. [`self.request.body_file`](#selfrequestbody_file)
    1. [\(fixed\) Problem with newlines](#fixed-problem-with-newlines)
    1. [\(fixed\) body not read if email is read first](#fixed-body-not-read-if-email-is-read-first)

<!-- /MarkdownTOC -->

<a name="example"></a>
# Example

<a name="curl"></a>
## cURL

```bash
curl -X POST -H "Content-Type: text/csv" --data-binary @file.csv http://<service_url>/api/<version>/dedupe?action=remove&duplicates=strict&email=foo@bar.baz&id=occurrenceid
```

<a name="limitations"></a>
# Limitations

<a name="method"></a>
## Method

Only `POST` methods will be allowed. `GET` isn't designed to send large content, and any other method doesn't really make sense.

<a name="request-size"></a>
## Request size

[According to the docs](https://cloud.google.com/appengine/docs/python/how-requests-are-handled#Python_Quotas_and_limits), there is a 32Mb limit on request size

<a name="headers"></a>
# Headers

<a name="content-type"></a>
## `Content-Type`

Since it can be pretty hard to reliably determine the file type (I'm planning on allowing several different formats), I'd rather make the users explicitly indicate the type of file they are sending to the service. To do that, instead of adding another parameter, the service makes use of the `Content-Type` header.

Currently, these are the supported file types and their corresponding `Content-Type` value:

| File type | Implemented | Extension | `Content-Type` |
|-----------|:-----------:|:---------:|---------------:|
| CSV | * | `.csv` | `text/csv` |
| Tab separated | * | `.txt` or `tsv` | `text/tab-separated-values` |
| DarwinCore Archive |  | `.zip` | `application/zip` |
| DarwinCore Archive (preferred) |  | `.zip` | `application/x-dwca` |
| JSON |  | `.json` | `application/json` |

Note the (future) use of `application/x-dwca` for DarwinCore Archives. Even if they are zip files, they are a special type of them, in the sense that (ideally) all share the same structure, and these zip files could be different than other zip files. For example, if a user sends a DWCA with a custom `id` field, this field will be reflected in the `meta.xml` file, so the service might be able to parse this file looking for the proper value of the `id` field.

<a name="parameters"></a>
# Parameters

<a name="action"></a>
## `action`

Initially, I thought I could offer different endpoints, one for each action. But since most of the logic is the same, I now think it makes more sense to offer a single endpoint and determine the action with a parameter. The most logic name for this parameter is `action`.

`action` can be one of those:


| `action` | Default | Effect |
|:--------:|:-------:|--------|
| `report` |  | Returns a JSON document with duplicate information. Doesn't alter the file in any way |
| `flag` | * | Adds new flag field/s to the data set indicating which record is duplicate and with reference to the original record |
| `remove` |  | Returns the data set with all duplicates removed |

More can be added as needed.

<a name="duplicates"></a>
## `duplicates`

In order to offer a wide range of possibilities, I'm thinking on adding a new parameter to the call, called `duplicates`, in which people can decide which type of duplicate they want to remove. So far, I've implemented functions for these:

| `duplicates` | Default | Effect |
|:------------:|:-------:|--------|
| `strict` |  | Only identical rows will be considered duplicates |
| `partial` |  | Only rows with the same key information (locality, scientific name, date and collector) will be considered duplicates |
| `all` | * | All the previous types apply |

<a name="email"></a>
## `email`

Since the deduplication tasks will be held in the background, the service needs a way of delivering the results to the user. The best way to do this, just like with the Download API service, is to send a notification to the user's email address with a link to the parsed file.

<a name="id"></a>
## `id`

A key component is the "id" field, because it will serve as an identifier for which record the duplicate is duplicate of. Both in the case of the report and the flag methods, each duplicate will show the id of the "original" record.

In principle, DWCAs will have either the `occurrenceid` or an `id` field, or an "id" can be determined from the `meta.xml` file. However, this might not be the case. I should offer a way of specifying the "id" field.

A first option, that overrides anything else, is to look for an `id` parameter in the `querystring`. If there is no such parameter, I can look for an `id` field, then an `occurrenceid` field.

But what if none is present? Should I throw a warning? Stop with an error? Go ahead with the first column? With no "id" reference, just the position in the record set?

So far, I made the API return a 400 error if the field specified as "id" is not among the headers. The only thing left here is to determine what to do when no suitable "id" field is present.

I guess, for now, I will omit the "duplicate ids" field if no "id" field can be properly detected, without stoping the process.

<a name="post-body-file"></a>
## `POST` body: file

The first big problem is how to deal with file uploads. Since I'm building an API, I cannot provide a form for file uploads (that should be a client instead). Also, I cannot accept the path to a file and make the API "take" it from that path, so I guess **the content will have to go in the body of the request**.

I have been exploring how to properly store the data and it seems it will have to go to **cloud storage**, so I'd better create a new bucket for it. Other options were:

* The Blobstore: Google now recommends switching to cloud storage instead (see first line [here](https://cloud.google.com/appengine/docs/python/blobstore/))
* Streaming data: that would be nice for small files, but what if the data exceeds the 128Mb memory limit? Not an option, I'm afraid.

Still, in order to send big files to Cloud Storage, they need to go via instances, so the 128Mb limit still applies? Let's try for now with data streaming.

**UPDATE**: I'm switching to tasks for the heavy part of the work. Tasks have a hard limit of 100Kb in size, so there is no way of streaming the content of regular files to tasks. Therefore, streaming data is not an option. Files will go directly to cloud storage.

Something for extreme testing: see if files larger than 32Mb (request limit) can be sent and, if not, how to make it happen.

<a name="problems"></a>
# Problems

<a name="selfrequestbody_file"></a>
## `self.request.body_file`

Looks like the `self.request` object has both a `body` and a `body_file` attributes, which hold the data content and the data as a (open) file-like object (`cStringIO.StringI`). This enables more memory-efficient data stream.

<a name="fixed-problem-with-newlines"></a>
## (fixed) Problem with newlines

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

<a name="fixed-body-not-read-if-email-is-read-first"></a>
## (fixed) body not read if email is read first

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

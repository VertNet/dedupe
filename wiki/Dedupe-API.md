Deduplication service
===

<!-- MarkdownTOC -->

1. [Introduction](#introduction)
    1. [Location and version](#location-and-version)
1. [Sending requests to the API](#sending-requests-to-the-api)
    1. [General request process](#general-request-process)
    1. [Request headers](#request-headers)
    1. [Query-string arguments](#query-string-arguments)
    1. [Sending the file itself](#sending-the-file-itself)
1. [Retrieving the response](#retrieving-the-response)
    1. [Immediate response](#immediate-response)
    1. [Downloading the parsed file](#downloading-the-parsed-file)
1. [Bugs and feedback](#bugs-and-feedback)

<!-- /MarkdownTOC -->

<a name="introduction"></a>
# Introduction

The `dedupe` method of the API offers a way of detecting several types of duplicate records in primary biodiversity data sets. Apart from proper record duplicates, this method also provides a way of detecting, flagging and/or removing potential or partial duplicates -- *i.e*, records that have the same information in certain key fields.

This method works asynchronously, meaning that the API returns almost as soon as the file has been uploaded to the server and lets the hard work for background threads. Notifications of results are later delivered via email to the user.

<a name="location-and-version"></a>
## Location and version

See the [documentation home page](http://www.github.com/VertNet/dedupe/wiki) for information on the current URL to access the service.

<a name="sending-requests-to-the-api"></a>
# Sending requests to the API

<a name="general-request-process"></a>
## General request process

<a name="request-headers"></a>
## Request headers

<a name="query-string-arguments"></a>
## Query-string arguments

<a name="sending-the-file-itself"></a>
## Sending the file itself

<a name="retrieving-the-response"></a>
# Retrieving the response

<a name="immediate-response"></a>
## Immediate response

<a name="downloading-the-parsed-file"></a>
## Downloading the parsed file

<a name="bugs-and-feedback"></a>
# Bugs and feedback
Asynchronous tasks are a bit tricky in the sense that the user cannot know if the process is running smoothly or if something wrong happened. The service has been designed to inform promptly of any failure that could happen during the de-duplication process, both to the user and the service administrator, but it is very difficult to foresee all that can potentially go wrong, and the service may break without notice.

If, for some reason, you don't receive a notification of your file being ready after 24h, please create a new issue in the code repository http://www.github.com/vertnet/dedupe/issues and/or send us an email at vertnetinfo@vertnet.org
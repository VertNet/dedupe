# De-duplication service dev notes: Detecting duplicates

<!-- MarkdownTOC -->

1. [Strict duplicates](#strict-duplicates)
    1. [`memcache`](#memcache)
    1. [hashing](#hashing)
    1. [isolating requests](#isolating-requests)
    1. [is datastore better?](#is-datastore-better)
    1. [cleaning up namespaces](#cleaning-up-namespaces)
1. [Partial duplicates](#partial-duplicates)
1. [Fuzzy duplicates](#fuzzy-duplicates)

<!-- /MarkdownTOC -->

<a name="strict-duplicates"></a>
# Strict duplicates

I found [this post on StackOverflow](http://stackoverflow.com/a/12937827/1379488) that shows how to use `set` for efficient duplicate flagging. This is good for small files, but what for bigger ones? What if the set grows beyond the max memory?

<a name="memcache"></a>
## `memcache`

`memcache` by itself won't work, since the `key` of each entry must not exceed 250 bytes (2K ascii characters). A sample subset of a dwca (with no long comment fields or remarks) shows a ~1300 bit mean length, so the 2K is really close.

<a name="hashing"></a>
## hashing

A nice option would be `memcache` with hashed lines... See [this post on StackOverflow](http://stackoverflow.com/a/29880709/1379488). It says that `md5` might be a good option. However, there's the remote possibility that two different lines produce the same hash. **UPDATE**: I checked both with John and Rob and they agree we can live with the extremely low possibility of getting these false positives.

There's also `sha256`, which will reduce significantly the probability of overlapping because it produces a hash twice as long. Still, an `md5` string is 128 bits and `sha256` takes 32b bytes (256 bits) per hash, and shared `memcache` doesn't guarantee availability... With `sha256`, 27 million records are transformed to 864MB, so even if it would fit in local memory, it won't work for GAE 128MB VMs, and shared `memcache` could be unreliable... I doubt we receive 27M rows in a single call. And we can always add a hard limit to the size of the file.

This is something for limit testing.

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

<a name="partial-duplicates"></a>
# Partial duplicates

As Rob suggested, we also need to provide the way of detecting partial duplicates. These will be determined based on four criteria:

* Same locality information
* Same date information
* Same taxonomic information
* Same collector information

The standard fields for those data are, respectively, `locality`, `eventDate`, `scientificName` and `recordedBy`. However, in order to provide as much flexibility as possible, we could let users add a list of the fields that will form a duplicate. I see two options:

1. Provide individual arguments for each of the four elements
1. Provide a single argument to be filled with a list of one or more fields

Something for a later release.

The process of detecting the duplicates is similar to the one for strict duplicates, with two differences:

* The key is calculated by concatenating the values of the four fields separated by the pipe (`|`) character, and not the whole line
* The key is not hashed (it is short enough to fit in `memcache`, so far...)

<a name="fuzzy-duplicates"></a>
# Fuzzy duplicates

Something for later releases.
# De-duplication service dev notes: Available actions

<!-- MarkdownTOC -->

1. [`report`](#report)
    1. [New version](#new-version)
1. [`remove`](#remove)
1. [`flag`](#flag)

<!-- /MarkdownTOC -->

<a name="report"></a>
# `report`

When using the `report` method, users will receive a JSON-like document specifying the duplicates in their records. The document will have the following structure:

```json
{
    "email": "Email to send notification to",
    "fields": "Number of fields of the data set",
    "records": "Number of records parsed (with duplicates)",
    "warnings": "List of warning messages, if any",
    "file": "Link to the generated file. Only if 'action' is 'remove' or 'flag'",
    "strict_duplicates": {
        "count": "Number of rows that are exact copies of other rows",
        "ids": "List consisting of the IDs of the duplicate rows. Only if ID field is provided or can be determined",
        "index_pairs": "List consisting of the positions of duplicate record pairs. Only if 'count' > 0"
    },
    "partial_duplicates": {
        "count": "Number of rows that are partial copies of other rows",
        "ids": "List consisting of the IDs of the duplicate rows. Only if ID field is provided or can be determined",
        "index_pairs": "List consisting of the positions of duplicate record pairs. Only if 'count' > 0"
    },
    "To be continued..."
}
```

<a name="new-version"></a>
## New version

Actually, since we are no longer offering direct parsing of files, offering a JSON-like object with such information makes no sense. All people will receive is an email with the information.

In fact, I don't think people will ever use this function alone. I'll add the default to "flag" instead.

<a name="remove"></a>
# `remove`

Pretty self-explanatory. The resulting file will omit duplicate rows.

<a name="flag"></a>
# `flag`

This is the default action, as of Aug-4. The reasoning behind switching from `report` to `flag` is that, first, I don't think people will use this function that often and, second, I'd rather make people receive more rather than less information, so `flag` instead of `remove` for the default.

A recent conversation with John helped me clarify certain aspects of duplicate flagging. Here are the ideas:

* Add three fields to the dataset: `isDuplicate`, `duplicateType` and `duplicateOf`
* `isDuplicate` is a boolean field indicating whether or not the row is a duplicate of another row
* `dupicateType` is a controlled vocabulary indicating the type of duplicate: `full`, `partial` or any other
* `duplicateOf` is a list of all the other record IDs for which the current record is a duplicate. Even for strict duplicates, for the sake of consistency, it makes sense to make this field a list.
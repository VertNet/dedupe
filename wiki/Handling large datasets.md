# De-duplication service dev notes: Handling large datasets

<!-- MarkdownTOC -->

1. [Tasks](#tasks)
    1. [\(ignored\) only `next` sent in `file` parameter](#ignored-only-next-sent-in-file-parameter)
    1. [\(issue-bypassed\) only 100K tasks can be enqueued](#issue-bypassed-only-100k-tasks-can-be-enqueued)
1. [Google Cloud Storage](#google-cloud-storage)
    1. [Installing and configuring Google Cloud Storage](#installing-and-configuring-google-cloud-storage)
    1. [Storing original file](#storing-original-file)
    1. [Getting the original file from the Cloud Storage](#getting-the-original-file-from-the-cloud-storage)

<!-- /MarkdownTOC -->

<a name="tasks"></a>
# Tasks

Sometimes, it might take longer than the 60 second limit to return results. Maybe I can add a `try-catch` block to check for `DeadlineExceededError` and, if so, launch a task to continue working. In any case, the user should provide a notification email to be able to receive the results.

Actually, I have decided (for the first version) to **directly send tasks to the taskqueue** and receive whichever result (even reports) via email. This is in principle easier than trying-catching, and I will deal with direct works later.

<a name="ignored-only-next-sent-in-file-parameter"></a>
## (ignored) only `next` sent in `file` parameter

The first issue I have so far encountered is that, when I send the `POST` request to the Task handler, using `params` and `self.request.get()`, only the `first` line of the file is sent, either in `self.file` or in `self.reader`. I guess it might be a matter of newlines...

I should try sending data via `payload` instead, to see if that fixes the issue.

When trying to fix this issue, I found the following:

<a name="issue-bypassed-only-100k-tasks-can-be-enqueued"></a>
## (issue-bypassed) only 100K tasks can be enqueued

No dice. There is a **maximum allowed size for tasks**, which is currently **102400 bytes**. Testing with my 23M (~16K lines) file, I get 29.138.038 bytes of data, so in principle **any file larger than 100K cannot be sent via tasks**.

Therefore, the only solution I can think of is to store the file directly from the API handler and make the tasks work on there.

<a name="google-cloud-storage"></a>
# Google Cloud Storage

<a name="installing-and-configuring-google-cloud-storage"></a>
## Installing and configuring Google Cloud Storage

GCS is not included in the default App Engine distro, so we need to download the client and load it in the packages. To do that, first "install" the module:

```bash
pip install GoogleAppEngineCloudStorageClient -t ./lib
```

Before the importing can be made effective, we need a way to tell GAE where to find the `cloudstorage` package. Editing `appengine_config.py`.

```py
# appengine_config.py
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
```

And now we can safely add the following `import` statement in the code

```py
import cloudstorage as gcs
```

I have created the `vn-dedupe` bucket. We add that as the default bucket. Also, I have configured the bucket to automatically remove all files older than 1 day.

<a name="storing-original-file"></a>
## Storing original file

As I said in another notebook, I am creating a separate namespace for each request. The name of the original file will be the name of the namespace plus "orig" plus the file extension (`.txt` or `.csv`), and it will be stored in the `vn-dedupe` bucket.

Then, the API handler will send the name of the file in the params to the Task handler.

<a name="getting-the-original-file-from-the-cloud-storage"></a>
## Getting the original file from the Cloud Storage


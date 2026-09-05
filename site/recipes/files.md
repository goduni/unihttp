---
title: Upload files with multipart forms
description: Send a file and form fields with unihttp File, Form, and UploadFile, including filenames and content types.
---

# Upload files with multipart forms

Use `File` for the binary payload and `Form` for associated scalar fields.
With `User` as the response model, define:

```python
--8<-- "examples/recipes.py:upload"
```

The declaration above needs these imports, plus the `User` response model from
the [quickstart](../getting-started/quickstart.md):

```python
from dataclasses import dataclass

from unihttp.bind_method import bind_method
from unihttp.http import UploadFile
from unihttp.markers import File, Form, Path
from unihttp.method import BaseMethod
```

Bind it as
`upload_avatar = bind_method(UploadAvatar)`.

With a configured client:

```python
from unihttp.http import UploadFile

user = client.upload_avatar(
    user_id=1,
    caption="portrait",
    avatar=UploadFile(
        b"image bytes",
        filename="ada.png",
        content_type="image/png",
    ),
)
```

For real files, open the input in binary mode and keep it open until the
request completes. Use a valid payload matching your declared content type.

Do not combine `Body` with `File`: use `Form` for multipart metadata.
Allow the transport to set the multipart boundary instead of hard-coding a
`Content-Type` header. Confirm file representations supported by your
[backend](../integrations/backends.md).

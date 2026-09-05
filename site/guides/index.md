---
title: User guide
description: "Find unihttp guides by task: declare requests, configure clients, serialize models, and handle responses, errors, and streaming."
---

# User guide

Start with the part of your client you are working on. Each guide explains the
behavior and links to a focused example or the corresponding API reference.
You do not need to read these pages in order.

**New to unihttp?** [Install it](../getting-started/installation.md), then follow
either the [sync](../getting-started/quickstart.md) or
[async quickstart](../getting-started/async.md). Both build the same API client.

## Requests

Define what each endpoint sends.

- [Methods and parameters](methods.md): URLs, HTTP verbs, path and query
  parameters, headers, JSON bodies, and method binding.
- [Optional fields and Omitted](../recipes/partial-updates.md): distinguish a
  missing field from an explicit null.
- [File uploads](../recipes/files.md): send multipart files and form fields.

## Clients and middleware

Choose how requests are sent and what runs around each call.

- [HTTP backends](../integrations/backends.md): compare sync and async clients,
  configure sessions, and switch transports.
- [Middleware](middleware.md): apply behavior per client or per method and
  understand request/response ordering.
- [Authentication](../recipes/authentication.md): attach bearer tokens through
  middleware.

## Serialization

Choose how method fields become request data and responses become Python models.

- [Serialization](serialization.md): connect Adaptix, Pydantic, or msgspec;
  customize field names and values; distinguish model conversion from JSON encoding.

## Responses and errors

Decide what your client returns and how it handles failures.

- [Response data and metadata](responses.md): return typed results with status
  codes and headers when needed.
- [Error handling](errors.md): validate responses and map HTTP statuses to
  application exceptions.
- [Retries](../recipes/retries.md): configure bounded retries and correct
  middleware ordering for calls that are safe to repeat.
- [Streaming downloads](streaming.md): consume response chunks and close streams.

## Need an exact signature?

The [API reference](../reference/index.md) lists public types, constructor
arguments, protocols, and hooks. Use it for symbol lookup; use these guides for
behavior and examples.

---
title: Serializers
description: RequestDumper and ResponseLoader protocols and built-in Adaptix, Pydantic, and msgspec implementations.
---

# Serializers

A request dumper produces request parts; a response loader converts parsed data into the declared type. Both are explicitly supplied to the client. See [serialization](../guides/serialization.md) for compatibility limits. `DEFAULT_RETORT` is exported from `unihttp.serializers.adaptix` and should be extended with a keyword `recipe` to preserve unihttp providers.

::: unihttp.serialize.RequestDumper

::: unihttp.serialize.ResponseLoader

::: unihttp.serializers.adaptix.serialize.AdaptixDumper

::: unihttp.serializers.adaptix.serialize.AdaptixLoader

::: unihttp.serializers.pydantic.serialize.PydanticDumper

::: unihttp.serializers.pydantic.serialize.PydanticLoader

::: unihttp.serializers.msgspec.serialize.MsgspecDumper

::: unihttp.serializers.msgspec.serialize.MsgspecLoader

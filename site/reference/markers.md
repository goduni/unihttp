---
title: Markers and omitted values
description: Typed aliases for request locations and the sentinel used to omit fields.
---

# Markers and omitted values

Import aliases from `unihttp.markers`: `Path`, `Query`, `Header`, `Body`, `Form`, `File`, and `Raw`. Each is an `Annotated[T, Marker]` alias, so its Python value remains of type `T`. See the [wire-location table](../guides/methods.md#marker-reference). `Raw` currently requires Adaptix or a custom dumper.

Import `Omittable` and `Omitted` from `unihttp.omitted`. `Omittable[T]` means `T | Omitted`; use `Omitted()` as the default. [Optional fields and Omitted](../recipes/partial-updates.md) explains omission versus null, independently of the HTTP method.

`Omitted()` is a singleton. Since 0.4.0, shallow copies, deep copies, and pickle
round trips preserve its identity. See [copying and pickling](../recipes/partial-updates.md#copying-and-pickling).

::: unihttp.markers.Marker

::: unihttp.omitted.Omitted

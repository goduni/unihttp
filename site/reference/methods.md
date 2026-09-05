---
title: Methods and binding
description: Public method definitions, response hooks, and typed client binding.
---

# Methods and binding

Bind a method dataclass with `bind_method` to expose its constructor arguments on a client. Buffered calls return the declared model; streaming calls return an HTTP response containing a stream. Runtime-bound signatures depend on the supplied dataclass, so the generic signatures below describe the binding machinery rather than every generated endpoint.

::: unihttp.method.RequestMethod

::: unihttp.method.BaseMethod

::: unihttp.method.StreamMethod

::: unihttp.bind_method.bind_method

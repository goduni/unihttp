"""Scope retries to a buffered GET and map statuses after the last attempt."""

from unihttp.bind_method import bind_method
from unihttp.clients.httpx import HTTPXAsyncClient, HTTPXSyncClient
from unihttp.exceptions import NetworkError, RequestTimeoutError
from unihttp.middlewares import AsyncRetryMiddleware, RetryMiddleware

from examples.recipes import CreateUser, GetUser
from examples.response_errors import async_status_errors, status_errors


# --8<-- [start:sync]
class UserClient(HTTPXSyncClient):
    get_user = bind_method(
        GetUser,
        middleware=[
            status_errors,
            RetryMiddleware(
                retries=2,
                backoff=0.5,
                exceptions=[NetworkError, RequestTimeoutError],
                jitter=True,
            ),
        ],
    )
    create_user = bind_method(CreateUser, middleware=[status_errors])
    # --8<-- [end:sync]


# --8<-- [start:async]
class AsyncUserClient(HTTPXAsyncClient):
    get_user = bind_method(
        GetUser,
        middleware=[
            async_status_errors,
            AsyncRetryMiddleware(
                retries=2,
                backoff=0.5,
                exceptions=[NetworkError, RequestTimeoutError],
                jitter=True,
            ),
        ],
    )
    create_user = bind_method(CreateUser, middleware=[async_status_errors])
    # --8<-- [end:async]

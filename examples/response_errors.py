"""HTTP status mapping and application errors for the response guides."""

import logging
from dataclasses import dataclass

from unihttp.bind_method import bind_method
from unihttp.clients.httpx import HTTPXAsyncClient, HTTPXSyncClient
from unihttp.exceptions import (
    ClientError,
    HTTPStatusError,
    NetworkError,
    RequestTimeoutError,
    ServerError,
)
from unihttp.http.response import HTTPResponse
from unihttp.markers import Path
from unihttp.method import BaseMethod
from unihttp.middlewares import AsyncErrorMapperMiddleware, SyncErrorMapperMiddleware

from examples.recipes import GetUser, User, UserNotFound

logger = logging.getLogger(__name__)


# --8<-- [start:sync]
status_errors = SyncErrorMapperMiddleware({
    range(400, 500): ClientError,
    range(500, 600): ServerError,
})


class UserClient(HTTPXSyncClient):
    get_user = bind_method(GetUser, middleware=[status_errors])
    # --8<-- [end:sync]


# --8<-- [start:async]
async_status_errors = AsyncErrorMapperMiddleware({
    range(400, 500): ClientError,
    range(500, 600): ServerError,
})


class AsyncUserClient(HTTPXAsyncClient):
    get_user = bind_method(GetUser, middleware=[async_status_errors])
    # --8<-- [end:async]


# --8<-- [start:catch-sync]
def find_user(client: UserClient, user_id: int) -> User | None:
    try:
        return client.get_user(user_id=user_id)
    except UserNotFound:
        return None
    except HTTPStatusError as exc:
        logger.warning(
            "API returned HTTP %s (request ID: %s)",
            exc.status_code,
            exc.response.headers.get("X-Request-ID"),
        )
        raise
    except (NetworkError, RequestTimeoutError):
        logger.warning("The API request could not be completed")
        raise
    # --8<-- [end:catch-sync]


# --8<-- [start:catch-async]
async def find_user_async(client: AsyncUserClient, user_id: int) -> User | None:
    try:
        return await client.get_user(user_id=user_id)
    except UserNotFound:
        return None
    except HTTPStatusError as exc:
        logger.warning(
            "API returned HTTP %s (request ID: %s)",
            exc.status_code,
            exc.response.headers.get("X-Request-ID"),
        )
        raise
    except (NetworkError, RequestTimeoutError):
        logger.warning("The API request could not be completed")
        raise
    # --8<-- [end:catch-async]


# --8<-- [start:validation]
class APIError(Exception):
    pass


@dataclass
class GetValidatedUser(BaseMethod[User]):
    __url__ = "/users/{user_id}"
    __method__ = "GET"

    user_id: Path[int]

    def validate_response(self, response: HTTPResponse) -> None:
        if (
            response.ok
            and isinstance(response.data, dict)
            and response.data.get("ok") is False
        ):
            raise APIError(response.data.get("error", "Unknown API error"))

    # --8<-- [end:validation]

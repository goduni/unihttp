"""Reusable, tested examples for the documentation guides."""

from dataclasses import dataclass

from unihttp.bind_method import bind_method
from unihttp.clients.httpx import HTTPXSyncClient
from unihttp.http import UploadFile
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.markers import Body, File, Form, Path, Raw
from unihttp.method import BaseMethod, StreamMethod
from unihttp.middlewares.base import Handler, Middleware
from unihttp.omitted import Omittable, Omitted


# --8<-- [start:models]
@dataclass
class User:
    id: int
    name: str


@dataclass
class CreateUser(BaseMethod[User]):
    __url__ = "/users"
    __method__ = "POST"

    name: Body[str]
    # --8<-- [end:models]


# --8<-- [start:partial]
@dataclass
class UpdateUser(BaseMethod[User]):
    __url__ = "/users/{user_id}"
    __method__ = "PATCH"

    user_id: Path[int]
    name: Body[Omittable[str | None]] = Omitted()
    # --8<-- [end:partial]


# --8<-- [start:auth]
class BearerAuth(Middleware):
    def __init__(self, token: str) -> None:
        self.token = token

    def handle(self, request: HTTPRequest, next_handler: Handler) -> HTTPResponse:
        request.header["Authorization"] = f"Bearer {self.token}"
        return next_handler(request)

    # --8<-- [end:auth]


# --8<-- [start:upload]
@dataclass
class UploadAvatar(BaseMethod[User]):
    __url__ = "/users/{user_id}/avatar"
    __method__ = "POST"

    user_id: Path[int]
    caption: Form[str]
    avatar: File[UploadFile]
    # --8<-- [end:upload]


# --8<-- [start:stream]
@dataclass
class DownloadFile(StreamMethod):
    __url__ = "/files/{file_id}"
    __method__ = "GET"

    file_id: Path[int]
    # --8<-- [end:stream]


# --8<-- [start:errors]
class UserNotFound(Exception):
    pass


@dataclass
class GetUser(BaseMethod[User]):
    __url__ = "/users/{user_id}"
    __method__ = "GET"

    user_id: Path[int]

    def on_error(self, response: HTTPResponse) -> None:
        if response.status_code == 404:
            raise UserNotFound(self.user_id)

    # --8<-- [end:errors]


# --8<-- [start:raw]
@dataclass
class PutBytes(BaseMethod[dict[str, int]]):
    __url__ = "/blob"
    __method__ = "PUT"

    content: Raw[bytes]
    # --8<-- [end:raw]


class UserClient(HTTPXSyncClient):
    get_user = bind_method(GetUser)
    create_user = bind_method(CreateUser)
    update_user = bind_method(UpdateUser)
    upload_avatar = bind_method(UploadAvatar)
    download_file = bind_method(DownloadFile)

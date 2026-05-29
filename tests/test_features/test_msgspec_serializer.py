from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

import msgspec
import pytest

from unihttp.http import UploadFile
from unihttp.markers import Body, File, Form, Header, Path, Query
from unihttp.method import BaseMethod
from unihttp.serializers.msgspec import MsgspecDumper, MsgspecLoader


class User(msgspec.Struct):
    id: int
    name: str


def test_msgspec_loader():
    loader = MsgspecLoader()
    data = {"id": 1, "name": "Alice"}

    user = loader.load(data, User)
    assert isinstance(user, User)
    assert user.id == 1
    assert user.name == "Alice"


def test_msgspec_loader_list():
    loader = MsgspecLoader()
    data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

    users = loader.load(data, list[User])
    assert len(users) == 2
    assert users[0].name == "Alice"
    assert users[1].name == "Bob"


def test_msgspec_loader_validation_error():
    loader = MsgspecLoader()
    data = {"id": "not-an-int", "name": "Alice"}

    with pytest.raises(msgspec.ValidationError):
        loader.load(data, User)


@dataclass
class CreateUser(BaseMethod[User]):
    __url__ = "/users"
    __method__ = "POST"

    token: Header[str]
    user_id: Path[int]
    user: Body[User]
    q: Query[str] = "default"


class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass
class ComplexParams(BaseMethod[None]):
    __url__ = "/complex"
    __method__ = "GET"

    status: Query[Status]
    since: Query[datetime]
    tracking_id: Path[UUID]


@dataclass
class NestedBody(BaseMethod[None]):
    __url__ = "/bulk"
    __method__ = "POST"

    users: Body[list[User]]


@dataclass
class OptionalParams(BaseMethod[None]):
    __url__ = "/optional"
    __method__ = "GET"

    q: Query[str | None] = None
    limit: Query[int | None] = None


def test_msgspec_dumper_simple():
    dumper = MsgspecDumper()
    method = CreateUser(
        token="abc", user_id=123, user=User(id=1, name="John"), q="search"
    )

    result = dumper.dump(method)

    assert result["header"]["token"] == "abc"
    assert result["path"]["user_id"] == 123
    assert result["query"]["q"] == "search"
    assert result["body"]["user"] == {"id": 1, "name": "John"}


def test_msgspec_complex_types_serialization():
    dumper = MsgspecDumper()
    dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    uid = UUID("12345678-1234-5678-1234-567812345678")

    method = ComplexParams(status=Status.ACTIVE, since=dt, tracking_id=uid)

    result = dumper.dump(method)

    assert result["query"]["status"] == "active"
    assert result["query"]["since"] == "2023-01-01T12:00:00Z"
    assert result["path"]["tracking_id"] == "12345678-1234-5678-1234-567812345678"


def test_msgspec_nested_body_list():
    dumper = MsgspecDumper()
    users = [User(id=1, name="A"), User(id=2, name="B")]
    method = NestedBody(users=users)

    result = dumper.dump(method)

    assert result["body"]["users"] == [
        {"id": 1, "name": "A"},
        {"id": 2, "name": "B"},
    ]


def test_msgspec_optional_fields():
    dumper = MsgspecDumper()

    method = OptionalParams(q="search", limit=10)
    result = dumper.dump(method)
    assert result["query"]["q"] == "search"
    assert result["query"]["limit"] == 10

    method = OptionalParams()
    result = dumper.dump(method)
    assert result["query"]["q"] is None
    assert result["query"]["limit"] is None


@dataclass
class FileUpload(BaseMethod[None]):
    __url__ = "/upload"
    __method__ = "POST"

    file: File[UploadFile]
    description: Form[str]


def test_msgspec_dumper_upload():
    dumper = MsgspecDumper()
    uf = UploadFile(file=b"test", filename="test.txt", content_type="text/plain")
    method = FileUpload(file=uf, description="desc")

    result = dumper.dump(method)

    # UploadFile.to_tuple() returns (filename, content, content_type)
    assert result["file"]["file"] == ("test.txt", b"test", "text/plain")
    assert result["form"]["description"] == "desc"


def test_msgspec_dumper_no_markers_ignored():
    @dataclass
    class NoMarkerMethod(BaseMethod[None]):
        __url__ = "/"
        __method__ = "GET"
        internal: str  # No marker

    method = NoMarkerMethod(internal="secret")
    result = MsgspecDumper().dump(method)

    assert "internal" not in result.get("body", {})
    assert "internal" not in result.get("query", {})


def test_msgspec_dumper_fallback_on_exception():
    """Dumper falls back to __annotations__ if get_type_hints raises."""
    from unittest.mock import patch

    dumper = MsgspecDumper()
    method = CreateUser(token="abc", user_id=1, user=User(id=1, name="a"))

    with patch(
        "unihttp.serializers.msgspec.serialize.get_type_hints",
        side_effect=ValueError("Boom"),
    ):
        result = dumper.dump(method)

    assert result["header"]["token"] == "abc"


def test_msgspec_dumper_skips_dunder_and_untyped():
    dumper = MsgspecDumper()
    method = CreateUser(token="abc", user_id=1, user=User(id=1, name="a"))

    method.__dict__["__internal_state__"] = "ignore me"
    method.__dict__["dynamic_attr"] = "ignore me too"

    result = dumper.dump(method)

    assert "__internal_state__" not in result["body"]
    assert "dynamic_attr" not in result["body"]
    assert result["header"]["token"] == "abc"


@dataclass
class BytesBody(BaseMethod[None]):
    __url__ = "/bytes"
    __method__ = "POST"

    payload: Body[bytes]


def test_msgspec_dumper_bytes_base64():
    dumper = MsgspecDumper()
    method = BytesBody(payload=b"hello")

    result = dumper.dump(method)

    # msgspec.to_builtins encodes bytes as base64 (backend-specific behavior)
    assert result["body"]["payload"] == "aGVsbG8="

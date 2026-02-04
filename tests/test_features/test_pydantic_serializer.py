from pydantic import BaseModel

from unihttp.http import UploadFile
from unihttp.markers import Body, Header, Path, Query, File, Form
from unihttp.method import BaseMethod
from unihttp.serializers.pydantic import PydanticDumper, PydanticLoader


class User(BaseModel):
    id: int
    name: str


from dataclasses import dataclass


@dataclass
class CreateUser(BaseMethod[User]):
    __url__ = "/users"
    __method__ = "POST"

    token: Header[str]
    user_id: Path[int]
    user: Body[User]
    q: Query[str] = "default"


@dataclass
class FileUpload(BaseMethod[None]):
    __url__ = "/upload"
    __method__ = "POST"

    file: File[UploadFile]
    description: Form[str]


def test_pydantic_dumper_simple():
    dumper = PydanticDumper()
    user_data = User(id=1, name="John")
    method = CreateUser(token="abc", user_id=123, user=user_data, q="search")

    result = dumper.dump(method)

    assert result["header"]["token"] == "abc"
    assert result["path"]["user_id"] == 123
    assert result["query"]["q"] == "search"
    assert result["body"]["user"] == {"id": 1, "name": "John"}


def test_pydantic_dumper_upload():
    dumper = PydanticDumper()
    uf = UploadFile(file=b"test", filename="test.txt", content_type="text/plain")
    method = FileUpload(file=uf, description="desc")

    result = dumper.dump(method)

    # UploadFile.to_tuple() returns (filename, content, content_type)
    assert result["file"]["file"] == ("test.txt", b"test", "text/plain")
    assert result["form"]["description"] == "desc"


def test_pydantic_loader():
    loader = PydanticLoader()
    data = {"id": 1, "name": "Alice"}

    user = loader.load(data, User)
    assert isinstance(user, User)
    assert user.id == 1
    assert user.name == "Alice"


def test_pydantic_loader_list():
    loader = PydanticLoader()
    data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

    users = loader.load(data, list[User])
    assert len(users) == 2
    assert users[0].name == "Alice"
    assert users[1].name == "Bob"


def test_dumper_no_markers_ignored():
    """Fields without markers should be ignored or handled?
    Current implementation ignores them.
    """

    @dataclass
    class NoMarkerMethod(BaseMethod[None]):
        __url__ = "/"
        __method__ = "GET"
        internal: str  # No marker

    method = NoMarkerMethod(internal="secret")
    dumper = PydanticDumper()
    result = dumper.dump(method)

    # Internal should typically not be in any of the buckets if no marker
    assert "internal" not in result.get("body", {})
    assert "internal" not in result.get("query", {})


from enum import Enum
from datetime import datetime, timezone
from uuid import UUID
import pytest
from pydantic import ValidationError


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


def test_pydantic_complex_types_serialization():
    dumper = PydanticDumper()
    dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    uid = UUID("12345678-1234-5678-1234-567812345678")

    method = ComplexParams(
        status=Status.ACTIVE,
        since=dt,
        tracking_id=uid
    )

    result = dumper.dump(method)

    # Pydantic defaults: Enums -> value, UUID -> str, datetime -> ISO string
    assert result["query"]["status"] == "active"
    assert result["query"]["since"] == "2023-01-01T12:00:00Z"
    assert result["path"]["tracking_id"] == "12345678-1234-5678-1234-567812345678"


def test_loader_validation_error():
    loader = PydanticLoader()
    data = {"id": "not-an-int", "name": "Alice"}

    with pytest.raises(ValidationError):
        loader.load(data, User)


@dataclass
class NestedBody(BaseMethod[None]):
    __url__ = "/bulk"
    __method__ = "POST"

    users: Body[list[User]]


def test_pydantic_nested_body_list():
    dumper = PydanticDumper()
    users = [User(id=1, name="A"), User(id=2, name="B")]
    method = NestedBody(users=users)

    result = dumper.dump(method)

    assert result["body"]["users"] == [
        {"id": 1, "name": "A"},
        {"id": 2, "name": "B"}
    ]


@dataclass
class OptionalParams(BaseMethod[None]):
    __url__ = "/optional"
    __method__ = "GET"

    q: Query[str | None] = None
    limit: Query[int | None] = None


def test_pydantic_optional_fields():
    dumper = PydanticDumper()

    # Case 1: Provided value
    method = OptionalParams(q="search", limit=10)
    result = dumper.dump(method)
    assert result["query"]["q"] == "search"
    assert result["query"]["limit"] == 10

    # Case 2: None (Default)
    method = OptionalParams()
    result = dumper.dump(method)

    # Pydantic defaults often preserve None
    assert result["query"]["q"] is None
    assert result["query"]["limit"] is None

def test_pydantic_dumper_fallback_on_exception():
    """Test that Dumper falls back to __annotations__ if get_type_hints raises."""
    # To simulate get_type_hints failure, we can mock it
    from unittest.mock import patch
    
    dumper = PydanticDumper()
    method = CreateUser(token="abc", user_id=1, user=User(id=1, name="a"))
    
    with patch("unihttp.serializers.pydantic.serialize.get_type_hints", side_effect=ValueError("Boom")):
        result = dumper.dump(method)
            
    # Should still work via __annotations__
    assert result["header"]["token"] == "abc"

def test_pydantic_dumper_skips_dunder_and_untyped():
    dumper = PydanticDumper()
    method = CreateUser(token="abc", user_id=1, user=User(id=1, name="a"))
    
    # Manually add dunder and untyped attributes
    method.__dict__["__internal_state__"] = "ignore me"
    method.__dict__["dynamic_attr"] = "ignore me too"
    
    result = dumper.dump(method)
    
    assert "__internal_state__" not in result["body"]
    assert "dynamic_attr" not in result["body"]
    # Check that it didn't crash
    assert result["header"]["token"] == "abc"

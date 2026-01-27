from typing import get_args

from unihttp.markers import (
    Body,
    BodyMarker,
    File,
    FileMarker,
    Header,
    HeaderMarker,
    Path,
    PathMarker,
    Query,
    QueryMarker,
)


def test_marker_repr():
    marker = PathMarker()
    assert repr(marker) == "<Marker 'path'>"

    marker = QueryMarker()
    assert repr(marker) == "<Marker 'query'>"


def test_marker_names():
    assert PathMarker.name == "path"
    assert QueryMarker.name == "query"
    assert BodyMarker.name == "body"
    assert HeaderMarker.name == "header"
    assert FileMarker.name == "file"


def test_annotated_markers():
    # Verify that helper types are correctly defined as Annotated

    # Path
    type_args = get_args(Path[str])
    assert type_args[0] == str
    assert isinstance(type_args[1], PathMarker)

    # Query
    type_args = get_args(Query[int])
    assert type_args[0] == int
    assert isinstance(type_args[1], QueryMarker)

    # Body
    type_args = get_args(Body[dict])
    assert type_args[0] == dict
    assert isinstance(type_args[1], BodyMarker)

    # Header
    type_args = get_args(Header[str])
    assert type_args[0] == str
    assert isinstance(type_args[1], HeaderMarker)

    # File
    type_args = get_args(File[bytes])
    assert type_args[0] == bytes
    assert isinstance(type_args[1], FileMarker)


def test_marker_instance_caching():
    # Annotated helpers reuse instances
    _, marker1 = get_args(Path[int])
    _, marker2 = get_args(Path[str])

    # Note: They are distinct instances in the current implementation
    # because Path[T] creates a new Annotated type, but the second argument
    # to Annotated is passed as is.
    # In markers.py: Path = Annotated[..., PathMarker()]
    # So the instance IS shared.
    assert marker1 is marker2

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any

from adaptix import Omittable, Omitted, P, dumper
from unihttp.markers import (
    Body,
    BodyMarker,
    Form,
    FormMarker,
    Header,
    HeaderMarker,
    Path,
    PathMarker,
    Query,
    QueryMarker,
)
from unihttp.method import BaseMethod
from unihttp.serializers.adaptix import DEFAULT_RETORT
from unihttp.serializers.adaptix.marker_tools import for_marker


def test_for_marker() -> None:
    class SubHeaderMarker(HeaderMarker):
        pass

    @dataclass(kw_only=True)
    class MyData(BaseMethod[Any]):
        header_dt: Header[datetime]
        header_root_str: Header[str]
        header_sub_str: Annotated[str, SubHeaderMarker()]
        path_str: Path[str | None]
        path_none: Path[str | None]
        query_int: Query[list[int]]
        query_str: Query[list[str]]
        body_int: Body[int]
        body_none: Body[None]
        body_default_none: Body[Any] = None
        body_omitted: Body[Omittable[str]] = Omitted()
        body_filled: Body[Omittable[str]] = Omitted()
        form_anyway: Form[str]
        random_field: str

    retort = DEFAULT_RETORT.extend(
        recipe=[
            dumper(
                for_marker(HeaderMarker, P[datetime]),
                lambda d: d.timestamp(),
            ),
            dumper(
                for_marker(PathMarker, P[None]),
                lambda _: "null",
            ),
            dumper(
                for_marker(QueryMarker, P[list[int]] | P[list[str]]),
                lambda s: ",".join(str(el) for el in s),
            ),
            dumper(
                for_marker(BodyMarker, P[int]),
                lambda t: datetime.fromtimestamp(t),
            ),
            dumper(
                for_marker(HeaderMarker, P[str], subclass=True),
                lambda x: int(x),
            ),
            dumper(
                for_marker(FormMarker),
                lambda x: int(x),
            ),
        ]
    )

    data = MyData(
        header_dt=datetime.fromtimestamp(1234567890),
        header_root_str="123",
        header_sub_str="1234",
        path_str="pathlike",
        path_none=None,
        query_int=[1, 2, 3],
        query_str=["4", "5", "6"],
        body_int=1234567890,
        body_none=None,
        # `body_default_none` acting like `Omitted` when `= None` idk why
        # `body_omitted` is just `Omitted`
        body_filled="filled",
        form_anyway="12345",
        random_field="random",
    )
    excepted = {
        "header": {
            "header_dt": 1234567890.0,
            "header_root_str": 123,
            "header_sub_str": 1234,
        },
        "path": {
            "path_str": "pathlike",
            "path_none": "null",
        },
        "query": {
            "query_int": "1,2,3",
            "query_str": "4,5,6",
        },
        "body": {
            "body_int": datetime.fromtimestamp(1234567890),
            "body_none": None,
            # `body_default_none` acting like `Omitted` when `= None` idk why
            # `body_omitted` is just `Omitted`
            "body_filled": "filled",
        },
        "form": {
            "form_anyway": 12345,
        },
        "random_field": "random",
    }
    assert retort.dump(data) == excepted

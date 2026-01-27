from typing import Annotated, ClassVar, TypeVar


class Marker:
    __slots__ = ()

    name: ClassVar[str]

    def __repr__(self) -> str:
        return f"<Marker {self.name!r}>"


class PathMarker(Marker):
    name = "path"


class QueryMarker(Marker):
    name = "query"


class BodyMarker(Marker):
    name = "body"


class HeaderMarker(Marker):
    name = "header"


class FileMarker(Marker):
    name = "file"


class FormMarker(Marker):
    name = "form"


_MarkerValueT = TypeVar("_MarkerValueT")

Path = Annotated[_MarkerValueT, PathMarker()]
Query = Annotated[_MarkerValueT, QueryMarker()]
Body = Annotated[_MarkerValueT, BodyMarker()]
Header = Annotated[_MarkerValueT, HeaderMarker()]
File = Annotated[_MarkerValueT, FileMarker()]
Form = Annotated[_MarkerValueT, FormMarker()]

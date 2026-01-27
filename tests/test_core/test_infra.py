import tempfile
from pathlib import Path

from unihttp.exceptions import ClientError, HTTPStatusError, ServerError
from unihttp.http.files import UploadFile
from unihttp.http.response import HTTPResponse


def test_upload_file_tuple_regular():
    uf = UploadFile(b"content", "f.txt")
    assert uf.to_tuple() == ("f.txt", b"content", "application/octet-stream")


def test_upload_file_tuple_path():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"content")
        f.close()
        path = Path(f.name)
        try:
            uf = UploadFile(path)
            # When using Path, it reads bytes
            filename, content, ctype = uf.to_tuple()
            assert filename == path.name
            assert content == b"content"
            assert ctype == "application/octet-stream"
        finally:
            path.unlink()


def test_upload_file_path_custom_name():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"content")
        f.close()
        path = Path(f.name)
        try:
            uf = UploadFile(path, filename="custom.txt")
            assert uf.to_tuple() == ("custom.txt", b"content", "application/octet-stream")
        finally:
            path.unlink()


def test_http_status_error():
    response = HTTPResponse(404, {}, {}, {}, None)
    err = HTTPStatusError("Not Found", response)

    assert err.response is response
    assert err.status_code == 404
    assert str(err) == "Not Found"


def test_exception_inheritance():
    assert issubclass(ClientError, HTTPStatusError)
    assert issubclass(ServerError, HTTPStatusError)


def test_response_properties():
    r = HTTPResponse(200, {}, {}, {}, None)
    assert r.ok
    assert not r.is_client_error
    assert not r.is_server_error

    r = HTTPResponse(404, {}, {}, {}, None)
    assert not r.ok
    assert r.is_client_error
    assert not r.is_server_error

    r = HTTPResponse(500, {}, {}, {}, None)
    assert not r.ok
    assert not r.is_client_error
    assert r.is_server_error

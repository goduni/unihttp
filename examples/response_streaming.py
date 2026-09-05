"""Consume a download without buffering it and reject unsuccessful responses."""

from dataclasses import dataclass
from hashlib import sha256

from unihttp.bind_method import bind_method
from unihttp.clients.httpx import HTTPXAsyncClient, HTTPXSyncClient
from unihttp.exceptions import HTTPStatusError
from unihttp.http.response import HTTPResponse
from unihttp.markers import Path
from unihttp.method import StreamMethod


# --8<-- [start:method]
@dataclass
class DownloadFile(StreamMethod):
    __url__ = "/files/{file_id}"
    __method__ = "GET"

    file_id: Path[int]

    def on_error(self, response: HTTPResponse) -> None:
        response.raise_for_status()
        raise HTTPStatusError(f"Unexpected HTTP {response.status_code}", response)

    # --8<-- [end:method]


class FileClient(HTTPXSyncClient):
    download_file = bind_method(DownloadFile)


class AsyncFileClient(HTTPXAsyncClient):
    download_file = bind_method(DownloadFile)


# --8<-- [start:sync]
def download_checksum(client: FileClient, file_id: int) -> str:
    response = client.download_file(file_id=file_id)
    digest = sha256()
    with response.data as stream:
        for chunk in stream:
            digest.update(chunk)
    return digest.hexdigest()
    # --8<-- [end:sync]


# --8<-- [start:async]
async def download_checksum_async(client: AsyncFileClient, file_id: int) -> str:
    response = await client.download_file(file_id=file_id)
    digest = sha256()
    async with response.data as stream:
        async for chunk in stream:
            digest.update(chunk)
    return digest.hexdigest()
    # --8<-- [end:async]

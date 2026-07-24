from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator


class ChunkStream(ABC):
    """Lazily-fetched, closeable stream of response body chunks (sync).

    Subclasses (one per backend) implement only `_fetch_chunk`/
    `_close_response`; this class owns the shared iteration, idempotent
    close and context-manager protocol. Closing does not depend on whether
    iteration ever started — unlike a bare generator's `finally`, `close()`
    always releases the underlying connection.
    """

    def __init__(self) -> None:
        self._closed = False

    @abstractmethod
    def _fetch_chunk(self) -> bytes:
        """Return the next chunk. Raise StopIteration when exhausted."""

    @abstractmethod
    def _close_response(self) -> None:
        """Release the underlying connection. Called at most once."""

    def __iter__(self) -> Iterator[bytes]:
        return self

    def __next__(self) -> bytes:
        if self._closed:
            raise StopIteration
        try:
            return self._fetch_chunk()
        except StopIteration:
            self.close()
            raise

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._close_response()

    def __enter__(self) -> "ChunkStream":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class AsyncChunkStream(ABC):
    """Async counterpart of `ChunkStream`."""

    def __init__(self) -> None:
        self._closed = False

    @abstractmethod
    async def _fetch_chunk(self) -> bytes:
        """Return the next chunk. Raise StopAsyncIteration when exhausted."""

    @abstractmethod
    async def _close_response(self) -> None:
        """Release the underlying connection. Called at most once."""

    def __aiter__(self) -> AsyncIterator[bytes]:
        return self

    async def __anext__(self) -> bytes:
        if self._closed:
            raise StopAsyncIteration
        try:
            return await self._fetch_chunk()
        except StopAsyncIteration:
            await self.aclose()
            raise

    async def aclose(self) -> None:
        if not self._closed:
            self._closed = True
            await self._close_response()

    async def __aenter__(self) -> "AsyncChunkStream":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()


class IteratorChunkStream(ChunkStream):
    """`ChunkStream` backed by a plain sync byte iterator plus a close callback.

    Fits backends where iteration and cleanup are just `next(iterator)` and
    a zero-arg call — `response.close`, or an `ExitStack`'s `.close` when
    the response lives behind a manually-driven context manager. Backends
    with a mismatched close signature (e.g. sync `close()` on an async
    response) use a dedicated `ChunkStream` subclass instead.
    """

    def __init__(self, iterator: Iterator[bytes], close: Callable[[], None]) -> None:
        super().__init__()
        self._iter = iterator
        self._close = close

    def _fetch_chunk(self) -> bytes:
        return next(self._iter)

    def _close_response(self) -> None:
        self._close()


class AsyncIteratorChunkStream(AsyncChunkStream):
    """Async counterpart of `IteratorChunkStream`."""

    def __init__(
        self, iterator: AsyncIterator[bytes], close: Callable[[], Awaitable[None]]
    ) -> None:
        super().__init__()
        self._iter = iterator
        self._close = close

    async def _fetch_chunk(self) -> bytes:
        return await anext(self._iter)

    async def _close_response(self) -> None:
        await self._close()

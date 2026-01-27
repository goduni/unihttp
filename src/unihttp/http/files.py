"""File types for HTTP uploads."""

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


@dataclass
class UploadFile:
    """Convenient wrapper for file uploads.

    Example:
        >>> UploadFile(b"content", filename="test.txt")
        >>> UploadFile(Path("./file.pdf"))
        >>> UploadFile(open("image.png", "rb"), content_type="image/png")
    """

    file: BinaryIO | bytes | Path
    filename: str | None = None
    content_type: str = "application/octet-stream"

    def to_tuple(self) -> tuple[str | None, bytes | BinaryIO, str]:
        """Convert to (filename, content, content_type) tuple."""
        if isinstance(self.file, Path):
            return (
                self.filename or self.file.name,
                self.file.read_bytes(),
                self.content_type,
            )

        return self.filename, self.file, self.content_type


# Type alias for file fields in method definitions
FileType = (
    bytes
    | BinaryIO
    | Path
    | UploadFile
    | tuple[str, bytes | BinaryIO]
    | tuple[str, bytes | BinaryIO, str]
)

__all__ = ("FileType", "UploadFile")

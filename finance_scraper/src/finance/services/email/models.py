"""Typed email attachments used by the SMTP delivery service."""

import mimetypes
from dataclasses import dataclass
from pathlib import Path


# ================================================== #
# ATTACHMENT MODEL                                   #
# ================================================== #

@dataclass(frozen=True, slots=True)
class EmailAttachment:
    """A file attachment ready to be added to an email message."""

    filename: str
    content: bytes
    maintype: str = 'application'
    subtype: str = 'octet-stream'

    def __post_init__(self) -> None:
        if not isinstance(self.filename, str):
            raise TypeError('Attachment filename must be a string')
        if not self.filename.strip():
            raise ValueError('Attachment filename must not be blank')
        if (
            Path(self.filename).name != self.filename
            or '\r' in self.filename
            or '\n' in self.filename
        ):
            raise ValueError('Attachment filename must be a safe file name')
        if not isinstance(self.content, bytes):
            raise TypeError('Attachment content must be bytes')
        if not isinstance(self.maintype, str) or not isinstance(self.subtype, str):
            raise TypeError('Attachment MIME type must be a string')
        if not self.maintype.strip() or not self.subtype.strip():
            raise ValueError('Attachment MIME type must not be blank')

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        *,
        filename: str | None = None,
    ) -> 'EmailAttachment':
        """Read a file and infer its MIME type."""

        attachment_path: Path = Path(path)
        if not attachment_path.is_file():
            raise FileNotFoundError(attachment_path)

        attachment_name: str = filename or attachment_path.name
        if (
            not attachment_name
            or Path(attachment_name).name != attachment_name
            or '\r' in attachment_name
            or '\n' in attachment_name
        ):
            raise ValueError('Attachment filename must be a safe file name')

        content_type: str | None
        encoding: str | None
        content_type, encoding = mimetypes.guess_type(attachment_name)
        del encoding
        if content_type is None or '/' not in content_type:
            maintype: str = 'application'
            subtype: str = 'octet-stream'
        else:
            maintype, subtype = content_type.split('/', 1)

        return cls(
            filename=attachment_name,
            content=attachment_path.read_bytes(),
            maintype=maintype,
            subtype=subtype,
        )


__all__: list[str] = [
    'EmailAttachment',
]

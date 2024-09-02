# Copyright 2022 Amethyst Reese, Tim Hatch
# Licensed under the MIT license

import logging
from pathlib import Path
from typing import List, Literal, Optional

from lsprotocol.types import (
    DocumentFormattingParams,
    MessageType,
    Position,
    Range,
    TEXT_DOCUMENT_FORMATTING,
    TextEdit,
)

from pygls.server import LanguageServer
from pygls.workspace import TextDocument

from .__version__ import __version__
from .config import load_config
from .core import ufmt_bytes
from .types import (
    BlackConfigFactory,
    Encoding,
    FileContent,
    Processor,
    Result,
    SkipFormatting,
    UfmtConfigFactory,
    UsortConfig,
    UsortConfigFactory,
)
from .util import make_black_config, normalize_content, normalize_result

ServerType = Literal["stdin", "tcp", "ws"]

LOG = logging.getLogger(__name__)


def _wrap_ufmt_bytes(  # pragma: nocover
    path: Path,
    content: FileContent,
    *,
    encoding: Encoding,
    ufmt_config_factory: Optional[UfmtConfigFactory] = None,
    black_config_factory: Optional[BlackConfigFactory] = None,
    usort_config_factory: Optional[UsortConfigFactory] = None,
    pre_processor: Optional[Processor] = None,
    post_processor: Optional[Processor] = None,
    root: Optional[Path] = None,
) -> Result:
    try:
        ufmt_config = (ufmt_config_factory or load_config)(path, root)
        black_config = (black_config_factory or make_black_config)(path)
        usort_config = (usort_config_factory or UsortConfig.find)(path)

        result = Result(path)

        dst_contents = ufmt_bytes(
            path,
            content,
            encoding=encoding,
            ufmt_config=ufmt_config,
            black_config=black_config,
            usort_config=usort_config,
            pre_processor=pre_processor,
            post_processor=post_processor,
        )
        result.after = dst_contents

    except SkipFormatting as e:
        result.after = content
        result.skipped = str(e) or True
        return result

    except Exception as e:
        result.error = e
        return result

    return result


def ufmt_lsp(  # pragma: nocover
    *,
    ufmt_config_factory: Optional[UfmtConfigFactory] = None,
    black_config_factory: Optional[BlackConfigFactory] = None,
    usort_config_factory: Optional[UsortConfigFactory] = None,
    pre_processor: Optional[Processor] = None,
    post_processor: Optional[Processor] = None,
    root: Optional[Path] = None,
) -> LanguageServer:
    """
    Prepare an LSP server instance.

    Keyword arguments have the same semantics as :func:`ufmt_paths`.

    Returns a LanguageServer object. User must call the ``start_io()`` or
    ``start_tcp()`` method with appropriate arguments to actually start the LSP server.
    """
    server = LanguageServer("ufmt-lsp", __version__)

    @server.feature(TEXT_DOCUMENT_FORMATTING)
    def lsp_format_document(
        ls: LanguageServer, params: DocumentFormattingParams
    ) -> Optional[List[TextEdit]]:
        document: TextDocument = ls.workspace.get_text_document(
            params.text_document.uri
        )
        path = Path(document.path).resolve()

        # XXX: we're assuming everything is UTF-8 because LSP doesn't track encodings...
        encoding: Encoding = "utf-8"
        content, newline = normalize_content(document.source.encode(encoding))

        result = _wrap_ufmt_bytes(
            path,
            content,
            encoding=encoding,
            ufmt_config_factory=ufmt_config_factory,
            black_config_factory=black_config_factory,
            usort_config_factory=usort_config_factory,
            pre_processor=pre_processor,
            post_processor=post_processor,
            root=root,
        )

        if result.error:
            ls.show_message(
                f"Formatting failed: {str(result.error)}", MessageType.Error
            )
            return []

        return [
            TextEdit(
                Range(
                    Position(0, 0),
                    Position(len(document.lines), 0),
                ),
                normalize_result(result.after, newline).decode(encoding),
            ),
        ]

    return server

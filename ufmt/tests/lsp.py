# Copyright Amethyst Reese
# Licensed under the MIT license

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Timer
from unittest import TestCase

from ufmt.lsp import ufmt_lsp


class LspTest(TestCase):
    def setUp(self) -> None:
        self.td = TemporaryDirectory()
        self.tdp = Path(self.td.name).resolve()
        self.addCleanup(self.td.cleanup)

    def test_startup_shutdown(self) -> None:
        stdin = BytesIO()
        stdout = BytesIO()

        server = ufmt_lsp(root=self.tdp)

        def times_up() -> None:
            server.shutdown()  # type: ignore[no-untyped-call]
            raise RuntimeError("had to forcefully shutdown lsp")

        timer = Timer(5, times_up)
        timer.start()
        server.start_io(stdin, stdout)
        timer.cancel()

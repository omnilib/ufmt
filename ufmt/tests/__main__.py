# Copyright 2021 John Reese
# Licensed under the MIT license

import unittest

from ufmt.cli import init_logging

if __name__ == "__main__":  # pragma: no cover
    init_logging()
    unittest.main(module="ufmt.tests", verbosity=2)

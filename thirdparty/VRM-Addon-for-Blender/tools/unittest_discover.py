#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR GPL-3.0-or-later

import argparse
import sys
from pathlib import Path
from typing import TextIO
from unittest import TestLoader
from unittest.runner import TextTestRunner

import bpy

# This is not necessary if executed from uv
sys.path.append(str(Path(__file__).parent.parent / "src"))


def discover_and_run_test_suite(argv: list[str], stream: TextIO) -> int:
    if bpy.app.binary_path:
        argv = argv[argv.index("--") + 1 :] if "--" in argv else []

    parser = argparse.ArgumentParser(prog=Path(__file__).name)
    parser.add_argument("-f", "--failfast", action="store_true")
    args = parser.parse_args(argv)

    test_loader = TestLoader()
    test_suite = test_loader.discover(start_dir=str(Path(__file__).parent.parent))
    test_runner = TextTestRunner(stream=stream, failfast=args.failfast)
    test_result = test_runner.run(test_suite)
    return 0 if test_result.wasSuccessful() else 1


def main(argv: list[str]) -> int:
    if sys.platform == "win32":
        with open(  # noqa: PTH123
            sys.stderr.fileno(), mode="w", encoding="ansi", buffering=1
        ) as windows_stderr:
            return discover_and_run_test_suite(argv, windows_stderr)
    return discover_and_run_test_suite(argv, sys.stderr)


if __name__ == "__main__":
    sys.exit(main(sys.argv))

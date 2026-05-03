"""Verify `_force_utf8_streams` reconfigures stdin (not just stdout/stderr).

On Windows the default stdin decoder is cp1252 with `surrogateescape`, so a
heredoc that pipes UTF-8 bytes (e.g. Vietnamese diacritics) into
`omnimem note new --body -` produced surrogates that crashed
`Path.write_text` later with "surrogates not allowed".

PR #6 (v1.2.5) reconfigured stdout/stderr to UTF-8 but missed stdin. This
test pins the wider contract: all three standard streams get UTF-8
encoding when `_force_utf8_streams` runs.
"""

import sys
import unittest
from unittest.mock import MagicMock

import omnimem


class TestForceUtf8Streams(unittest.TestCase):
    def test_reconfigure_called_on_all_three_streams(self):
        original = (sys.stdin, sys.stdout, sys.stderr)
        try:
            stdin = MagicMock()
            stdout = MagicMock()
            stderr = MagicMock()
            sys.stdin, sys.stdout, sys.stderr = stdin, stdout, stderr

            omnimem._force_utf8_streams()

            stdin.reconfigure.assert_called_once_with(encoding="utf-8")
            stdout.reconfigure.assert_called_once_with(encoding="utf-8")
            stderr.reconfigure.assert_called_once_with(encoding="utf-8")
        finally:
            sys.stdin, sys.stdout, sys.stderr = original

    def test_streams_without_reconfigure_are_skipped_quietly(self):
        original = (sys.stdin, sys.stdout, sys.stderr)
        try:
            class _BareStream:
                """Looks like a closed/redirected stream that lacks reconfigure."""

            sys.stdin = _BareStream()
            sys.stdout = _BareStream()
            sys.stderr = _BareStream()
            # Should not raise.
            omnimem._force_utf8_streams()
        finally:
            sys.stdin, sys.stdout, sys.stderr = original

    def test_reconfigure_failure_is_swallowed(self):
        original = (sys.stdin, sys.stdout, sys.stderr)
        try:
            stream = MagicMock()
            stream.reconfigure.side_effect = ValueError("can't change encoding mid-stream")
            sys.stdin = stream
            sys.stdout = MagicMock()
            sys.stderr = MagicMock()
            # Should not raise — bad reconfigure is never fatal.
            omnimem._force_utf8_streams()
        finally:
            sys.stdin, sys.stdout, sys.stderr = original


if __name__ == "__main__":
    unittest.main()

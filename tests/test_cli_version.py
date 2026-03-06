import subprocess
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
EXPECTED_BANNER = f"OmniMem v{(ROOT_DIR / 'VERSION').read_text(encoding='utf-8').strip()}"
SCRIPTS = (
    "omnimem.py",
    "omni_add.py",
    "omni_search.py",
    "omni_import.py",
    "omni_del.py",
    "omni_bootstrap.py",
    "omni_ops.py",
    "omni_doctor.py",
    "omni_update.py",
)


class TestCliVersion(unittest.TestCase):
    def test_version_flag_works_for_core_scripts(self):
        for script_name in SCRIPTS:
            with self.subTest(script=script_name):
                result = subprocess.run(
                    [sys.executable, str(ROOT_DIR / script_name), "--version"],
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr)
                self.assertIn(EXPECTED_BANNER, result.stdout.strip())

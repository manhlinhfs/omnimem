import sys
import types
import unittest
from unittest.mock import patch

import omni_doctor


class FakeCollection:
    def count(self):
        return 1


class FakePersistentClient:
    def __init__(self, path):
        self.path = path

    def get_collection(self, name):
        return FakeCollection()


class TestOmniDoctor(unittest.TestCase):
    def test_doctor_report_includes_effective_config(self):
        fake_chromadb = types.SimpleNamespace(PersistentClient=FakePersistentClient)
        fake_kreuzberg = types.SimpleNamespace(__name__="kreuzberg")
        with patch.dict(sys.modules, {"chromadb": fake_chromadb, "kreuzberg": fake_kreuzberg}):
            report = omni_doctor.run_doctor(deep=False)

        self.assertIn("effective_config", report)
        self.assertIn("settings", report["effective_config"])
        check_names = {item["name"] for item in report["checks"]}
        self.assertIn("config_file", check_names)
        self.assertIn("effective_config", check_names)


if __name__ == "__main__":
    unittest.main()

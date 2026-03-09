import unittest
from pathlib import Path
from unittest.mock import patch

import omni_service


class TestSearchServiceRuntimeIsolation(unittest.TestCase):
    def test_ensure_search_service_rejects_runtime_mismatch(self):
        expected_runtime = {
            "root_dir": "/root/omnimem",
            "runtime_home": "/tmp/current-home",
            "db_dir": "/tmp/current-home/.omnimem_db",
            "models_dir": "/tmp/models",
        }
        status = {
            "status": "ok",
            "reachable": True,
            "host": "127.0.0.1",
            "port": 41733,
            "detail": {
                "status": "ok",
                "runtime": {
                    "root_dir": "/root/omnimem",
                    "runtime_home": "/tmp/other-home",
                    "db_dir": "/tmp/other-home/.omnimem_db",
                    "models_dir": "/tmp/models",
                },
            },
        }

        with patch.object(omni_service, "get_search_service_settings", return_value={
            "enabled": True,
            "host": "127.0.0.1",
            "port": 41733,
            "startup_timeout_seconds": 20,
            "request_timeout_seconds": 10,
        }):
            with patch.object(omni_service, "_get_runtime_signature", return_value=expected_runtime):
                with patch.object(omni_service, "inspect_search_service", return_value=status):
                    with self.assertRaises(omni_service.SearchServiceUnavailable):
                        omni_service.ensure_search_service(root_dir=Path("/root/omnimem"))

    def test_ensure_search_service_accepts_matching_runtime(self):
        expected_runtime = {
            "root_dir": "/root/omnimem",
            "runtime_home": "/tmp/current-home",
            "db_dir": "/tmp/current-home/.omnimem_db",
            "models_dir": "/tmp/models",
        }
        status = {
            "status": "ok",
            "reachable": True,
            "host": "127.0.0.1",
            "port": 41733,
            "detail": {
                "status": "ok",
                "runtime": dict(expected_runtime),
            },
        }

        with patch.object(omni_service, "get_search_service_settings", return_value={
            "enabled": True,
            "host": "127.0.0.1",
            "port": 41733,
            "startup_timeout_seconds": 20,
            "request_timeout_seconds": 10,
        }):
            with patch.object(omni_service, "_get_runtime_signature", return_value=expected_runtime):
                with patch.object(omni_service, "inspect_search_service", return_value=status):
                    report = omni_service.ensure_search_service(root_dir=Path("/root/omnimem"))

        self.assertEqual(report["status"], "ready")
        self.assertFalse(report["started"])


if __name__ == "__main__":
    unittest.main()

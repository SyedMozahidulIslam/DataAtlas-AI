import os
from pathlib import Path
import unittest
from unittest.mock import patch

from dataatlas.config import Settings


class SettingsTests(unittest.TestCase):
    def test_reads_environment(self):
        with patch.dict(os.environ, {"DATAATLAS_HOME": "./custom-data", "DATAATLAS_HOST": "127.0.0.1", "DATAATLAS_PORT": "8123"}):
            settings = Settings.from_env()
        self.assertEqual(settings.data_home, Path("./custom-data"))
        self.assertEqual(settings.port, 8123)

    def test_rejects_invalid_port(self):
        with patch.dict(os.environ, {"DATAATLAS_PORT": "70000"}):
            with self.assertRaisesRegex(ValueError, "between 1 and 65535"):
                Settings.from_env()


if __name__ == "__main__":
    unittest.main()

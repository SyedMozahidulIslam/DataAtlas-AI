import tempfile
import unittest
from pathlib import Path

from dataatlas.storage import LocalFileStorage


class BronzeStorageTests(unittest.TestCase):
    def test_atomic_bronze_file_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            storage = LocalFileStorage(Path(temp))
            workspace_id = "a" * 32
            dataset_id = "b" * 32
            source = b"id,value\n1,25\n"
            stored = storage.write_bronze_csv(workspace_id, dataset_id, source)
            self.assertEqual(stored.byte_count, len(source))
            self.assertEqual(len(stored.sha256), 64)
            self.assertEqual(storage.read(stored.uri), source)
            self.assertIn(workspace_id, stored.uri)

    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            storage = LocalFileStorage(Path(temp))
            with self.assertRaises(ValueError):
                storage.write_bronze_csv("../outside", "b" * 32, b"x")
            with self.assertRaises(FileNotFoundError):
                storage.read("../../outside.csv")


if __name__ == "__main__":
    unittest.main()

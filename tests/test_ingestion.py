import unittest

from dataatlas.ingestion import parse_csv


class CsvIngestionTests(unittest.TestCase):
    def test_infers_schema_and_preserves_values(self):
        columns, rows, schema = parse_csv("sales.csv", b"id,amount,label\n1,2.50,hello\n2,,world\n")
        self.assertEqual(columns, ["id", "amount", "label"])
        self.assertEqual(rows[0], {"id": "1", "amount": "2.50", "label": "hello"})
        self.assertEqual(rows[1]["amount"], None)
        self.assertEqual([x["type"] for x in schema], ["integer", "number", "string"])
        self.assertTrue(schema[1]["nullable"])

    def test_rejects_non_csv(self):
        with self.assertRaisesRegex(ValueError, "Only CSV"):
            parse_csv("data.json", b"{}")

    def test_rejects_duplicate_headers(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            parse_csv("data.csv", b"id,id\n1,2\n")

    def test_rejects_extra_cells(self):
        with self.assertRaisesRegex(ValueError, "more cells"):
            parse_csv("data.csv", b"id,name\n1,a,extra\n")

    def test_rejects_empty_dataset(self):
        with self.assertRaisesRegex(ValueError, "no data rows"):
            parse_csv("data.csv", b"id,name\n")

    def test_infers_boolean_date_and_timestamp_types(self):
        _, _, schema = parse_csv("dates.csv", b"active,day,seen_at\ntrue,2026-01-01,2026-01-01T12:00:00Z\nfalse,2026-01-02,2026-01-02T13:00:00Z\n")
        self.assertEqual([column["type"] for column in schema], ["boolean", "date", "timestamp"])


if __name__ == "__main__":
    unittest.main()

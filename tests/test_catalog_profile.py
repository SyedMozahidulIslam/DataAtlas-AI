import unittest

from dataatlas.catalog import compare_schemas, validate_metadata
from dataatlas.profiling import profile_dataset


class CatalogSchemaTests(unittest.TestCase):
    def test_schema_change_severity_and_ambiguous_rename(self):
        old = [{"name": "id", "type": "integer", "nullable": False},
               {"name": "value", "type": "integer", "nullable": True}]
        new = [{"name": "record_id", "type": "integer", "nullable": False},
               {"name": "value", "type": "string", "nullable": False},
               {"name": "note", "type": "string", "nullable": True}]
        changes = compare_schemas(old, new)
        change_types = {change["change_type"] for change in changes}
        self.assertEqual(change_types, {"column_added", "column_removed", "data_type_changed", "nullability_changed"})
        self.assertEqual(next(c for c in changes if c["change_type"] == "column_removed")["severity"], "breaking")
        self.assertEqual(next(c for c in changes if c["change_type"] == "column_added")["severity"], "info")
        self.assertEqual(next(c for c in changes if c["change_type"] == "data_type_changed")["severity"], "breaking")

    def test_metadata_normalizes_and_deduplicates_tags(self):
        description, tags = validate_metadata("  Revenue facts  ", ["sales", " Sales ", "monthly"])
        self.assertEqual(description, "Revenue facts")
        self.assertEqual(tags, ["sales", "monthly"])


class ProfilingTests(unittest.TestCase):
    def test_profiles_numeric_outliers_text_boolean_and_dates(self):
        records = [
            {"amount": "1", "label": "aa", "active": "true", "day": "2026-01-01"},
            {"amount": "2", "label": "b", "active": "false", "day": "2026-01-02"},
            {"amount": "3", "label": "aa", "active": "true", "day": "2026-01-03"},
            {"amount": "4", "label": "b", "active": "true", "day": "2026-01-04"},
            {"amount": "1000", "label": "ccc", "active": "false", "day": "2026-01-05"},
        ]
        schema = [{"name": "amount", "type": "integer", "nullable": False},
                  {"name": "label", "type": "string", "nullable": False},
                  {"name": "active", "type": "boolean", "nullable": False},
                  {"name": "day", "type": "date", "nullable": False}]
        profile = profile_dataset({"row_count": len(records), "records_json": records, "schema_json": schema})
        columns = {column["name"]: column for column in profile["columns"]}
        self.assertEqual(columns["amount"]["outlier_count"], 1)
        self.assertEqual(columns["label"]["max_length"], 3)
        self.assertEqual(columns["active"]["true_count"], 3)
        self.assertEqual(columns["day"]["latest"], "2026-01-05")


if __name__ == "__main__":
    unittest.main()

import json
import unittest

from dataatlas.quality import evaluate_rule, validate_rule


class QualityRuleTests(unittest.TestCase):
    def setUp(self):
        self.schema = [
            {"name": "id", "type": "integer", "nullable": False},
            {"name": "amount", "type": "number", "nullable": True},
            {"name": "status", "type": "string", "nullable": True},
        ]
        self.records = [
            {"id": "1", "amount": "10", "status": "paid"},
            {"id": "1", "amount": "-2", "status": "unknown"},
            {"id": "3", "amount": None, "status": None},
        ]

    def rule(self, rule_type, column="id", config=None):
        return {"id": "rule-1", "rule_type": rule_type, "target_column": column,
                "config": config or {}, "version": 1, "severity": "warning", "name": "test"}

    def test_not_null_unique_and_numeric_range_have_real_counts_and_bounded_samples(self):
        not_null = self.rule("not_null")
        unique = self.rule("unique")
        numeric = self.rule("numeric_range", "amount", {"min": 0, "max": 20})
        self.assertEqual(evaluate_rule(not_null, self.records)["violations"], 0)
        self.assertEqual(evaluate_rule(unique, self.records)["violations"], 1)
        result = evaluate_rule(numeric, self.records)
        self.assertEqual((result["rows_evaluated"], result["violations"]), (3, 1))
        self.assertEqual(result["samples"], [{"row_number": 2, "value": "-2"}])

    def test_row_count_allowed_values_and_reference_checks(self):
        row_count = self.rule("row_count", None, {"min": 4})
        allowed = self.rule("allowed_values", "status", {"values": ["paid", "pending"]})
        reference = self.rule("referential_integrity", "id", {
            "reference_dataset_id": "lookup", "reference_column": "id"})
        self.assertEqual(evaluate_rule(row_count, self.records)["violations"], 1)
        self.assertEqual(evaluate_rule(allowed, self.records)["violations"], 1)
        refs = [{"id": "1"}, {"id": "3"}]
        self.assertEqual(evaluate_rule(reference, self.records, refs)["violations"], 0)

    def test_validation_rejects_unknown_columns_unsafe_pattern_and_bad_bounds(self):
        with self.assertRaisesRegex(ValueError, "target dataset schema"):
            validate_rule("bad", "", "d", "missing", "not_null", {}, "warning", self.schema)
        with self.assertRaisesRegex(ValueError, "Nested repeating"):
            validate_rule("bad", "", "d", "status", "regex", {"pattern": "(a+)+$"}, "warning", self.schema)
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            validate_rule("bad", "", "d", "amount", "numeric_range", {"min": 10, "max": 1}, "warning", self.schema)
        with self.assertRaisesRegex(ValueError, "at most 100"):
            validate_rule("bad", "", "d", "status", "allowed_values", {"values": list(range(101))}, "warning", self.schema)


if __name__ == "__main__":
    unittest.main()

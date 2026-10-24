import unittest

from dataatlas.transformations import run_steps, validate_definition


class TransformationTests(unittest.TestCase):
    def setUp(self):
        self.schema = [
            {"name": "amount", "type": "number", "nullable": False},
            {"name": "status", "type": "string", "nullable": False},
        ]
        self.records = [{"amount": "10", "status": "paid"}, {"amount": "4", "status": "pending"}]

    def test_filter_derive_and_select_pipeline(self):
        name, description, steps = validate_definition(
            "Paid values", "Filtered and tax adjusted", "dataset-id", "gold", [
                {"type": "filter", "column": "status", "operator": "eq", "value": "paid"},
                {"type": "derive", "column": "with_tax", "source_column": "amount",
                 "operation": "multiply", "value": 1.1},
                {"type": "select", "columns": ["status", "with_tax"]},
            ], self.schema)
        columns, schema, rows = run_steps(self.records, self.schema, steps)
        self.assertEqual((name, description), ("Paid values", "Filtered and tax adjusted"))
        self.assertEqual(columns, ["status", "with_tax"])
        self.assertEqual(rows, [{"status": "paid", "with_tax": 11.0}])
        self.assertEqual(schema[-1]["type"], "number")

    def test_rejects_division_by_zero_and_unknown_columns(self):
        with self.assertRaisesRegex(ValueError, "divide by zero"):
            validate_definition("Bad", "", "d", "silver", [
                {"type": "derive", "column": "x", "source_column": "amount", "operation": "divide", "value": 0},
            ], self.schema)
        with self.assertRaisesRegex(ValueError, "unknown column"):
            validate_definition("Bad", "", "d", "silver", [
                {"type": "filter", "column": "missing", "operator": "eq", "value": "x"},
            ], self.schema)


if __name__ == "__main__":
    unittest.main()

import json
import unittest

from dataatlas.sql_workspace import execute_readonly, table_catalog


class SqlWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.dataset = {
            "id": "12345678abcdef",
            "name": "Sales Orders",
            "row_count": 2,
            "schema_json": json.dumps([
                {"name": "order_id", "type": "integer", "nullable": False},
                {"name": "amount", "type": "number", "nullable": False},
            ]),
            "records_json": json.dumps([
                {"order_id": 1, "amount": 12.5}, {"order_id": 2, "amount": 8.0},
            ]),
        }

    def test_catalog_and_read_query(self):
        table = table_catalog([self.dataset])[0]
        self.assertEqual(table["table_name"], "sales_orders_12345678")
        result = execute_readonly([self.dataset], f'SELECT order_id, amount FROM "{table["table_name"]}" ORDER BY order_id')
        self.assertEqual(result["columns"], ["order_id", "amount"])
        self.assertEqual(result["rows"], [{"order_id": 1, "amount": 12.5}, {"order_id": 2, "amount": 8.0}])

    def test_rejects_mutation_and_unknown_tables(self):
        table = table_catalog([self.dataset])[0]["table_name"]
        with self.assertRaisesRegex(ValueError, "read-only SELECT"):
            execute_readonly([self.dataset], f'DELETE FROM "{table}"')
        with self.assertRaises(ValueError):
            execute_readonly([self.dataset], "SELECT * FROM another_workspace_table")

    def test_enforces_result_bound_and_sql_length(self):
        dataset = dict(self.dataset)
        dataset["row_count"] = 501
        dataset["records_json"] = json.dumps([{"order_id": index, "amount": 1} for index in range(501)])
        table = table_catalog([dataset])[0]["table_name"]
        with self.assertRaisesRegex(ValueError, "LIMIT clause"):
            execute_readonly([dataset], f'SELECT * FROM "{table}"')
        with self.assertRaisesRegex(ValueError, "characters or fewer"):
            execute_readonly([self.dataset], "x" * 10_001)


if __name__ == "__main__":
    unittest.main()

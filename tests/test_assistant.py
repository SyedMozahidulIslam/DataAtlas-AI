import unittest

from dataatlas.assistant import (
    answer_locally, local_sql_candidate, parse_json_object, provider_status,
)
from dataatlas.sql_workspace import table_catalog


class AssistantTests(unittest.TestCase):
    def setUp(self):
        self.dataset = {"id": "12345678abcdef", "name": "Sales Orders", "row_count": 4,
                        "schema_json": '[{"name":"order_id","type":"integer","nullable":false}]'}
        self.table = table_catalog([self.dataset])[0]

    def test_provider_defaults_to_local_without_credentials(self):
        status = provider_status(None, None)
        self.assertEqual(status["provider"], "local")
        self.assertFalse(status["configured"])

    def test_local_sql_is_limited_to_explicit_preview_and_count(self):
        self.assertIsNone(local_sql_candidate(
            "show highest revenue categories in Sales Orders", [self.dataset], [self.table]))
        count = local_sql_candidate("How many rows are in Sales Orders?", [self.dataset], [self.table])
        self.assertIn("COUNT(*)", count["sql"])
        preview = local_sql_candidate("preview 3 rows from Sales Orders", [self.dataset], [self.table])
        self.assertIn("LIMIT 3", preview["sql"])
        self.assertIsNone(local_sql_candidate("preview rows", [self.dataset, self.dataset],
                                              [self.table, self.table]))

    def test_parse_json_object_accepts_wrapped_json_and_rejects_invalid(self):
        self.assertEqual(parse_json_object('answer: {"sql":"SELECT 1"}'), {"sql": "SELECT 1"})
        with self.assertRaises(ValueError):
            parse_json_object("no JSON here")

    def test_local_answer_uses_only_context_facts(self):
        context = {
            "datasets": [{"id": "1", "name": "Orders", "row_count": 7, "schema": [{"name": "id"}],
                          "layer": "bronze", "updated_at": "today", "profile": [
                              {"name": "amount", "null_count": 2}]}],
            "failed_quality_rules": [], "failed_ingestion_jobs": [],
            "recent_transformations": [], "lineage_edges": [],
        }
        answer = answer_locally("which columns have missing values?", context)
        self.assertIn("Orders.amount: 2 nulls", answer)
        self.assertNotIn("secret raw record", answer)


if __name__ == "__main__":
    unittest.main()

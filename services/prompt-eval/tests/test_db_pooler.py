"""The vision worker must support the production transaction pooler."""
import unittest
from unittest.mock import patch

from argus_prompt_eval import db


class PoolerEngineTests(unittest.TestCase):
    def test_disables_asyncpg_statement_cache_like_the_api(self):
        db.get_engine.cache_clear()
        try:
            with patch.object(db, "create_async_engine") as create:
                engine = db.get_engine()
                self.assertIs(engine, create.return_value)
                self.assertTrue(create.call_args.kwargs["pool_pre_ping"])
                self.assertEqual(
                    create.call_args.kwargs.get("connect_args"),
                    {"statement_cache_size": 0},
                )
                self.assertIs(db.get_engine(), engine)
                create.assert_called_once()
        finally:
            db.get_engine.cache_clear()

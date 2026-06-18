import unittest

from config import MINERU_CACHE_SCHEMA_VERSION
from services.mineru_cache import build_cache_key


class MinerUCacheTest(unittest.TestCase):
    def test_cache_key_includes_schema_version(self):
        cache_key = build_cache_key("abc123")

        self.assertIn(f"__schema_{MINERU_CACHE_SCHEMA_VERSION}", cache_key)


if __name__ == "__main__":
    unittest.main()

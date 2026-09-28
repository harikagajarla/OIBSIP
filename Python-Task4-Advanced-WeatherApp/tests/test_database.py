"""
Tests for app/database.py.

Uses an in-memory SQLite database (":memory:") so tests never touch
the real weather_app.db file and leave no artifacts behind.
"""

import unittest

from app import database


class TestSearchHistoryRepo(unittest.TestCase):
    def setUp(self):
        self.conn = database.get_connection(db_path=":memory:")
        self.repo = database.SearchHistoryRepo(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_add_and_retrieve(self):
        self.repo.add("Hyderabad", "IN", 29.5, "Clouds")
        entries = self.repo.get_recent()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].city, "Hyderabad")

    def test_most_recent_first(self):
        self.repo.add("Delhi", "IN", 32.0, "Clear")
        self.repo.add("Mumbai", "IN", 28.0, "Rain")
        entries = self.repo.get_recent()
        self.assertEqual(entries[0].city, "Mumbai")

    def test_clear_removes_all(self):
        self.repo.add("Chennai", "IN", 33.0, "Clear")
        self.repo.clear()
        self.assertEqual(len(self.repo.get_recent()), 0)

    def test_limit_respected(self):
        for i in range(5):
            self.repo.add(f"City{i}", "IN", 25.0, "Clear")
        entries = self.repo.get_recent(limit=3)
        self.assertEqual(len(entries), 3)


class TestFavoriteCitiesRepo(unittest.TestCase):
    def setUp(self):
        self.conn = database.get_connection(db_path=":memory:")
        self.repo = database.FavoriteCitiesRepo(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_add_favorite(self):
        added = self.repo.add("Hyderabad", "IN")
        self.assertTrue(added)
        self.assertTrue(self.repo.is_favorite("Hyderabad", "IN"))

    def test_add_duplicate_favorite_returns_false(self):
        self.repo.add("Hyderabad", "IN")
        added_again = self.repo.add("Hyderabad", "IN")
        self.assertFalse(added_again)

    def test_remove_favorite(self):
        self.repo.add("Pune", "IN")
        self.repo.remove("Pune", "IN")
        self.assertFalse(self.repo.is_favorite("Pune", "IN"))

    def test_get_all_sorted(self):
        self.repo.add("Zurich", "CH")
        self.repo.add("Austin", "US")
        favorites = self.repo.get_all()
        self.assertEqual(favorites[0].city, "Austin")  # alphabetical


if __name__ == "__main__":
    unittest.main()

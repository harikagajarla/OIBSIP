"""Tests for the SQLite storage layer (every test uses a temporary database file)."""

import sqlite3
from datetime import datetime

import pytest

from bmi_tracker.db import database as database_module
from bmi_tracker.db.database import Database
from bmi_tracker.exceptions import DatabaseError, DuplicateUserError


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "test.db")


def test_database_file_and_folder_are_created(tmp_path):
    path = tmp_path / "nested" / "folder" / "bmi.db"
    Database(path)
    assert path.exists()


def test_add_user_and_list_sorted_case_insensitively(db):
    db.add_user("bob")
    db.add_user("Alice")
    db.add_user("carol")
    assert [u.name for u in db.get_users()] == ["Alice", "bob", "carol"]


def test_empty_database_has_no_users(db):
    assert db.get_users() == []


def test_duplicate_user_is_rejected_ignoring_case(db):
    db.add_user("Alice")
    with pytest.raises(DuplicateUserError):
        db.add_user("alice")


def test_get_user_by_name_is_case_insensitive(db):
    created = db.add_user("Alice")
    assert db.get_user_by_name("ALICE").id == created.id
    assert db.get_user_by_name("nobody") is None


def test_add_record_and_read_back(db):
    user = db.add_user("Alice")
    saved = db.add_record(user.id, 70.0, 1.75, 22.86, "Normal")
    records = db.get_records(user.id)
    assert len(records) == 1
    assert records[0].id == saved.id
    assert (records[0].weight_kg, records[0].height_m, records[0].bmi) == (70.0, 1.75, 22.86)
    assert records[0].category == "Normal"
    assert isinstance(records[0].recorded_at, datetime)


def test_records_are_returned_oldest_first(db):
    user = db.add_user("Alice")
    db.add_record(user.id, 72, 1.75, 23.51, "Normal", recorded_at=datetime(2026, 3, 1, 9, 0))
    db.add_record(user.id, 70, 1.75, 22.86, "Normal", recorded_at=datetime(2026, 1, 1, 9, 0))
    db.add_record(user.id, 71, 1.75, 23.18, "Normal", recorded_at=datetime(2026, 2, 1, 9, 0))
    assert [r.bmi for r in db.get_records(user.id)] == [22.86, 23.18, 23.51]


def test_records_are_kept_separate_per_user(db):
    alice = db.add_user("Alice")
    bob = db.add_user("Bob")
    db.add_record(alice.id, 70, 1.75, 22.86, "Normal")
    db.add_record(bob.id, 95, 1.70, 32.87, "Obese")
    db.add_record(bob.id, 94, 1.70, 32.53, "Obese")
    assert len(db.get_records(alice.id)) == 1
    assert len(db.get_records(bob.id)) == 2
    assert all(r.category == "Obese" for r in db.get_records(bob.id))


def test_user_with_no_records_returns_empty_list(db):
    user = db.add_user("Alice")
    assert db.get_records(user.id) == []


def test_data_persists_after_reopening_the_database(tmp_path):
    path = tmp_path / "persist.db"
    first = Database(path)
    user = first.add_user("Alice")
    first.add_record(user.id, 70, 1.75, 22.86, "Normal")

    reopened = Database(path)
    assert [u.name for u in reopened.get_users()] == ["Alice"]
    assert len(reopened.get_records(user.id)) == 1


def test_queries_are_parameterized_against_sql_injection(db):
    nasty = "Robert'); DROP TABLE users;--"
    db.add_user(nasty)
    assert [u.name for u in db.get_users()] == [nasty]  # table still exists
    assert db.get_user_by_name(nasty) is not None


def test_record_for_unknown_user_is_rejected(db):
    with pytest.raises(DatabaseError):
        db.add_record(9999, 70, 1.75, 22.86, "Normal")


def test_failed_write_does_not_leave_partial_data(db):
    user = db.add_user("Alice")
    with pytest.raises(DatabaseError):
        db.add_record(user.id, -5, 1.75, 22.86, "Normal")  # violates CHECK (weight_kg > 0)
    assert db.get_records(user.id) == []


# --------------------------------------------------- failure handling (A10)
def test_corrupt_database_file_raises_database_error(tmp_path):
    path = tmp_path / "corrupt.db"
    path.write_bytes(b"this is definitely not a sqlite database file. " * 20)
    with pytest.raises(DatabaseError):
        Database(path)


def test_unusable_data_folder_raises_database_error(tmp_path):
    blocker = tmp_path / "i_am_a_file.txt"
    blocker.write_text("x")
    with pytest.raises(DatabaseError):
        Database(blocker / "sub" / "bmi.db")


def test_read_failure_raises_database_error(db, tmp_path):
    db.db_path = tmp_path / "missing_folder" / "gone.db"  # simulate the file disappearing
    with pytest.raises(DatabaseError, match="reading users"):
        db.get_users()


def test_write_failure_raises_database_error(db, tmp_path):
    user = db.add_user("Alice")
    db.db_path = tmp_path / "missing_folder" / "gone.db"
    with pytest.raises(DatabaseError, match="saving the BMI record"):
        db.add_record(user.id, 70, 1.75, 22.86, "Normal")


def test_sqlite_errors_are_wrapped(db, monkeypatch):
    def broken_connect(*_args, **_kwargs):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(database_module.sqlite3, "connect", broken_connect)
    with pytest.raises(DatabaseError, match="disk I/O error"):
        db.get_users()

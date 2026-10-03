"""Tests for the service layer (validation + calculation + storage together)."""

from datetime import datetime

import pytest

from bmi_tracker.db.database import Database, Record
from bmi_tracker.exceptions import DatabaseError, DuplicateUserError, ValidationError
from bmi_tracker.services.tracker_service import TrackerService, build_trend_series


@pytest.fixture
def service(tmp_path):
    return TrackerService(Database(tmp_path / "service.db"))


def test_create_user_trims_name(service):
    user = service.create_user("  Alice  ")
    assert user.name == "Alice"
    assert [u.name for u in service.list_users()] == ["Alice"]


@pytest.mark.parametrize("name", ["", "   ", "bad;name"])
def test_create_user_rejects_invalid_names(service, name):
    with pytest.raises(ValidationError):
        service.create_user(name)
    assert service.list_users() == []


def test_create_user_rejects_duplicates(service):
    service.create_user("Alice")
    with pytest.raises(DuplicateUserError):
        service.create_user("ALICE")


def test_calculate_and_save_stores_a_correct_record(service):
    user = service.create_user("Alice")
    record = service.calculate_and_save(user.id, "70", "1.75")
    assert record.bmi == pytest.approx(22.86)
    assert record.category == "Normal"
    history = service.get_history(user.id)
    assert len(history) == 1
    assert history[0].bmi == record.bmi


@pytest.mark.parametrize(
    "weight, height",
    [("abc", "1.75"), ("70", "xyz"), ("-70", "1.75"), ("70", "-1.75"), ("", "1.75"), ("70", ""), ("70", "0")],
)
def test_invalid_input_is_rejected_and_nothing_is_saved(service, weight, height):
    user = service.create_user("Alice")
    with pytest.raises(ValidationError):
        service.calculate_and_save(user.id, weight, height)
    assert service.get_history(user.id) == []


def test_each_user_has_their_own_history(service):
    alice = service.create_user("Alice")
    bob = service.create_user("Bob")
    service.calculate_and_save(alice.id, "55", "1.65")
    service.calculate_and_save(bob.id, "95", "1.70")
    service.calculate_and_save(bob.id, "93", "1.70")
    assert len(service.get_history(alice.id)) == 1
    assert len(service.get_history(bob.id)) == 2
    assert service.get_history(alice.id)[0].category == "Normal"
    assert service.get_history(bob.id)[0].category == "Obese"


def test_database_failure_on_save_is_reported(service, tmp_path):
    user = service.create_user("Alice")
    service._db.db_path = tmp_path / "missing" / "gone.db"
    with pytest.raises(DatabaseError):
        service.calculate_and_save(user.id, "70", "1.75")


def test_database_failure_on_read_is_reported(service, tmp_path):
    service._db.db_path = tmp_path / "missing" / "gone.db"
    with pytest.raises(DatabaseError):
        service.list_users()


def test_get_trend_data_returns_matching_lists(service):
    user = service.create_user("Alice")
    service.calculate_and_save(user.id, "80", "1.75")
    service.calculate_and_save(user.id, "75", "1.75")
    dates, values = service.get_trend_data(user.id)
    assert len(dates) == len(values) == 2
    assert values == [26.12, 24.49]


def test_get_trend_data_for_user_without_records_is_empty(service):
    user = service.create_user("Alice")
    assert service.get_trend_data(user.id) == ([], [])


def _record(record_id, bmi, when):
    return Record(record_id, 1, 70.0, 1.75, bmi, "Normal", when)


def test_build_trend_series_orders_oldest_to_newest():
    records = [
        _record(2, 23.0, datetime(2026, 2, 1)),
        _record(1, 22.0, datetime(2026, 1, 1)),
        _record(3, 24.0, datetime(2026, 3, 1)),
    ]
    dates, values = build_trend_series(records)
    assert values == [22.0, 23.0, 24.0]
    assert dates == sorted(dates)


def test_build_trend_series_handles_empty_input():
    assert build_trend_series([]) == ([], [])

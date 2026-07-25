from sqlalchemy import create_engine, inspect

from backend.app.database.base import Base
from backend.app import models  # noqa: F401


def test_database_creates_expected_tables() -> None:
    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)
    table_names = set(inspect(engine).get_table_names())

    assert table_names == {
        "customer_balances",
        "establishment_admins",
        "establishments",
        "point_movements",
        "qr_validation_attempts",
        "recycling_events",
        "redemptions",
        "rewards",
        "settings",
        "users",
    }

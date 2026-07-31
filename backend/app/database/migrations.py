from sqlalchemy import Engine, inspect, text


def run_compatible_migrations(engine: Engine) -> None:
    datetime_type = "TIMESTAMP" if engine.dialect.name == "postgresql" else "DATETIME"
    """Amplía la base SQLite del prototipo sin borrar información existente."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    additions = {
        "establishments": {
            "code": "VARCHAR(50)",
            "description": "TEXT",
            "logo_url": "VARCHAR(500)",
            "updated_at": datetime_type,
        },
        "customer_balances": {
            "total_points_earned": "INTEGER NOT NULL DEFAULT 0",
            "total_points_redeemed": "INTEGER NOT NULL DEFAULT 0",
            "created_at": datetime_type,
        },
        "recycling_events": {
            "bottle_count": "INTEGER NOT NULL DEFAULT 1",
            "device_id": "INTEGER",
            "status": "VARCHAR(30) NOT NULL DEFAULT 'accepted'",
            "image_path": "VARCHAR(500)",
            "captured_at": datetime_type,
            "capture_identifier": "VARCHAR(100)",
            "decision": "VARCHAR(30) NOT NULL DEFAULT 'accepted'",
            "model_version": "VARCHAR(50)",
            "inference_time_ms": "NUMERIC(10, 3)",
        },
    }
    with engine.begin() as connection:
        for table, columns in additions.items():
            if table not in tables:
                continue
            existing = {column["name"] for column in inspect(engine).get_columns(table)}
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
        if "establishments" in tables:
            connection.execute(
                text("UPDATE establishments SET code = 'LEGACY-' || id WHERE code IS NULL")
            )
            connection.execute(
                text("CREATE UNIQUE INDEX IF NOT EXISTS ix_establishments_code ON establishments (code)")
            )
        if "customer_balances" in tables:
            connection.execute(
                text("UPDATE customer_balances SET total_points_earned = points WHERE total_points_earned = 0 AND points > 0")
            )
        if "recycling_events" in tables:
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "ix_recycling_events_capture_identifier "
                    "ON recycling_events (capture_identifier)"
                )
            )

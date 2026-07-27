from backend.app.database.migrations import run_compatible_migrations
from backend.app.database.seed import seed_phase_one
from backend.app.database.session import SessionLocal, engine
from backend.app.database.base import Base


def main() -> None:
    from backend.app import models  # noqa: F401
    Base.metadata.create_all(engine)
    run_compatible_migrations(engine)
    with SessionLocal() as database:
        seed_phase_one(database)
    print("Fase 1 cargada: tres locales y cuentas de demostración disponibles.")


if __name__ == "__main__":
    main()

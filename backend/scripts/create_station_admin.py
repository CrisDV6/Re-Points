from getpass import getpass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.session import SessionLocal, init_database
from backend.app.models.entities import Establishment, EstablishmentAdmin, User, UserRole
from backend.app.services.security import hash_password


def create_station_admin(
    database: Session,
    establishment_name: str,
    full_name: str,
    email: str,
    password: str,
) -> tuple[Establishment, User]:
    normalized_email = email.strip().lower()
    establishment_name = establishment_name.strip()
    full_name = full_name.strip()

    if not establishment_name or len(full_name) < 3:
        raise ValueError("Completa el nombre del establecimiento y del administrador")
    if "@" not in normalized_email or "." not in normalized_email.split("@")[-1]:
        raise ValueError("El correo electrónico no es válido")
    if len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")

    establishment = database.scalar(
        select(Establishment).where(Establishment.name == establishment_name)
    )
    if establishment is None:
        establishment = Establishment(name=establishment_name)
        database.add(establishment)
        database.flush()

    user = database.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        user = User(
            full_name=full_name,
            email=normalized_email,
            password_hash=hash_password(password),
            public_identifier=str(uuid4()),
            role=UserRole.ESTABLISHMENT_ADMIN,
        )
        database.add(user)
        database.flush()
    elif user.role != UserRole.ESTABLISHMENT_ADMIN:
        raise ValueError("Ese correo ya pertenece a una cuenta con otro rol")

    assignment = database.scalar(
        select(EstablishmentAdmin).where(
            EstablishmentAdmin.user_id == user.id,
            EstablishmentAdmin.establishment_id == establishment.id,
        )
    )
    if assignment is None:
        database.add(EstablishmentAdmin(user_id=user.id, establishment_id=establishment.id))

    database.commit()
    database.refresh(establishment)
    database.refresh(user)
    return establishment, user


def main() -> None:
    print("\nConfiguración de la estación Re-Points\n")
    establishment_name = input("Nombre del establecimiento: ")
    full_name = input("Nombre del administrador: ")
    email = input("Correo del administrador: ")
    password = getpass("Contraseña (mínimo 8 caracteres): ")
    confirmation = getpass("Repite la contraseña: ")

    if password != confirmation:
        raise SystemExit("Las contraseñas no coinciden. No se realizó ningún cambio.")

    init_database()
    try:
        with SessionLocal() as database:
            establishment, user = create_station_admin(
                database,
                establishment_name,
                full_name,
                email,
                password,
            )
    except ValueError as error:
        raise SystemExit(f"No se pudo completar: {error}") from error

    print(f"\nEstablecimiento listo: {establishment.name}")
    print(f"Administrador listo: {user.email}")
    print("Ya puedes iniciar el servidor e ingresar a /estacion.")


if __name__ == "__main__":
    main()

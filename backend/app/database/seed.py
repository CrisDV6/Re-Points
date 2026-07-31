import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.entities import CustomerBalance, Device, Establishment, EstablishmentAdmin, LocalRewardRule, Setting, User, UserRole, WasteType
from backend.app.services.security import hash_password


DEMO_LOCALS = (
    ("EcoMarket Centro", "LOCAL-ECO-001", "Supermercado ecológico ubicado en el centro de la ciudad.", "Avenida Central y Calle 10", 10, 15),
    ("Green Store Norte", "LOCAL-GREEN-002", "Tienda sostenible ubicada en la zona norte.", "Avenida del Norte y Calle Verde", 8, 12),
    ("Recycle Shop Sur", "LOCAL-RECYCLE-003", "Local especializado en productos reciclados.", "Avenida Sur y Calle Ambiental", 12, 18),
)

DEMO_DEVICES = (
    ("RASPI-ECO-001", "LOCAL-ECO-001", "Raspberry EcoMarket"),
    ("RASPI-GREEN-001", "LOCAL-GREEN-002", "Raspberry Green Store"),
    ("RASPI-RECYCLE-001", "LOCAL-RECYCLE-003", "Raspberry Recycle Shop"),
)
DEMO_DEVICE_API_KEY = os.getenv("DEMO_DEVICE_API_KEY", "change-this-demo-device-key")
DEMO_CLIENT_PASSWORD = os.getenv("DEMO_CLIENT_PASSWORD", "change-this-demo-client-password")
DEMO_ADMIN_PASSWORD = os.getenv("DEMO_ADMIN_PASSWORD", "change-this-demo-admin-password")


def _user(database: Session, email: str, name: str, role: UserRole, password: str, reset_password: bool = False) -> User:
    user = database.scalar(select(User).where(User.email == email))
    if user is None:
        from uuid import uuid4
        user = User(email=email, full_name=name, password_hash=hash_password(password), public_identifier=str(uuid4()), role=role, is_active=True)
        database.add(user)
        database.flush()
    elif reset_password:
        user.password_hash = hash_password(password)
    return user


def seed_phase_one(database: Session) -> None:
    credentials_seeded = database.scalar(select(Setting).where(Setting.key == "phase1_demo_credentials_v1"))
    reset_demo_passwords = credentials_seeded is None
    locals_by_code = {}
    for name, code, description, address, plastic, glass in DEMO_LOCALS:
        local = database.scalar(select(Establishment).where(Establishment.code == code))
        if local is None:
            local = Establishment(name=name, code=code)
            database.add(local)
        local.description, local.address = description, address
        local.plastic_points, local.glass_points, local.is_active = plastic, glass, True
        database.flush()
        locals_by_code[code] = local

    demo = _user(database, "usuario@repoints.com", "Usuario Demo", UserRole.CLIENT, DEMO_CLIENT_PASSWORD, reset_demo_passwords)
    _user(database, "admin@repoints.com", "Administrador General", UserRole.SUPERADMIN, DEMO_ADMIN_PASSWORD, reset_demo_passwords).role = UserRole.SUPERADMIN
    for email, code in (
        ("admin.eco@repoints.com", "LOCAL-ECO-001"),
        ("admin.green@repoints.com", "LOCAL-GREEN-002"),
        ("admin.recycle@repoints.com", "LOCAL-RECYCLE-003"),
    ):
        admin = _user(database, email, f"Administrador {locals_by_code[code].name}", UserRole.ESTABLISHMENT_ADMIN, DEMO_ADMIN_PASSWORD, reset_demo_passwords)
        assignment = database.scalar(select(EstablishmentAdmin).where(EstablishmentAdmin.user_id == admin.id, EstablishmentAdmin.establishment_id == locals_by_code[code].id))
        if assignment is None:
            database.add(EstablishmentAdmin(user_id=admin.id, establishment_id=locals_by_code[code].id))

    for local in locals_by_code.values():
        balance = database.scalar(select(CustomerBalance).where(CustomerBalance.user_id == demo.id, CustomerBalance.establishment_id == local.id))
        if balance is None:
            database.add(CustomerBalance(user_id=demo.id, establishment_id=local.id, points=50, total_points_earned=50, total_points_redeemed=0))
    for device_code, local_code, name in DEMO_DEVICES:
        device = database.scalar(select(Device).where(Device.device_code == device_code))
        if device is None:
            device = Device(device_code=device_code, establishment_id=locals_by_code[local_code].id, name=name, api_key_hash=hash_password(DEMO_DEVICE_API_KEY), is_active=True)
            database.add(device)
    for local_code, local in locals_by_code.items():
        values = {
            WasteType.PLASTIC: local.plastic_points,
            WasteType.GLASS: local.glass_points,
        }
        for material, points in values.items():
            rule = database.scalar(select(LocalRewardRule).where(LocalRewardRule.establishment_id == local.id, LocalRewardRule.material == material))
            if rule is None:
                database.add(LocalRewardRule(establishment_id=local.id, material=material, points=points, minimum_confidence="0.80", is_active=True))
    if credentials_seeded is None:
        database.add(Setting(key="phase1_demo_credentials_v1", value="loaded", description="Evita restablecer claves demo en cada inicio"))
    database.commit()

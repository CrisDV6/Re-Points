from uuid import uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.base import Base
from backend.app.database.session import get_database_session
from backend.app.main import app
from backend.app.models.entities import CustomerBalance, Establishment, EstablishmentAdmin, PointMovement, RecyclingEvent, User, UserRole
from backend.app.services.security import hash_password

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(bind=engine, expire_on_commit=False)

def database_override():
    with Session() as database:
        yield database

def make_user(database, email, role):
    user = User(full_name=email.split("@")[0].title(), email=email, password_hash=hash_password("ClaveSegura123"), public_identifier=str(uuid4()), role=role)
    database.add(user); database.commit(); database.refresh(user)
    return user

def login(client, email):
    assert client.post("/auth/login", json={"email": email, "password": "ClaveSegura123"}).status_code == 200

def test_deposit_awards_points_and_populates_history_and_dashboard(client):
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    app.dependency_overrides[get_database_session] = database_override
    try:
        with Session() as database:
            owner = make_user(database, "owner@example.com", UserRole.ESTABLISHMENT_ADMIN)
            customer = make_user(database, "customer@example.com", UserRole.CLIENT)
            place = Establishment(name="Eco Centro", plastic_points=5, glass_points=8)
            database.add(place); database.flush()
            database.add(EstablishmentAdmin(user_id=owner.id, establishment_id=place.id)); database.commit()
        login(client, owner.email)
        response = client.post("/station/deposits", json={"public_identifier": customer.public_identifier, "plastic_bottles": 3, "glass_bottles": 2})
        assert response.status_code == 201
        assert response.json()["bottle_count"] == 5
        assert response.json()["points_awarded"] == 31
        assert response.json()["new_balance"] == 31
        dashboard = client.get("/station/dashboard")
        assert dashboard.status_code == 200
        assert dashboard.json()["total_bottles"] == 5
        assert dashboard.json()["points_awarded"] == 31
        assert dashboard.json()["unique_clients"] == 1
        assert client.get("/panel-dueno").status_code == 200
        client.post("/auth/logout"); login(client, customer.email)
        history = client.get("/client/history")
        assert history.status_code == 200
        assert history.json()["total_points"] == 31
        assert len(history.json()["movements"]) == 2
        assert "31" in client.get("/mi-historial").text
        with Session() as database:
            assert database.scalar(select(func.count(RecyclingEvent.id))) == 2
            assert database.scalar(select(func.count(PointMovement.id))) == 2
            assert database.scalar(select(CustomerBalance.points)) == 31
    finally:
        app.dependency_overrides.clear()

def test_deposit_rejects_empty_delivery_and_unassigned_owner(client):
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    app.dependency_overrides[get_database_session] = database_override
    try:
        with Session() as database:
            owner = make_user(database, "owner2@example.com", UserRole.ESTABLISHMENT_ADMIN)
            customer = make_user(database, "customer2@example.com", UserRole.CLIENT)
        login(client, owner.email)
        empty = client.post("/station/deposits", json={"public_identifier": customer.public_identifier, "plastic_bottles": 0, "glass_bottles": 0})
        assert empty.status_code == 422
        unassigned = client.post("/station/deposits", json={"public_identifier": customer.public_identifier, "plastic_bottles": 1, "glass_bottles": 0})
        assert unassigned.status_code == 403
    finally:
        app.dependency_overrides.clear()

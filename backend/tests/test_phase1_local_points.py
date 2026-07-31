from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.base import Base
from backend.app.database.seed import DEMO_CLIENT_PASSWORD, DEMO_LOCALS, seed_phase_one
from backend.app.database.session import get_database_session
from backend.app.main import app
from backend.app.models.entities import CustomerBalance, Establishment, User


engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(bind=engine, expire_on_commit=False)


def override_database():
    with TestSession() as database:
        yield database


def test_phase_one_seed_and_points_by_local_api(client):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestSession() as database:
        seed_phase_one(database)
        seed_phase_one(database)
        assert len(database.scalars(select(Establishment).where(Establishment.code.in_([item[1] for item in DEMO_LOCALS]))).all()) == 3
        demo = database.scalar(select(User).where(User.email == "usuario@repoints.com"))
        assert len(database.scalars(select(CustomerBalance).where(CustomerBalance.user_id == demo.id)).all()) == 3

    app.dependency_overrides[get_database_session] = override_database
    try:
        login = client.post("/auth/login", json={"email": "usuario@repoints.com", "password": DEMO_CLIENT_PASSWORD})
        assert login.status_code == 200
        logged_home = client.get("/")
        assert "RESUMEN DE TU CUENTA" in logged_home.text
        assert "150" in logged_home.text
        assert "Registrarme en Re-Points" not in logged_home.text
        assert "Reciclar en tres pasos" not in logged_home.text
        assert "BENEFICIOS COMPARTIDOS" not in logged_home.text
        response = client.get("/api/users/me/points")
        assert response.status_code == 200
        payload = response.json()
        assert payload["generalBalance"] == 150
        assert [item["pointsBalance"] for item in payload["locals"]] == [50, 50, 50]
        assert {item["localCode"] for item in payload["locals"]} == {item[1] for item in DEMO_LOCALS}
        one_local = client.get(f'/api/users/me/points/{payload["locals"][0]["localId"]}')
        assert one_local.status_code == 200
        assert one_local.json()["pointsBalance"] == 50
        page = client.get("/mi-historial")
        assert page.status_code == 200
        for name, *_ in DEMO_LOCALS:
            assert name in page.text
    finally:
        app.dependency_overrides.clear()


def test_phase_two_local_detail_public_api_and_history_filter(client):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestSession() as database:
        seed_phase_one(database)
        local = database.scalar(select(Establishment).where(Establishment.code == "LOCAL-ECO-001"))
        local_id = local.id

    app.dependency_overrides[get_database_session] = override_database
    try:
        public = client.get("/api/locals")
        assert public.status_code == 200
        assert len([item for item in public.json() if item["code"].startswith("LOCAL-")]) == 3
        assert client.get(f"/api/locals/{local_id}").json()["name"] == "EcoMarket Centro"
        assert client.get(f"/api/locals/{local_id}/rewards").json() == []

        assert client.get(f"/locales/{local_id}").status_code == 401
        assert client.get("/api/users/me/recycling-history").status_code == 401
        assert client.post("/auth/login", json={"email": "usuario@repoints.com", "password": DEMO_CLIENT_PASSWORD}).status_code == 200

        detail = client.get(f"/locales/{local_id}")
        assert detail.status_code == 200
        assert "EcoMarket Centro" in detail.text
        assert "50 puntos" in detail.text
        filtered_page = client.get("/mi-historial", params={"localId": local_id})
        assert filtered_page.status_code == 200
        assert "Historial en EcoMarket Centro" in filtered_page.text
        filtered_api = client.get("/api/users/me/recycling-history", params={"localId": local_id})
        assert filtered_api.status_code == 200
        assert filtered_api.json() == {"localId": local_id, "events": []}
    finally:
        app.dependency_overrides.clear()

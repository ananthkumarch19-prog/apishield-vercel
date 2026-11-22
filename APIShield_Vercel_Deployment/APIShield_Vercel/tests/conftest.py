"""Fixtures use real password hashing and real CSRF tokens. CSRF stays enabled."""
import pytest
from werkzeug.security import generate_password_hash
from application import create_app
from database.seed import seed_demo, DEMO_PASSWORD, PASSWORD_METHOD

BASE = "http://127.0.0.1"


@pytest.fixture(scope="session")
def password_hashes():
    return [generate_password_hash(DEMO_PASSWORD, method=PASSWORD_METHOD) for _ in range(4)]


@pytest.fixture
def app(tmp_path, password_hashes):
    application = create_app({"TESTING": True, "SECRET_KEY": "test-only-secret-" * 4,
                              "DATABASE": str(tmp_path / "test.sqlite"), "RESULTS_DIR": str(tmp_path / "results"),
                              "LAB_MODE": True})
    with application.app_context():
        seed_demo(password_hashes)
    assert application.config["WTF_CSRF_ENABLED"] is True
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def request(client, method, path, **kwargs):
    return client.open(path, method=method, base_url=BASE, **kwargs)


def token(client):
    return request(client, "GET", "/auth/csrf").json["csrf_token"]


def login(client, email="alice@alpha.test"):
    response = request(client, "POST", "/login", json={"email": email, "password": DEMO_PASSWORD},
                       headers={"X-CSRFToken": token(client)})
    assert response.status_code == 200
    return token(client)

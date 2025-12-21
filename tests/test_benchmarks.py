"""Performance benchmarks for Fast-EasiLogin using pytest-codspeed."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


def test_savedata_endpoint(benchmark, client):
    """Benchmark the /savedata GET endpoint."""
    response = benchmark(client.get, "/savedata")
    assert response.status_code == 200


def test_get_sso_list_endpoint(benchmark, client):
    """Benchmark the /getData/SSOLOGIN endpoint."""
    response = benchmark(client.get, "/getData/SSOLOGIN")
    assert response.status_code == 200


def test_sso_logout_endpoint(benchmark, client):
    """Benchmark the /getData/SSOLOGOUT endpoint."""
    response = benchmark(client.get, "/getData/SSOLOGOUT")
    assert response.status_code == 200


def test_delete_data_endpoint(benchmark, client):
    """Benchmark the /deleteData DELETE endpoint."""
    response = benchmark(client.delete, "/deleteData")
    assert response.status_code == 200

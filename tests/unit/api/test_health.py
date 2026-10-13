from fastapi.testclient import TestClient

from datos.api.app import create_app


class FixedProbe:
    def __init__(self, *, reachable: bool) -> None:
        self._reachable = reachable

    def is_reachable(self) -> bool:
        return self._reachable


def test_reports_the_database_up_with_200_when_it_answers() -> None:
    client = TestClient(create_app(database_probe=FixedProbe(reachable=True)))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"database": "up"}


def test_reports_the_database_down_with_503_when_it_does_not_answer() -> None:
    client = TestClient(create_app(database_probe=FixedProbe(reachable=False)))

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"database": "down"}

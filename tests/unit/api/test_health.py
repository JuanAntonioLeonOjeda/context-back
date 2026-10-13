from collections.abc import Callable

from fastapi.testclient import TestClient


def test_reports_the_database_up_with_200_when_it_answers(
    make_client: Callable[..., TestClient],
) -> None:
    response = make_client(reachable=True).get("/health")

    assert response.status_code == 200
    assert response.json() == {"database": "up"}


def test_reports_the_database_down_with_503_when_it_does_not_answer(
    make_client: Callable[..., TestClient],
) -> None:
    response = make_client(reachable=False).get("/health")

    assert response.status_code == 503
    assert response.json() == {"database": "down"}

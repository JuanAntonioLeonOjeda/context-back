from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from datos.api.provider import built_on, per_request


class Connections:
    """Counts what is opened and closed, as a database engine would."""

    def __init__(self) -> None:
        self.opened = 0
        self.open_now = 0

    @contextmanager
    def connect(self) -> Iterator[int]:
        self.opened += 1
        self.open_now += 1
        try:
            yield self.opened
        finally:
            self.open_now -= 1


class ReaderA:
    def __init__(self, connection: int) -> None:
        self.connection = connection


class ReaderB:
    def __init__(self, connection: int) -> None:
        self.connection = connection


def _app(connections: Connections) -> FastAPI:
    connection = per_request(connections.connect)
    a_reader = built_on(connection, ReaderA)
    b_reader = built_on(connection, ReaderB)
    app = FastAPI()

    @app.get("/both")
    def both(
        a: Annotated[ReaderA, Depends(a_reader)], b: Annotated[ReaderB, Depends(b_reader)]
    ) -> dict[str, int]:
        return {"a": a.connection, "b": b.connection, "open": connections.open_now}

    return app


def test_every_reader_of_a_request_shares_one_connection() -> None:
    connections = Connections()

    body = TestClient(_app(connections)).get("/both").json()

    assert body["a"] == body["b"]
    assert connections.opened == 1


def test_the_connection_is_open_during_the_request_and_closed_after_it() -> None:
    connections = Connections()

    body = TestClient(_app(connections)).get("/both").json()

    assert body["open"] == 1
    assert connections.open_now == 0


def test_each_request_gets_its_own_connection() -> None:
    connections = Connections()
    client = TestClient(_app(connections))

    first = client.get("/both").json()
    second = client.get("/both").json()

    assert first["a"] != second["a"]
    assert connections.opened == 2

"""How the API receives its readers: a FastAPI dependency that gives one per request.

A plain function (tests: `lambda: fake`), or a reader built on the request's database
connection (the composition root). FastAPI resolves a dependency once per request and shares
the value with every dependant, so all the readers of one request use one connection, opened
before the handler and closed after the response.
"""

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from typing import Annotated

from fastapi import Depends

type Provider[T] = Callable[..., T] | Callable[..., Iterator[T]]


def per_request[C](
    open_resource: Callable[[], AbstractContextManager[C]],
) -> Callable[[], Iterator[C]]:
    """A dependency that opens the resource for a request and closes it when the request ends."""

    def dependency() -> Iterator[C]:
        with open_resource() as resource:
            yield resource

    return dependency


def built_on[C, R](
    resource: Callable[[], Iterator[C]], build: Callable[[C], R]
) -> Callable[..., R]:
    """A dependency that builds `R` on the request's shared resource (one per request, not one
    per reader)."""

    def dependency(value: Annotated[C, Depends(resource)]) -> R:
        return build(value)

    return dependency

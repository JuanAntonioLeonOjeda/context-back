"""How the API receives its readers: a FastAPI dependency that gives one per request.

A plain function (tests: `lambda: fake`) or a generator that opens and closes a database
connection around the request (the composition root).
"""

from collections.abc import Callable, Iterator

type Provider[T] = Callable[[], T] | Callable[[], Iterator[T]]

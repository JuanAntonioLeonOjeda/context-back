"""The encoder that turns an article into a vector: the only code of this module that imports
sentence-transformers.

It needs the `ml` dependency group (`uv sync --group ml`), which is never in the API image. The
library is imported inside `load`, so importing this module loads no torch.
"""

from collections.abc import Sequence
from typing import Any, Protocol


class SentenceModel(Protocol):
    """What the adapter needs of a SentenceTransformer; a fake in the unit tests."""

    max_seq_length: int

    def encode(self, sentences: list[str], **options: Any) -> Any:  # noqa: ANN401 - numpy array
        ...


class SentenceEncoder:
    def __init__(self, name: str, model: SentenceModel) -> None:
        self.name = name
        # What changes the vectors: the model and how much text it reads. The weights' revision is
        # not pinned (the classifier does not pin it either, ADR-0016).
        self.version = f"{name.rsplit('/', 1)[-1]}-max{model.max_seq_length}"
        self._model = model

    @classmethod
    def load(cls, name: str) -> "SentenceEncoder":
        from sentence_transformers import SentenceTransformer  # lazy on purpose, see above

        model: SentenceModel = SentenceTransformer(name)
        return cls(name, model)

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        # Normalised, so the cosine similarity of two vectors is their dot product.
        vectors = self._model.encode(list(texts), normalize_embeddings=True)
        return [[float(value) for value in vector] for vector in vectors]

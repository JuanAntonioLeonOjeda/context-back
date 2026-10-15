"""Trained models on the local disk, out of git (`models/`, ADR-0016).

A model is a directory named after its training set, encoder and seed. Its version is a hash of
every file in it except its card: two trainings can differ in the bit on a CPU, and the version
must name what actually classified. The card is written after, so it is not part of that hash.
"""

import hashlib
from pathlib import Path

from datos.classification.application.train_model import CARD_FILE, TrainedModel

VERSION_LENGTH = 12


class LocalModelStore:
    def __init__(self, root: Path) -> None:
        self._root = root

    def exists(self, name: str) -> bool:
        return (self._root / name).exists()

    def save(self, name: str, model: TrainedModel) -> str:
        directory = self._root / name
        directory.mkdir(parents=True, exist_ok=False)  # never into an existing model
        model.save(directory)
        return directory_hash(directory)

    def write_card(self, name: str, card: str) -> None:
        (self._root / name / CARD_FILE).write_text(card, encoding="utf-8")


def directory_hash(directory: Path) -> str:
    """A hash of the files (names and contents) of a model directory, its card left out."""
    digest = hashlib.sha256()
    for path in sorted(p for p in directory.rglob("*") if p.is_file() and p.name != CARD_FILE):
        digest.update(path.relative_to(directory).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:VERSION_LENGTH]

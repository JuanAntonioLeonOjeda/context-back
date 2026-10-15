"""Trains the own model with SetFit (ADR-0016). Needs the `ml` group, never in the API image.

SetFit is imported inside `train`, so importing this module loads nothing. Training checkpoints go
to a temporary directory: SetFit writes them to `./checkpoints`, inside the repository, by default.
"""

import tempfile
from collections.abc import Mapping, Sequence
from importlib.metadata import version
from pathlib import Path
from typing import Any

from datos.classification.application.train_model import TrainingConfig

LIBRARIES = ("setfit", "sentence-transformers", "transformers", "torch")


class TrainedSetFit:
    """A model just trained: saved by the training job, asked for probabilities by the curve."""

    def __init__(self, model: Any, labels: Sequence[str], environment: Mapping[str, str]) -> None:  # noqa: ANN401 - SetFit is untyped
        self._model = model
        self._labels = list(labels)
        self.environment = environment

    def save(self, directory: Path) -> None:
        self._model.save_pretrained(str(directory))

    def predict_proba(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        rows = [
            [float(p) for p in row] for row in self._model.predict_proba(list(texts), as_numpy=True)
        ]
        # Every row must have one probability per label, in their order: a shorter row zipped
        # with the labels later would silently drop a label.
        if len(rows) != len(texts) or any(len(row) != len(self._labels) for row in rows):
            raise ValueError(f"expected {len(texts)} rows of {len(self._labels)} probabilities")
        return rows


class SetFitModelTrainer:
    def train(
        self,
        *,
        texts: Sequence[str],
        targets: Sequence[Sequence[int]],
        labels: Sequence[str],
        config: TrainingConfig,
    ) -> TrainedSetFit:
        from datasets import Dataset  # lazy on purpose, see the module docstring
        from setfit import SetFitModel, Trainer, TrainingArguments

        model = SetFitModel.from_pretrained(
            config.encoder, multi_target_strategy="one-vs-rest", labels=list(labels)
        )
        dataset = Dataset.from_dict({"text": list(texts), "label": [list(t) for t in targets]})
        with tempfile.TemporaryDirectory(prefix="setfit-") as checkpoints:
            args = TrainingArguments(
                output_dir=checkpoints,
                batch_size=config.batch_size,
                num_epochs=config.num_epochs,
                body_learning_rate=config.body_learning_rate,
                sampling_strategy=config.sampling_strategy,
                num_iterations=config.num_iterations,
                seed=config.seed,
                save_strategy="no",
            )
            Trainer(model=model, args=args, train_dataset=dataset).train()
        environment = {"device": str(model.model_body.device)} | {
            library: version(library) for library in LIBRARIES
        }
        return TrainedSetFit(model, labels, environment)


def count_pairs(
    texts: Sequence[str], targets: Sequence[Sequence[int]], config: TrainingConfig
) -> int:
    """How many sentence pairs SetFit will draw: the work to do, and so the time it takes."""
    from setfit.sampler import ContrastiveDataset  # lazy on purpose, see the module docstring

    pairs = ContrastiveDataset(
        list(texts),
        [list(t) for t in targets],
        multilabel=True,
        num_iterations=config.num_iterations,
        sampling_strategy=config.sampling_strategy,
    )
    return len(pairs)


def device_name() -> str:
    """Where torch will train: the Apple GPU, CUDA or the CPU, as a person reads it."""
    import torch  # lazy on purpose, see the module docstring

    if torch.backends.mps.is_available():
        return "mps (Apple GPU)"
    return "cuda" if torch.cuda.is_available() else "cpu"

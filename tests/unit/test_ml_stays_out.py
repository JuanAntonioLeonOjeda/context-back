"""The `ml` dependency group (torch and the rest) is never in what the API runs (ADR-0016)."""

import re
import tomllib
from pathlib import Path

HEAVY = ("setfit", "torch", "sentence_transformers", "transformers", "datasets")
ADAPTERS = [
    Path("src/datos/classification/infrastructure/setfit_predictor.py"),
    Path("src/datos/classification/infrastructure/setfit_trainer.py"),
    Path("src/datos/stories/infrastructure/sentence_encoder.py"),
]


def test_ml_is_not_a_default_group() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert "ml" in pyproject["dependency-groups"]
    assert "ml" not in pyproject["tool"]["uv"]["default-groups"]


def test_the_api_image_installs_no_optional_group() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    syncs = [line for line in dockerfile.splitlines() if line.startswith("RUN uv sync")]

    assert syncs
    assert all("--no-default-groups" in line for line in syncs)
    assert not re.search(r"--(all-groups|group)\b", dockerfile)


def test_no_module_imports_the_heavy_libraries_at_the_top_level() -> None:
    # An import inside a function is lazy and costs nothing until it runs; at the top of a module
    # it would load torch for anything that merely imports the module, the API included.
    pattern = re.compile(rf"^(from|import)\s+({'|'.join(HEAVY)})\b", re.MULTILINE)

    offenders = [
        str(path)
        for path in sorted(Path("src").rglob("*.py"))
        if pattern.search(path.read_text(encoding="utf-8"))
    ]

    assert offenders == []


def test_only_the_ml_adapters_import_them_at_all() -> None:
    pattern = re.compile(rf"^\s*(from|import)\s+({'|'.join(HEAVY)})\b", re.MULTILINE)

    importers = [
        path
        for path in sorted(Path("src").rglob("*.py"))
        if pattern.search(path.read_text(encoding="utf-8"))
    ]

    assert importers == ADAPTERS

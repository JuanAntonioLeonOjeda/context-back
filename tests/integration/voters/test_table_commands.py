"""`load-age` and `load-born-abroad` on a real database, with the INE's files trimmed."""

import shutil
import sys
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from datos.voters.__main__ import main

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).parents[2] / "fixtures" / "ine"


def _run(monkeypatch: pytest.MonkeyPatch, engine: Engine, command: str, *arguments: str) -> None:
    url = engine.url.render_as_string(hide_password=False)
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(sys, "argv", ["datos.voters", command, *arguments])
    main()


def _loaded(engine: Engine) -> list[tuple[str, str, str]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT l.dimension, v.municipality_code, v.value::text FROM municipal_values v"
                " JOIN municipal_value_loads l ON l.id = v.load_id ORDER BY 1, 2"
            )
        )
        return [(dimension, code, value) for dimension, code, value in rows]


def test_the_age_is_the_share_aged_70_or_over_of_the_population_of_15_or_more(
    monkeypatch: pytest.MonkeyPatch, engine: Engine, tmp_path: Path
) -> None:
    table = tmp_path / "66620.csv"
    shutil.copy(FIXTURES / "education-66620-sample.csv", table)

    _run(monkeypatch, engine, "load-age", "--year", "2023", "--file", str(table))

    assert _loaded(engine) == [
        ("age", "01001", "11.215"),  # (181 + 81 + 13) / 2,452 = 0.112153…
        ("age", "28079", "17.381"),  # (275,354 + 178,766 + 54,291) / 2,925,135 = 0.173813…
    ]


def test_born_abroad_is_the_share_of_foreigners_over_all_the_population_of_15_or_more(
    monkeypatch: pytest.MonkeyPatch, engine: Engine, tmp_path: Path
) -> None:
    table = tmp_path / "66621.csv"
    shutil.copy(FIXTURES / "born-abroad-66621-sample.csv", table)

    _run(monkeypatch, engine, "load-born-abroad", "--year", "2023", "--file", str(table))

    assert _loaded(engine) == [
        ("born_abroad", "01001", "16.843"),  # 413 / 2,452 = 0.168433…
        ("born_abroad", "28079", "28.317"),  # 828,310 / 2,925,135 = 0.283168…
    ]
    with engine.connect() as connection:
        page = connection.execute(text("SELECT source_url FROM municipal_value_loads")).scalar_one()
    assert page == "https://www.ine.es/jaxiT3/Tabla.htm?t=66621"


def test_age_and_education_of_the_same_file_are_separate_loads(
    monkeypatch: pytest.MonkeyPatch, engine: Engine, tmp_path: Path
) -> None:
    table = tmp_path / "66620.csv"
    shutil.copy(FIXTURES / "education-66620-sample.csv", table)

    _run(monkeypatch, engine, "load-education", "--year", "2023", "--file", str(table))
    _run(monkeypatch, engine, "load-age", "--year", "2023", "--file", str(table))

    assert [(dimension, code) for dimension, code, _ in _loaded(engine)] == [
        ("age", "01001"),
        ("age", "28079"),
        ("education", "01001"),
        ("education", "28079"),
    ]


def test_a_file_of_another_dimension_stops_the_load(
    monkeypatch: pytest.MonkeyPatch, engine: Engine, tmp_path: Path
) -> None:
    table = tmp_path / "66621.csv"
    shutil.copy(FIXTURES / "born-abroad-66621-sample.csv", table)

    with pytest.raises(SystemExit) as stop:
        _run(monkeypatch, engine, "load-age", "--year", "2023", "--file", str(table))

    assert stop.value.code == 1
    assert _loaded(engine) == []

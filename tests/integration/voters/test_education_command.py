"""`python -m datos.voters load-education` on a real database, with the INE's files trimmed."""

import shutil
import sys
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from datos.voters.__main__ import main

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).parents[2] / "fixtures" / "ine"


@pytest.fixture
def files(tmp_path: Path) -> tuple[Path, Path]:
    big, small = tmp_path / "66620.csv", tmp_path / "66623.csv"
    shutil.copy(FIXTURES / "education-66620-sample.csv", big)
    shutil.copy(FIXTURES / "education-66623-sample.csv", small)
    return big, small


def _run(monkeypatch: pytest.MonkeyPatch, engine: Engine, *arguments: str) -> None:
    url = engine.url.render_as_string(hide_password=False)
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(sys, "argv", ["datos.voters", "load-education", *arguments])
    main()


def _values(engine: Engine) -> dict[str, str]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT municipality_code, value FROM municipal_values ORDER BY 1")
        )
        return {code: str(value) for code, value in rows}


def test_both_files_are_loaded_each_in_its_own_load(
    monkeypatch: pytest.MonkeyPatch, engine: Engine, files: tuple[Path, Path]
) -> None:
    _run(monkeypatch, engine, "--year", "2023", "--file", str(files[0]), "--file", str(files[1]))

    assert _values(engine) == {
        "01001": "43.026",  # 1,055 / 2,452 = 0.430261…
        "01006": "40.580",  # 84 / 207
        "01011": "29.856",  # 83 / 278
        "28079": "46.315",  # 1,354,780 / 2,925,135
    }
    with engine.connect() as connection:
        loads = connection.execute(
            text("SELECT source_file, source_url FROM municipal_value_loads ORDER BY 1")
        ).all()
    assert [tuple(load) for load in loads] == [
        ("66620.csv", "https://www.ine.es/jaxiT3/Tabla.htm?t=66620"),
        ("66623.csv", "https://www.ine.es/jaxiT3/Tabla.htm?t=66623"),
    ]


def test_running_it_again_stores_nothing_new(
    monkeypatch: pytest.MonkeyPatch, engine: Engine, files: tuple[Path, Path]
) -> None:
    arguments = ("--year", "2023", "--file", str(files[0]), "--file", str(files[1]))
    _run(monkeypatch, engine, *arguments)
    _run(monkeypatch, engine, *arguments)

    assert len(_values(engine)) == 4


def test_a_file_that_is_not_one_of_the_tables_stops_the_load(
    monkeypatch: pytest.MonkeyPatch, engine: Engine, files: tuple[Path, Path]
) -> None:
    other = files[0].with_name("other.csv")
    files[0].rename(other)

    with pytest.raises(SystemExit) as stop:
        _run(monkeypatch, engine, "--year", "2023", "--file", str(other))

    assert stop.value.code == 1
    assert _values(engine) == {}


def test_a_year_the_files_do_not_have_stops_the_load(
    monkeypatch: pytest.MonkeyPatch, engine: Engine, files: tuple[Path, Path]
) -> None:
    with pytest.raises(SystemExit) as stop:
        _run(monkeypatch, engine, "--year", "2030", "--file", str(files[0]))

    assert stop.value.code == 1
    assert _values(engine) == {}

"""Reads the JSON export of a Label Studio project (the labelling interface in data/labelling/).

The export holds, for each task, its data (the headline and the lead among it) and its annotations.
Only the article id and the choices are read: the text never leaves this module, so it cannot end
up in a file that goes to git.
"""

import json
from pathlib import Path

from pydantic import BaseModel, ValidationError

from datos.classification.domain.labelled_export import Answer, ExportedTask
from datos.classification.domain.training_set import TrainingSetError


class _Value(BaseModel):
    choices: list[str] = []


class _Result(BaseModel):
    from_name: str
    type: str
    value: _Value | None = None


class _Annotation(BaseModel):
    result: list[_Result]
    was_cancelled: bool = False  # "Skip" in the tool


class _Data(BaseModel):
    article_id: int


class _Task(BaseModel):
    data: _Data
    annotations: list[_Annotation]


def read_label_studio_export(path: Path) -> list[ExportedTask]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise TrainingSetError(f"{path}: not found") from error
    except json.JSONDecodeError as error:
        raise TrainingSetError(f"{path}: not valid JSON: {error}") from error
    if not isinstance(raw, list):
        raise TrainingSetError(f"{path}: expected the list of tasks of a JSON export")
    tasks: list[ExportedTask] = []
    for number, item in enumerate(raw, start=1):
        try:
            task = _Task.model_validate(item)
        except ValidationError as error:
            raise TrainingSetError(f"{path}: task {number}: {error}") from error
        answers = tuple(_answer(a) for a in task.annotations if not a.was_cancelled)
        tasks.append(ExportedTask(task.data.article_id, answers))
    return tasks


def _answer(annotation: _Annotation) -> Answer:
    choices: dict[str, frozenset[str]] = {}
    for result in annotation.result:
        if result.type == "choices" and result.value is not None:
            choices[result.from_name] = frozenset(result.value.choices)
    return Answer(choices)

"""The Space's backup: a dump of the whole database uploaded to the private dataset it starts from.

The Space's disk is not persistent, so this dump is the database. `python backup.py` dumps and
uploads once; the collector and the worker run it after each of their cycles, when the data has
just changed (Hugging Face stops a Space too fast for a backup on stop, checked on 2026-11-17).
Two calls at once wait for each other. Each upload replaces the previous one and the dataset's
history is squashed, so the dataset holds one dump (about 155 MB in November 2026). The dump keeps
the leads: the dataset is private and the API never reads them (project policies: never published).
"""

import fcntl
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from huggingface_hub import HfApi

DATA_REPO = os.environ.get("DATA_REPO", "Juanan237/incontext-data")
DUMP_NAME = os.environ.get("DUMP_NAME", "live.dump")
# In the home of the Space user, not in a shared /tmp.
DUMP = Path(os.environ.get("BACKUP_DIR", str(Path.home()))) / DUMP_NAME


def log(event: str, **fields: object) -> None:
    print(json.dumps({"event": event, **fields, "at": datetime.now(UTC).isoformat()}), flush=True)


def backup() -> None:
    # The collector and the worker can finish at the same moment: one backup at a time.
    with DUMP.with_suffix(".lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        _dump_and_upload()


def _dump_and_upload() -> None:
    partial = DUMP.with_suffix(".partial")
    # Written aside and renamed: an upload never reads a dump that is still being written.
    # Fixed arguments and the image's own pg_dump (PostgreSQL 17, as the server).
    subprocess.run(  # noqa: S603 - no input from outside reaches the command
        [
            "/usr/lib/postgresql/17/bin/pg_dump",
            "--host=127.0.0.1",
            "--username=user",
            "--dbname=datos",
            "-Fc",
            "--no-owner",
            "--no-privileges",
            f"--file={partial}",
        ],
        check=True,
    )
    partial.rename(DUMP)
    api = HfApi()
    # Private on creation: the dump holds the leads.
    api.create_repo(DATA_REPO, repo_type="dataset", private=True, exist_ok=True)
    api.upload_file(
        path_or_fileobj=str(DUMP),
        path_in_repo=DUMP_NAME,
        repo_id=DATA_REPO,
        repo_type="dataset",
        commit_message="Backup of the Space",
    )
    api.super_squash_history(repo_id=DATA_REPO, repo_type="dataset")
    log("backup_uploaded", dataset=DATA_REPO, file=DUMP_NAME, bytes=DUMP.stat().st_size)


def main() -> None:
    try:
        backup()
    except Exception as error:  # said in the log and in the exit code; the next cycle tries again
        log("backup_failed", reason=str(error)[:300])
        sys.exit(1)


if __name__ == "__main__":
    main()

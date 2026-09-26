"""On-disk layout of one work item and its immutable, versioned artifacts.

    work/<work_id>/
      state.json                        current state (atomic rewrite)
      events.jsonl                      append-only history
      request.md                        the original request
      submissions/<stage>/<stage>-vN.*  every submission, including failed ones
      validations/<stage>-vN.json       every gate run on submission vN
      drafts/draft-vN.md                accepted drafts only
      human/input-vN.md                 notes and answers from people
      metrics/llm_calls.jsonl           one record per LLM call
      release/approval.json             written only by a human approval

Submissions are persisted before their gate runs, so a failed gate never loses
work. A submission becomes current only when its gate passes (``WorkState.accepted``).
Versions are chosen by numeric sort, so v10 comes after v9.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .files import normalize_newlines, read_json, read_text, sha256_text, write_json_atomic, write_text_atomic
from .state import WorkState

EXTENSIONS = {"json": "json", "markdown": "md"}


@dataclass(frozen=True)
class ArtifactRef:
    kind: str
    version: int
    path: Path
    sha256: str


class WorkItem:
    def __init__(self, root: Path) -> None:
        self.root = root

    # -- fixed paths -------------------------------------------------------
    @property
    def work_id(self) -> str:
        return self.root.name

    @property
    def state_path(self) -> Path:
        return self.root / "state.json"

    @property
    def events_path(self) -> Path:
        return self.root / "events.jsonl"

    @property
    def request_path(self) -> Path:
        return self.root / "request.md"

    @property
    def metrics_path(self) -> Path:
        return self.root / "metrics" / "llm_calls.jsonl"

    @property
    def approval_path(self) -> Path:
        return self.root / "release" / "approval.json"

    # -- state -------------------------------------------------------------
    def exists(self) -> bool:
        return self.state_path.exists()

    def load_state(self) -> WorkState:
        return WorkState.from_dict(read_json(self.state_path))

    def save_state(self, state: WorkState) -> None:
        write_json_atomic(self.state_path, state.to_dict())

    # -- versioned artifacts -----------------------------------------------
    @staticmethod
    def latest_version(folder: Path, prefix: str, ext: str) -> int:
        if not folder.exists():
            return 0
        pattern = re.compile(rf"^{re.escape(prefix)}-v(\d+)\.{re.escape(ext)}$")
        versions = [int(m.group(1)) for p in folder.iterdir() if (m := pattern.match(p.name))]
        return max(versions, default=0)

    def _put(self, folder: Path, prefix: str, ext: str, text: str) -> ArtifactRef:
        text = normalize_newlines(text)
        version = self.latest_version(folder, prefix, ext) + 1
        path = folder / f"{prefix}-v{version}.{ext}"
        if path.exists():  # never overwrite history
            raise FileExistsError(path)
        write_text_atomic(path, text)
        return ArtifactRef(prefix, version, path, sha256_text(text))

    def put_submission(self, stage: str, fmt: str, text: str) -> ArtifactRef:
        return self._put(self.root / "submissions" / stage, stage, EXTENSIONS[fmt], text)

    def submission_path(self, stage: str, fmt: str, version: int) -> Path:
        return self.root / "submissions" / stage / f"{stage}-v{version}.{EXTENSIONS[fmt]}"

    def read_submission(self, stage: str, fmt: str, version: int) -> str:
        return read_text(self.submission_path(stage, fmt, version))

    def put_draft(self, text: str) -> ArtifactRef:
        return self._put(self.root / "drafts", "draft", "md", text)

    def read_draft(self, version: int) -> str:
        return read_text(self.root / "drafts" / f"draft-v{version}.md")

    def put_human_input(self, text: str) -> ArtifactRef:
        return self._put(self.root / "human", "input", "md", text)

    def human_inputs(self) -> list[str]:
        latest = self.latest_version(self.root / "human", "input", "md")
        return [read_text(self.root / "human" / f"input-v{v}.md") for v in range(1, latest + 1)]

    def validation_path(self, stage: str, version: int) -> Path:
        return self.root / "validations" / f"{stage}-v{version}.json"

    def record_validation(self, stage: str, version: int, data: dict) -> Path:
        path = self.validation_path(stage, version)
        if path.exists():
            raise FileExistsError(path)
        write_json_atomic(path, data)
        return path

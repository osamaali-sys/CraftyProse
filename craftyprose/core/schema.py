"""Strict readers for human-authored TOML (brand files, content-type specs).

Every value is read through a ``Table``. A missing required key, a wrong type or
an unknown key raises ``SchemaError`` naming the file and key path, so a typo
can't silently fall back to a default.
"""
from __future__ import annotations

import datetime as dt
import re
import tomllib
from pathlib import Path
from typing import Any, Iterable

URL_RE = re.compile(r"^https?://[^\s/$.?#][^\s]*$")


class SchemaError(ValueError):
    pass


def load_toml(path: Path) -> "Table":
    try:
        with open(path, "rb") as fh:
            return Table(tomllib.load(fh), str(path))
    except tomllib.TOMLDecodeError as exc:
        raise SchemaError(f"{path}: invalid TOML: {exc}") from exc


class Table:
    def __init__(self, data: dict[str, Any], where: str) -> None:
        if not isinstance(data, dict):
            raise SchemaError(f"{where}: expected a table")
        self.data = data
        self.where = where
        self._seen: set[str] = set()

    def _fail(self, key: str, message: str) -> SchemaError:
        return SchemaError(f"{self.where}: '{key}' {message}")

    def _take(self, key: str, required: bool) -> Any:
        self._seen.add(key)
        if key not in self.data:
            if required:
                raise self._fail(key, "is required")
            return None
        return self.data[key]

    def has(self, key: str) -> bool:
        return key in self.data

    def str(self, key: str, *, required: bool = True, default: str = "", choices: Iterable[str] | None = None,
            nonempty: bool = True) -> str:
        value = self._take(key, required)
        if value is None:
            return default
        if not isinstance(value, str):
            raise self._fail(key, f"must be a string, got {type(value).__name__}")
        value = value.strip()
        if nonempty and not value:
            raise self._fail(key, "must not be empty")
        if choices is not None and value not in set(choices):
            raise self._fail(key, f"must be one of {sorted(set(choices))}, got {value!r}")
        return value

    def url(self, key: str, *, required: bool = True) -> str:
        value = self.str(key, required=required)
        if value and not URL_RE.match(value):
            raise self._fail(key, f"must be an http(s) URL, got {value!r}")
        return value

    def bool(self, key: str, *, default: bool | None = None) -> bool:
        value = self._take(key, default is None)
        if value is None:
            return bool(default)
        if not isinstance(value, bool):
            raise self._fail(key, "must be true or false")
        return value

    def int(self, key: str, *, default: int | None = None, minimum: int | None = None) -> int:
        value = self._take(key, default is None)
        if value is None:
            return int(default)  # type: ignore[arg-type]
        if not isinstance(value, int) or isinstance(value, bool):
            raise self._fail(key, "must be an integer")
        if minimum is not None and value < minimum:
            raise self._fail(key, f"must be at least {minimum}")
        return value

    def float(self, key: str, *, default: float | None = None, minimum: float | None = None,
              maximum: float | None = None) -> float:
        value = self._take(key, default is None)
        if value is None:
            return float(default)  # type: ignore[arg-type]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise self._fail(key, "must be a number")
        if (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
            raise self._fail(key, f"must be between {minimum} and {maximum}")
        return float(value)

    def str_list(self, key: str, *, required: bool = False, choices: Iterable[str] | None = None,
                 nonempty: bool = False) -> tuple[str, ...]:
        value = self._take(key, required)
        if value is None:
            return ()
        if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
            raise self._fail(key, "must be a list of non-empty strings")
        items = tuple(v.strip() for v in value)
        if nonempty and not items:
            raise self._fail(key, "must not be empty")
        if choices is not None:
            bad = sorted(set(items) - set(choices))
            if bad:
                raise self._fail(key, f"has unknown value(s) {bad}; allowed: {sorted(set(choices))}")
        if len(set(items)) != len(items):
            raise self._fail(key, "has duplicate values")
        return items

    def range(self, key: str, *, required: bool = True, minimum: int = 0) -> tuple[int, int] | None:
        value = self._take(key, required)
        if value is None:
            return None
        ok = (isinstance(value, list) and len(value) == 2
              and all(isinstance(v, int) and not isinstance(v, bool) for v in value))
        if not ok:
            raise self._fail(key, "must be a [min, max] pair of integers")
        lo, hi = value
        if lo < minimum or lo > hi:
            raise self._fail(key, f"must satisfy {minimum} <= min <= max, got {value}")
        return lo, hi

    def date(self, key: str, *, required: bool = True) -> dt.date | None:
        value = self._take(key, required)
        if value is None:
            return None
        if isinstance(value, dt.datetime):
            return value.date()
        if isinstance(value, dt.date):
            return value
        if isinstance(value, str):
            try:
                return dt.date.fromisoformat(value.strip())
            except ValueError:
                pass
        raise self._fail(key, "must be a date (YYYY-MM-DD)")

    def table(self, key: str, *, required: bool = False) -> "Table":
        value = self._take(key, required)
        return Table(value if value is not None else {}, f"{self.where}.{key}")

    def tables(self, key: str) -> list["Table"]:
        value = self._take(key, False)
        if value is None:
            return []
        if not isinstance(value, list) or not all(isinstance(v, dict) for v in value):
            raise self._fail(key, "must be an array of tables ([[...]])")
        return [Table(v, f"{self.where}.{key}[{i}]") for i, v in enumerate(value)]

    def int_map(self, key: str, *, minimum: int = 0) -> dict[str, int]:
        t = self.table(key)
        return {k: t.int(k, minimum=minimum) for k in list(t.data)} if t.data else {}

    def finish(self) -> None:
        unknown = sorted(set(self.data) - self._seen)
        if unknown:
            raise SchemaError(f"{self.where}: unknown key(s) {unknown}")


def unique_ids(items: Iterable[Any], where: str, attr: str = "id") -> None:
    seen: set[str] = set()
    for item in items:
        value = getattr(item, attr)
        if value in seen:
            raise SchemaError(f"{where}: duplicate {attr} {value!r}")
        seen.add(value)

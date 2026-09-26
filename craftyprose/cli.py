"""Command-line interface.

    craftyprose [--workspace DIR] new REQUEST_FILE --brand ID --type TYPE
    craftyprose brand init|check BRAND_ID
    craftyprose types
    craftyprose status|events|usage WORK_ID
    craftyprose list
    craftyprose approve WORK_ID --by NAME
    craftyprose reject WORK_ID --by NAME --reason TEXT
    craftyprose resume WORK_ID --by NAME [--note TEXT] [--grant-revisions N]

The workspace defaults to $CRAFTYPROSE_WORKSPACE, then ./workspace.
Exit codes: 0 success, 1 refused or failed, 2 usage error.
Stage execution commands arrive with the stage implementations (M4 onward).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import TextIO

from .content_types.loader import Catalog
from .core.config import ConfigError
from .core.engine import Engine, EngineError
from .core.schema import SchemaError
from .eis.contradictions import find_contradictions
from .eis.scaffold import init_brand
from .eis.workspace import load_brand


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="craftyprose", description="CraftyProse content engine")
    p.add_argument("--workspace", help="workspace directory (default: $CRAFTYPROSE_WORKSPACE or ./workspace)")
    sub = p.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="create a work item from a request file")
    new.add_argument("request_file")
    new.add_argument("--brand", required=True)
    new.add_argument("--type", required=True, dest="content_type")

    for name, text in (("status", "show state"), ("events", "show the event log"),
                       ("usage", "show LLM usage, cost and loop counts")):
        sub.add_parser(name, help=text).add_argument("work_id")
    sub.add_parser("list", help="list work items")
    sub.add_parser("types", help="list content types")

    brand = sub.add_parser("brand", help="create or check a brand workspace")
    brand_sub = brand.add_subparsers(dest="brand_command", required=True)
    brand_sub.add_parser("init", help="scaffold a brand workspace to fill in").add_argument("brand_id")
    brand_sub.add_parser("check", help="validate a brand workspace and list contradictions").add_argument("brand_id")

    approve = sub.add_parser("approve", help="release work that is ready (human action)")
    approve.add_argument("work_id")
    approve.add_argument("--by", required=True)

    reject = sub.add_parser("reject", help="reject a work item (human action)")
    reject.add_argument("work_id")
    reject.add_argument("--by", required=True)
    reject.add_argument("--reason", required=True)

    resume = sub.add_parser("resume", help="continue paused work (human action)")
    resume.add_argument("work_id")
    resume.add_argument("--by", required=True)
    resume.add_argument("--note", default="")
    resume.add_argument("--grant-revisions", type=int, default=0)
    return p


def _dump(data: object, out: TextIO) -> None:
    out.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None, *, out: TextIO | None = None, err: TextIO | None = None) -> int:
    out = out or sys.stdout
    err = err or sys.stderr
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:  # argparse reports usage errors itself
        return 0 if exc.code in (0, None) else 2
    workspace = Path(args.workspace or os.environ.get("CRAFTYPROSE_WORKSPACE") or "workspace")
    try:
        engine = Engine(workspace)
        if args.command == "new":
            catalog = Catalog()
            catalog.get(args.content_type)  # refuse unknown types before creating anything
            load_brand(workspace, args.brand, content_types=catalog.ids())  # a broken brand stops here, with the path
            text = Path(args.request_file).read_text(encoding="utf-8")
            state = engine.new(text, brand_id=args.brand, content_type=args.content_type)
            out.write(f"created {state.work_id} (stage: {state.stage})\n")
        elif args.command == "status":
            _dump(engine.status(args.work_id).to_dict(), out)
        elif args.command == "events":
            _dump(engine.events(args.work_id), out)
        elif args.command == "usage":
            _dump(engine.usage(args.work_id), out)
        elif args.command == "list":
            for work_id in engine.list():
                s = engine.status(work_id)
                out.write(f"{work_id}  {s.status.value:<22} {s.stage:<8} {s.content_type} ({s.brand_id})\n")
        elif args.command == "approve":
            state = engine.approve(args.work_id, by=args.by)
            out.write(f"{state.work_id} released, approved by {state.approval['approved_by']}\n")
        elif args.command == "reject":
            state = engine.reject(args.work_id, by=args.by, reason=args.reason)
            out.write(f"{state.work_id} rejected\n")
        elif args.command == "types":
            for ct in Catalog().types.values():
                out.write(f"{ct.id:<20} {ct.goal:<9} {ct.length[0]}-{ct.length[1]} {ct.length_unit:<10} {ct.name}\n")
        elif args.command == "brand" and args.brand_command == "init":
            root = init_brand(workspace, args.brand_id)
            out.write(f"created {root}; fill in the files, then run: craftyprose brand check {args.brand_id}\n")
        elif args.command == "brand" and args.brand_command == "check":
            ws = load_brand(workspace, args.brand_id, content_types=Catalog().ids())
            problems = find_contradictions(ws)
            out.write(f"{ws.brand.name}: {len(ws.personas)} persona(s), {len(ws.samples)} voice sample(s) "
                      f"({sum(s.provenance.human_written for s in ws.samples)} human-written), "
                      f"{len(ws.approved_claims)} approved claim(s), {len(ws.rules)} guardrail(s), "
                      f"{len(ws.open())} open question(s)\n")
            for c in problems:
                out.write(f"contradiction {c.id}: {c.detail} ({', '.join(c.files)})\n")
            if problems:
                return 1
            out.write("ok\n")
        elif args.command == "resume":
            state = engine.resume(args.work_id, by=args.by, note=args.note, grant_revisions=args.grant_revisions)
            out.write(f"{state.work_id} resumed at {state.stage}\n")
    except (EngineError, ConfigError, SchemaError, OSError, ValueError) as exc:
        err.write(f"error: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

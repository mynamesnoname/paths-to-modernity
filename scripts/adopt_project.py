#!/usr/bin/env python3
"""Adopt the Paths to Modernity protocol into a project.

The protocol lives in AGENTS.md because an agent instruction file is re-read on
every turn, while a skill body is loaded once and can be summarised away by
context compaction. This tool writes three things:

- a marked protocol block in `AGENTS.md` (pointers and four invariants only)
- a one-line `CLAUDE.md` pointing at `AGENTS.md`
- a `_aiHumanInteract/state/active.md` skeleton for recovery

Everything is idempotent and removable. Nothing overwrites content the project
already has: a differing block, `CLAUDE.md`, or state file is reported, not
replaced. Ownership is recorded when the tool writes a block or pointer
(`created_block`, `created_claude`), so removal keeps matching content the
project already had instead of inferring ownership from a hash. Use
`--upgrade-block` to move an unmodified block to the current version after
reviewing the diff, and `--uninstall` to remove only what this tool added and
left unchanged.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import sys
from pathlib import Path
from typing import Sequence

SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSET_ROOT = SKILL_ROOT / "assets" / "protocol"
START_MARKER = "<!-- paths-to-modernity:protocol:start -->"
END_MARKER = "<!-- paths-to-modernity:protocol:end -->"
MANIFEST_VERSION = 2
SUPPORTED_MANIFEST_VERSIONS = (1, 2)
MANIFEST_RELATIVE = Path("_aiHumanInteract/adopt-manifest.json")
STATE_RELATIVE = Path("_aiHumanInteract/state/active.md")
CLAUDE_POINTER = (
    "This repository is governed by `AGENTS.md`. Read it before acting; it "
    "takes precedence over tool defaults.\n"
)


class AdoptError(Exception):
    """A precondition failed or an existing file could not be reconciled."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _block() -> str:
    text = (ASSET_ROOT / "AGENTS.protocol.md").read_text(encoding="utf-8")
    return text if text.endswith("\n") else text + "\n"


def _block_bytes() -> bytes:
    return _block().rstrip("\n").encode("utf-8")


def _block_text() -> str:
    return _block().rstrip("\n")


def _protocol_version(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("<!-- schema-version:") and stripped.endswith("-->"):
            return stripped[len("<!-- schema-version:"):-3].strip()
    return "unknown"


def _diff(old: str, new: str, label: str) -> str:
    lines = list(
        difflib.unified_diff(
            old.splitlines(),
            new.splitlines(),
            fromfile=f"{label} (adopted)",
            tofile=f"{label} (current)",
            lineterm="",
        )
    )
    return "\n".join(lines)


def _state_template() -> str:
    text = (ASSET_ROOT / "state-active.md").read_text(encoding="utf-8")
    return text if text.endswith("\n") else text + "\n"


def _read_manifest(repo: Path) -> dict | None:
    path = repo / MANIFEST_RELATIVE
    if not path.exists():
        return None
    if not path.is_file():
        raise AdoptError(f"adoption manifest is not a regular file: {path}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise AdoptError(f"cannot read {path}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise AdoptError("adoption manifest must contain a JSON object")
    if manifest.get("manifest_version") not in SUPPORTED_MANIFEST_VERSIONS:
        raise AdoptError("unsupported adoption manifest version")
    return manifest


def _write_manifest(repo: Path, manifest: dict) -> None:
    path = repo / MANIFEST_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _existing_block(text: str) -> str | None:
    has_start = START_MARKER in text
    has_end = END_MARKER in text
    if has_start != has_end:
        raise AdoptError("AGENTS.md contains an unbalanced protocol marker")
    if not has_start:
        return None
    if text.count(START_MARKER) > 1:
        raise AdoptError("AGENTS.md contains more than one protocol block")
    start = text.index(START_MARKER)
    end = text.index(END_MARKER, start) + len(END_MARKER)
    return text[start:end]


def _adoption_plan(repo: Path, previous: dict) -> tuple[str | None, str, bool, bool, bool]:
    """Return (new AGENTS.md text or None, CLAUDE.md action, state create, ...)."""
    agents = repo / "AGENTS.md"
    if agents.exists() and not agents.is_file():
        raise AdoptError(f"AGENTS.md is not a regular file: {agents}")
    current = agents.read_text(encoding="utf-8") if agents.exists() else ""

    block = _block()
    existing = _existing_block(current)
    agents_text: str | None = None
    if existing is None:
        separator = "\n\n" if current.strip() else ""
        agents_text = current.rstrip() + separator + block + "\n"
    elif existing != block.strip("\n"):
        recorded = previous.get("protocol_block")
        if recorded is not None and existing == recorded:
            raise AdoptError(
                "the protocol block is outdated "
                f"({_protocol_version(existing)} -> {_protocol_version(block)}); "
                "run --upgrade-block to review the diff and replace it."
            )
        raise AdoptError(
            "AGENTS.md already carries a different protocol block, and it is not "
            "the one this manifest adopted. Reconcile it by hand before adopting "
            "again."
        )

    claude = repo / "CLAUDE.md"
    if claude.exists() and not claude.is_file():
        raise AdoptError(f"CLAUDE.md is not a regular file: {claude}")
    if claude.exists() and claude.read_text(encoding="utf-8") != CLAUDE_POINTER:
        raise AdoptError(
            "CLAUDE.md already exists with different content; merge the pointer "
            "by hand instead of overwriting it."
        )

    state = repo / STATE_RELATIVE
    if state.exists() and not state.is_file():
        raise AdoptError(f"state path is not a regular file: {state}")

    return (
        agents_text,
        "write" if not claude.exists() else "unchanged",
        not state.exists(),
        existing is None,
        not agents.exists(),
    )


def adopt(repo: Path, *, dry_run: bool = False) -> None:
    repo = repo.resolve()
    if not repo.is_dir():
        raise AdoptError(f"repository directory does not exist: {repo}")

    previous = _read_manifest(repo) or {}
    agents_text, claude_action, create_state, add_block, created_agents = _adoption_plan(
        repo, previous
    )
    # A second adoption must not forget that an earlier one created these files.
    created_agents = created_agents or previous.get("created_agents", False)
    created_claude = (claude_action == "write") or previous.get("created_claude", False)
    created_state = create_state or previous.get("created_state", False)
    # Content equality is not ownership: a project may already carry the exact
    # block or pointer. Record whether this tool inserted it, so removal can
    # keep what it found instead of inferring ownership from a matching hash.
    created_block = add_block or previous.get("created_block", False)

    print(f"Paths to Modernity protocol in {repo}")
    print(f"  AGENTS.md: {'append marked block' if add_block else 'block present, unchanged'}")
    print(f"  CLAUDE.md: {claude_action}")
    print(f"  {STATE_RELATIVE.as_posix()}: {'create' if create_state else 'kept as is'}")
    if dry_run:
        print("Dry run only; no files were changed.")
        return

    if agents_text is not None:
        (repo / "AGENTS.md").write_text(agents_text, encoding="utf-8")
    if claude_action == "write":
        (repo / "CLAUDE.md").write_text(CLAUDE_POINTER, encoding="utf-8")
    if create_state:
        state = repo / STATE_RELATIVE
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(_state_template(), encoding="utf-8")

    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "protocol_block_sha256": _sha256(_block_bytes()),
        "protocol_block": _block_text(),
        "protocol_version": _protocol_version(_block_text()),
        "claude_text": CLAUDE_POINTER,
        "claude_sha256": _sha256(CLAUDE_POINTER.encode("utf-8")),
        "state_sha256": _sha256(_state_template().encode("utf-8")),
        "created_state": created_state,
        "created_claude": created_claude,
        "created_agents": created_agents,
        "created_block": created_block,
    }
    _write_manifest(repo, manifest)
    print("Adopted.")


def upgrade_block(repo: Path, *, dry_run: bool = False) -> None:
    """Move an unmodified block to the current asset version, after showing the diff."""
    repo = repo.resolve()
    if not repo.is_dir():
        raise AdoptError(f"repository directory does not exist: {repo}")
    manifest = _read_manifest(repo)
    if manifest is None:
        raise AdoptError(
            f"no adoption manifest at {repo / MANIFEST_RELATIVE}; "
            "nothing to upgrade"
        )

    agents = repo / "AGENTS.md"
    if not agents.is_file():
        raise AdoptError(f"AGENTS.md is missing: {agents}")
    current_text = agents.read_text(encoding="utf-8")
    current = _existing_block(current_text)
    block_text = _block_text()

    if current is None:
        print("  protocol block is absent; adopting the current version")
        adopt(repo, dry_run=dry_run)
        return

    version_from = _protocol_version(current)
    version_to = _protocol_version(block_text)

    claude = repo / "CLAUDE.md"
    claude_action = "unchanged"
    if not claude.exists():
        claude_action = "create"
    elif claude.read_text(encoding="utf-8") != CLAUDE_POINTER:
        if claude.read_text(encoding="utf-8") != manifest.get("claude_text"):
            raise AdoptError(
                "CLAUDE.md was edited since adoption; reconcile it by hand."
            )
        claude_action = "update"

    if current == block_text:
        print(f"  AGENTS.md block: already current ({version_to})")
        changed = False
    else:
        recorded = manifest.get("protocol_block")
        if recorded is None:
            print(_diff(current, block_text, "protocol block"))
            raise AdoptError(
                "this manifest predates block receipts, so the block cannot be "
                "verified as unmodified. Remove the block by hand and adopt again."
            )
        if current != recorded:
            print(_diff(recorded, block_text, "protocol block"))
            raise AdoptError(
                "the protocol block was edited after adoption; the migration "
                "cannot merge your changes. Reconcile it by hand."
            )
        print(
            f"  AGENTS.md block: {version_from} -> {version_to}"
        )
        print(_diff(recorded, block_text, "protocol block"))
        changed = True

    print(f"  CLAUDE.md: {claude_action}")
    if dry_run:
        print("Dry run only; no files were changed.")
        return

    if changed:
        start = current_text.index(START_MARKER)
        end = current_text.index(END_MARKER, start) + len(END_MARKER)
        agents.write_text(
            current_text[:start] + block_text + current_text[end:], encoding="utf-8"
        )
    if claude_action in {"create", "update"}:
        claude.write_text(CLAUDE_POINTER, encoding="utf-8")
        manifest["created_claude"] = manifest.get("created_claude", False) or (
            claude_action == "create"
        )

    if changed or claude_action != "unchanged":
        manifest.update(
            {
                "protocol_block_sha256": _sha256(block_text.encode("utf-8")),
                "protocol_block": block_text,
                "protocol_version": version_to,
                "claude_text": CLAUDE_POINTER,
            }
        )
        _write_manifest(repo, manifest)
    print("Protocol block upgraded.")


def uninstall(repo: Path, *, dry_run: bool = False) -> None:
    repo = repo.resolve()
    if not repo.is_dir():
        raise AdoptError(f"repository directory does not exist: {repo}")
    manifest = _read_manifest(repo)
    if manifest is None:
        raise AdoptError(f"no adoption manifest at {repo / MANIFEST_RELATIVE}")

    agents = repo / "AGENTS.md"
    current = agents.read_text(encoding="utf-8") if agents.is_file() else ""
    existing = _existing_block(current)
    if existing is None:
        block_action = "absent"
    elif _sha256(existing.encode("utf-8")) != manifest["protocol_block_sha256"]:
        raise AdoptError(
            "the protocol block in AGENTS.md was edited since adoption; remove "
            "it by hand instead of letting the tool delete your changes."
        )
    elif "created_block" not in manifest:
        block_action = "kept (no ownership record)"
    elif not manifest["created_block"]:
        block_action = "kept (pre-existing)"
    else:
        block_action = "remove"

    claude = repo / "CLAUDE.md"
    claude_action = "absent"
    if claude.is_file():
        if _sha256(claude.read_bytes()) != manifest["claude_sha256"]:
            raise AdoptError(
                "CLAUDE.md was edited since adoption; remove it by hand."
            )
        if not manifest.get("created_claude", False):
            claude_action = "kept (pre-existing)"
        else:
            claude_action = "remove"

    state = repo / STATE_RELATIVE
    state_action = "absent"
    if state.is_file():
        if not manifest.get("created_state", False):
            state_action = "kept (pre-existing)"
        elif _sha256(state.read_bytes()) != manifest["state_sha256"]:
            state_action = "kept (edited since adoption)"
        else:
            state_action = "remove"

    print(f"Paths to Modernity protocol removal in {repo}")
    print(f"  AGENTS.md block: {block_action}")
    print(f"  CLAUDE.md: {claude_action}")
    print(f"  {STATE_RELATIVE.as_posix()}: {state_action}")
    if dry_run:
        print("Dry run only; no files were changed.")
        return

    if block_action == "remove" and existing is not None:
        start = current.index(START_MARKER)
        end = current.index(END_MARKER, start) + len(END_MARKER)
        remainder = (current[:start].rstrip() + "\n" + current[end:].lstrip()).strip()
        if remainder:
            agents.write_text(remainder + "\n", encoding="utf-8")
        elif manifest.get("created_agents", False):
            agents.unlink()
        else:
            agents.write_text("", encoding="utf-8")
    if claude_action == "remove":
        claude.unlink()
    if state_action == "remove":
        state.unlink()
        for directory in (state.parent, state.parent.parent):
            try:
                directory.rmdir()
            except OSError:
                break
    (repo / MANIFEST_RELATIVE).unlink(missing_ok=True)
    for directory in (repo / STATE_RELATIVE).parents:
        if directory == repo or directory.name != "_aiHumanInteract":
            continue
        try:
            directory.rmdir()
        except OSError:
            break
    print("Protocol removed.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--uninstall", action="store_true")
    mode.add_argument("--upgrade-block", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.uninstall:
            uninstall(args.repository, dry_run=args.dry_run)
        elif args.upgrade_block:
            upgrade_block(args.repository, dry_run=args.dry_run)
        else:
            adopt(args.repository, dry_run=args.dry_run)
    except AdoptError as exc:
        print(f"Operation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

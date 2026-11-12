#!/usr/bin/env python3
"""Install, preview, or remove unchanged Plan Graph bundle additions."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Sequence


SKILL_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_ROOT = SKILL_ROOT / "assets" / "plan-graph"
SCHEMA_VERSION = "paths-to-modernity-plan-graph-v4"
MANIFEST_VERSION = 1
PLAN_RELATIVE = Path("_aiHumanInteract/plan")
MANIFEST_RELATIVE = PLAN_RELATIVE / "install-manifest.json"
PLAN_FILES = (
    "README.md",
    "validate.py",
    "build_graph.py",
    "test_plan_graph.py",
)
PLAN_DIRS = (
    "requirements",
    "evaluations",
    "long-term",
    "mid-term",
    "short-term",
    "work-package",
    "structure",
)
START_MARKER = "<!-- paths-to-modernity:plan-graph:start -->"
END_MARKER = "<!-- paths-to-modernity:plan-graph:end -->"


class InstallError(RuntimeError):
    """Raised when installation or removal could damage target state."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _relative(path: Path, repo: Path) -> str:
    return path.relative_to(repo).as_posix()


def _manifest_path(repo: Path, value: str) -> Path:
    relative = Path(value)
    if not value or relative.is_absolute() or ".." in relative.parts:
        raise InstallError(f"unsafe path in install manifest: {value!r}")
    return repo / relative


def _fragment() -> str:
    return (BUNDLE_ROOT / "AGENTS.plan-management.md").read_text(
        encoding="utf-8"
    ).strip()


def _refuse_competing_trees(repo: Path) -> None:
    """Refuse to act while a v3 tree exists; never let two plan trees coexist."""
    legacy = repo / "_plan"
    if not legacy.is_dir():
        return
    current = repo / PLAN_RELATIVE
    if current.exists():
        raise InstallError(
            "both _plan/ and _aiHumanInteract/plan/ exist. Two plan trees cannot "
            "coexist; reconcile them by hand before reinstalling."
        )
    raise InstallError(
        "found a v3 plan tree at _plan/; v4 reads _aiHumanInteract/plan/ and "
        "will not migrate it. Run scripts/migrate_plan_graph_v3.py, or move "
        "_plan/ to _aiHumanInteract/plan/ by hand after reading the migration "
        "steps in references/plan-graph.md."
    )


def _read_manifest(repo: Path) -> dict[str, Any] | None:
    path = repo / MANIFEST_RELATIVE
    if not path.exists():
        return None
    if not path.is_file():
        raise InstallError(f"install manifest is not a regular file: {path}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise InstallError(f"cannot read install manifest: {path}") from exc
    if not isinstance(manifest, dict):
        raise InstallError("install manifest must contain a JSON object")
    if manifest.get("manifest_version") != MANIFEST_VERSION:
        raise InstallError("unsupported install manifest version")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise InstallError(
            "installed schema version differs; remove the existing installation "
            "manually instead of overwriting it"
        )
    return manifest


def _agent_block(text: str) -> str | None:
    has_start = START_MARKER in text
    has_end = END_MARKER in text
    if has_start != has_end:
        raise InstallError("AGENTS.md contains only one plan-graph marker")
    if not has_start:
        return None
    start = text.index(START_MARKER)
    end = text.index(END_MARKER, start) + len(END_MARKER)
    if START_MARKER in text[start + len(START_MARKER) : end]:
        raise InstallError("AGENTS.md contains duplicate plan-graph markers")
    return text[start:end]


def _installation_plan(
    repo: Path,
    update_agents: bool,
) -> tuple[list[tuple[Path, Path]], list[Path], str]:
    copies: list[tuple[Path, Path]] = []
    for name in PLAN_FILES:
        source = BUNDLE_ROOT / "_aiHumanInteract/plan" / name
        target = repo / "_aiHumanInteract/plan" / name
        if target.exists():
            if not target.is_file() or _sha256_file(source) != _sha256_file(target):
                raise InstallError(
                    f"refusing to overwrite differing existing file: {target}"
                )
        else:
            copies.append((source, target))

    directories = [repo / "_aiHumanInteract/plan", *(repo / "_aiHumanInteract/plan" / name for name in PLAN_DIRS)]
    created_dirs = [path for path in directories if not path.exists()]
    for path in directories:
        if path.exists() and not path.is_dir():
            raise InstallError(f"required directory path is not a directory: {path}")

    agents_action = "unchanged"
    if update_agents:
        agents = repo / "AGENTS.md"
        if agents.exists() and not agents.is_file():
            raise InstallError(f"AGENTS.md is not a regular file: {agents}")
        current = agents.read_text(encoding="utf-8") if agents.exists() else ""
        installed_block = _agent_block(current)
        if installed_block is None:
            agents_action = "create" if not agents.exists() else "append"
        elif installed_block.strip() != _fragment():
            raise InstallError(
                "AGENTS.md contains a different plan-graph block; migrate or "
                "reconcile it manually"
            )
    return copies, created_dirs, agents_action


def _print_install_plan(
    repo: Path,
    copies: list[tuple[Path, Path]],
    created_dirs: list[Path],
    agents_action: str,
    *,
    dry_run: bool,
) -> None:
    prefix = "Would install" if dry_run else "Installed"
    print(f"{prefix} Plan Graph bundle {SCHEMA_VERSION} in {repo}")
    for path in created_dirs:
        print(f"  directory: {_relative(path, repo)}/")
    for _, target in copies:
        print(f"  file: {_relative(target, repo)}")
    if agents_action != "unchanged":
        print(f"  AGENTS.md: {agents_action} marked governance block")
    if not copies and not created_dirs and agents_action == "unchanged":
        print("  no content changes")
    if dry_run:
        print("Dry run only; no files were changed.")


def install(repo: Path, update_agents: bool, *, dry_run: bool = False) -> None:
    repo = repo.resolve()
    if not repo.is_dir():
        raise InstallError(f"repository directory does not exist: {repo}")

    _refuse_competing_trees(repo)
    previous = _read_manifest(repo)
    copies, created_dirs, agents_action = _installation_plan(repo, update_agents)
    _print_install_plan(
        repo, copies, created_dirs, agents_action, dry_run=dry_run
    )
    if dry_run:
        return

    for path in created_dirs:
        path.mkdir(parents=True, exist_ok=True)
    for source, target in copies:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    agents_record = (
        dict(previous.get("agents", {})) if previous else {"mode": "unchanged"}
    )
    if agents_action != "unchanged":
        agents = repo / "AGENTS.md"
        current = agents.read_text(encoding="utf-8") if agents.exists() else ""
        separator = "\n\n" if current.strip() else ""
        agents.write_text(
            current.rstrip() + separator + _fragment() + "\n",
            encoding="utf-8",
        )
        agents_record = {
            "mode": "created" if agents_action == "create" else "appended",
            "block_sha256": _sha256_bytes(_fragment().encode("utf-8")),
        }

    created_files = dict(previous.get("created_files", {})) if previous else {}
    for source, target in copies:
        created_files[_relative(target, repo)] = _sha256_file(source)
    created_dir_names = set(previous.get("created_dirs", [])) if previous else set()
    created_dir_names.update(_relative(path, repo) for path in created_dirs)
    managed_files = {
        f"_aiHumanInteract/plan/{name}": _sha256_file(BUNDLE_ROOT / "_aiHumanInteract/plan" / name)
        for name in PLAN_FILES
    }
    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "schema_version": SCHEMA_VERSION,
        "managed_files": managed_files,
        "created_files": dict(sorted(created_files.items())),
        "created_dirs": sorted(
            created_dir_names, key=lambda value: (value.count("/"), value)
        ),
        "agents": agents_record,
    }
    manifest_path = repo / MANIFEST_RELATIVE
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"  manifest: {MANIFEST_RELATIVE.as_posix()}")
    print("Create real LT/MT/ST/WP source nodes, then validate and rebuild.")


def _removal_plan(
    repo: Path,
    manifest: dict[str, Any],
) -> tuple[list[Path], list[Path], str]:
    files: list[Path] = []
    created_files = manifest.get("created_files", {})
    if not isinstance(created_files, dict):
        raise InstallError("manifest created_files must be an object")
    for relative, expected_hash in created_files.items():
        if not isinstance(relative, str) or not isinstance(expected_hash, str):
            raise InstallError("manifest contains an invalid created_files entry")
        path = _manifest_path(repo, relative)
        if not path.exists():
            continue
        if not path.is_file() or _sha256_file(path) != expected_hash:
            raise InstallError(f"refusing to remove changed installed file: {path}")
        files.append(path)

    agents_record = manifest.get("agents", {})
    if not isinstance(agents_record, dict):
        raise InstallError("manifest agents entry must be an object")
    agents_mode = agents_record.get("mode", "unchanged")
    if agents_mode not in {"unchanged", "created", "appended"}:
        raise InstallError("manifest contains an invalid AGENTS.md mode")
    if agents_mode != "unchanged":
        agents = repo / "AGENTS.md"
        if not agents.is_file():
            raise InstallError("refusing rollback because AGENTS.md is missing")
        current = agents.read_text(encoding="utf-8")
        block = _agent_block(current)
        if block is None or block.strip() != _fragment():
            raise InstallError(
                "refusing rollback because the installed AGENTS.md block changed"
            )
        if agents_mode == "created" and current.strip() != _fragment():
            raise InstallError(
                "refusing to remove AGENTS.md because it now contains other content"
            )
    created_dirs = manifest.get("created_dirs", [])
    if not isinstance(created_dirs, list) or not all(
        isinstance(value, str) for value in created_dirs
    ):
        raise InstallError("manifest created_dirs must be an array of strings")
    directories = [_manifest_path(repo, value) for value in created_dirs]
    return files, directories, agents_mode


def uninstall(repo: Path, *, dry_run: bool = False) -> None:
    repo = repo.resolve()
    if not repo.is_dir():
        raise InstallError(f"repository directory does not exist: {repo}")
    _refuse_competing_trees(repo)
    manifest = _read_manifest(repo)
    if manifest is None:
        raise InstallError(f"no install manifest found at {repo / MANIFEST_RELATIVE}")
    files, directories, agents_mode = _removal_plan(repo, manifest)

    prefix = "Would remove" if dry_run else "Removing"
    print(f"{prefix} manifest-owned Plan Graph additions from {repo}")
    for path in files:
        print(f"  file: {_relative(path, repo)}")
    for path in sorted(
        directories,
        key=lambda value: len(value.relative_to(repo).parts),
        reverse=True,
    ):
        print(f"  directory if empty: {_relative(path, repo)}/")
    if agents_mode != "unchanged":
        print(f"  AGENTS.md: remove unchanged marked block ({agents_mode})")
    print(f"  manifest: {MANIFEST_RELATIVE.as_posix()}")
    if dry_run:
        print("Dry run only; no files were changed.")
        return

    for path in files:
        path.unlink()

    if agents_mode != "unchanged":
        agents = repo / "AGENTS.md"
        current = agents.read_text(encoding="utf-8")
        block = _agent_block(current)
        assert block is not None
        if agents_mode == "created":
            agents.unlink()
        else:
            start = current.index(block)
            end = start + len(block)
            remainder = (current[:start].rstrip() + current[end:]).rstrip()
            agents.write_text(remainder + ("\n" if remainder else ""), encoding="utf-8")

    manifest_path = repo / MANIFEST_RELATIVE
    manifest_path.unlink()
    for path in sorted(
        directories,
        key=lambda value: len(value.relative_to(repo).parts),
        reverse=True,
    ):
        relative = _relative(path, repo)
        if path.is_dir():
            try:
                path.rmdir()
                print(f"  removed empty directory: {relative}/")
            except OSError:
                print(f"  kept non-empty directory: {relative}/")
    print("Safe rollback completed.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument(
        "--update-agents",
        action="store_true",
        help="append the marked governance block when absent",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show the exact installation or removal plan without writing",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="remove only unchanged additions recorded by the install manifest",
    )
    args = parser.parse_args(argv)
    if args.uninstall and args.update_agents:
        parser.error("--update-agents cannot be combined with --uninstall")
    try:
        if args.uninstall:
            uninstall(args.repository, dry_run=args.dry_run)
        else:
            install(
                args.repository,
                args.update_agents,
                dry_run=args.dry_run,
            )
        return 0
    except (InstallError, OSError) as exc:
        print(f"Operation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

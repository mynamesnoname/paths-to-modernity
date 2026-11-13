#!/usr/bin/env python3
"""Migrate a v3 Plan Graph installation to v4 in place.

v4 moved the plan tree from `<repository>/_plan/` to
`<repository>/_aiHumanInteract/plan/`. The installer rejects a v3 tree instead
of migrating it, so this tool performs the migration as one reversible step:

1. verify the v3 installation (manifest, schema, installer-owned file hashes)
2. copy the tree to a temporary backup
3. move `_plan/` to `_aiHumanInteract/plan/`
4. rewrite repository-relative `_plan/` references in Markdown sources
5. replace the marked governance block in AGENTS.md, when present and
   verifiably unmodified
6. reinstall the v4 tools, validate the sources, rebuild the views

Any failure restores the backup and AGENTS.md, and leaves no second tree.
Use `--dry-run` to print the plan without touching the repository. A block the
v3 manifest cannot vouch for is never replaced unless you pass
`--replace-governance-block` after moving any local rules out of it.
"""

from __future__ import annotations

import argparse
import difflib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import install_plan_graph as installer  # noqa: E402

V3_SCHEMA = "paths-to-modernity-plan-graph-v3"
V3_PLAN_RELATIVE = Path("_plan")
TOOL_FILES = installer.PLAN_FILES
# A real v3 installation predates plan_view.py; only these were recorded.
V3_TOOL_FILES = ("README.md", "validate.py", "build_graph.py", "test_plan_graph.py")


class MigrationError(Exception):
    """A migration precondition failed or a step could not complete."""


def _sha256(path: Path) -> str:
    return installer._sha256_file(path)


def _plan_of(repo: Path) -> tuple[Path, Path]:
    legacy = repo / V3_PLAN_RELATIVE
    if not legacy.exists():
        raise MigrationError(f"no v3 plan tree at {legacy}")
    if not legacy.is_dir():
        raise MigrationError(f"{legacy} is not a directory; expected a v3 plan tree")
    current = repo / installer.PLAN_RELATIVE
    if current.exists():
        raise MigrationError(
            f"target already exists: {current}. Two plan trees cannot coexist; "
            "remove or reconcile the existing v4 tree first."
        )
    return legacy, current


def _load_v3_manifest(legacy: Path) -> dict:
    path = legacy / "install-manifest.json"
    if not path.is_file():
        raise MigrationError(
            f"no install manifest at {path}; this does not look like an "
            "installer-created v3 installation"
        )
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise MigrationError(f"cannot read {path}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise MigrationError("install manifest must contain a JSON object")
    if manifest.get("manifest_version") != installer.MANIFEST_VERSION:
        raise MigrationError(
            f"unsupported manifest version {manifest.get('manifest_version')!r}"
        )
    if manifest.get("schema_version") != V3_SCHEMA:
        raise MigrationError(
            f"expected schema {V3_SCHEMA}, found {manifest.get('schema_version')!r}"
        )
    for field in ("created_files", "managed_files"):
        entry = manifest.get(field)
        if not isinstance(entry, dict) or not entry:
            raise MigrationError(f"manifest {field} must be a non-empty object")
        for key in entry:
            if not key.startswith("_plan/"):
                raise MigrationError(f"manifest {field} entry is not a v3 path: {key!r}")
    return manifest


def _check_tools(legacy: Path, manifest: dict) -> None:
    """Installer-owned tools are replaced; user edits there must be resolved first."""
    managed = manifest["managed_files"]
    for name in V3_TOOL_FILES:
        path = legacy / name
        if not path.is_file():
            raise MigrationError(f"missing installed tool: {path}")
        recorded = managed.get(f"_plan/{name}")
        if recorded is None:
            raise MigrationError(
                f"manifest does not record {name}; this installation is not "
                "the one the manifest describes"
            )
        if _sha256(path) != recorded:
            raise MigrationError(
                f"{path} was modified after installation. The migration replaces "
                "installed tools, so move your changes aside and reinstall them "
                "as a local extension before migrating."
            )


def _rewrite(text: str) -> str:
    return text.replace("_plan/", "_aiHumanInteract/plan/").replace(
        "`_plan`", "`_aiHumanInteract/plan`"
    )


def _plan_rewrites(current_after_move: Path) -> list[tuple[Path, int]]:
    """Markdown sources under the plan tree that mention the old path."""
    planned: list[tuple[Path, int]] = []
    for path in sorted(current_after_move.rglob("*.md")):
        if "structure" in path.relative_to(current_after_move).parts:
            continue  # regenerated views
        text = path.read_text(encoding="utf-8")
        count = text.count("_plan/") + text.count("`_plan`")
        if count:
            planned.append((path, count))
    return planned


def _has_block(repo: Path) -> bool:
    path = repo / "AGENTS.md"
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    if text.count(installer.START_MARKER) > 1:
        raise MigrationError(
            "AGENTS.md contains more than one plan-graph block; "
            "keep one and rerun"
        )
    return installer.START_MARKER in text


def _block_diff(old: str, new: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            old.splitlines(),
            new.splitlines(),
            fromfile="governance block (installed)",
            tofile="governance block (v4)",
            lineterm="",
        )
    )


def _governance_replacement(
    repo: Path, manifest: dict, *, replace_unverified: bool
) -> str:
    """Return AGENTS.md text with the v4 governance block in place.

    Content equality is not ownership. The v3 manifest recorded the hash of the
    block it installed, so a mismatch means the block carries local rules that
    replacing it would drop. Refuse unless the user explicitly asks to replace.
    """
    path = repo / "AGENTS.md"
    text = path.read_text(encoding="utf-8")
    start = text.index(installer.START_MARKER)
    end = text.index(installer.END_MARKER, start) + len(installer.END_MARKER)
    installed = text[start:end]
    fragment = installer._fragment()

    if not replace_unverified:
        agents_record = manifest.get("agents")
        recorded = (
            agents_record.get("block_sha256")
            if isinstance(agents_record, dict)
            else None
        )
        if recorded is None:
            raise MigrationError(
                "AGENTS.md carries a plan-graph block, but the v3 manifest "
                "recorded no hash for it, so local edits cannot be ruled out. "
                "Review the block and rerun with --replace-governance-block if "
                "it holds nothing you need to keep."
            )
        if installer._sha256_bytes(installed.encode("utf-8")) != recorded:
            print(_block_diff(installed, fragment))
            raise MigrationError(
                "AGENTS.md governance block was edited after installation; the "
                "migration replaces the whole block and would drop those edits. "
                "Move them outside the markers, then rerun with "
                "--replace-governance-block."
            )
    return text[:start] + fragment + text[end:]


def _run(python: str, script: Path, repo: Path) -> None:
    completed = subprocess.run(
        (python, "-B", str(script)), cwd=repo, capture_output=True, text=True
    )
    if completed.returncode != 0:
        raise MigrationError(
            f"{script.name} failed:\n{completed.stdout}{completed.stderr}".strip()
        )


def _describe(repo: Path, legacy: Path) -> tuple[list[tuple[Path, int]], bool, bool]:
    current = repo / installer.PLAN_RELATIVE
    rewrites = _plan_rewrites(legacy)
    has_block = _has_block(repo)
    has_views = (legacy / "structure").is_dir()
    return rewrites, has_block, has_views


def migrate(
    repo: Path, *, dry_run: bool = False, replace_governance_block: bool = False
) -> None:
    repo = repo.resolve()
    if not repo.is_dir():
        raise MigrationError(f"repository directory does not exist: {repo}")

    legacy, current = _plan_of(repo)
    manifest = _load_v3_manifest(legacy)
    _check_tools(legacy, manifest)

    rewrites, has_block, has_views = _describe(repo, legacy)
    python = sys.executable

    print(f"Plan Graph v3 -> v4 migration in {repo}")
    print(f"  move: {legacy} -> {current}")
    print(f"  files recorded in the v3 manifest: {len(manifest['created_files'])}")
    print(f"  Markdown sources to rewrite: {len(rewrites)}")
    for path, count in rewrites:
        print(f"    {path.relative_to(repo)} ({count} reference(s))")
    print(f"  AGENTS.md governance block: {'replace' if has_block else 'absent'}")
    print(f"  generated views: {'rebuild' if has_views else 'none installed'}")

    replacement = None
    if has_block:
        replacement = _governance_replacement(
            repo, manifest, replace_unverified=replace_governance_block
        )

    if dry_run:
        print("Dry run only; no files were changed.")
        return

    agents_path = repo / "AGENTS.md"
    saved_agents = agents_path.read_bytes() if agents_path.is_file() else None
    with tempfile.TemporaryDirectory(prefix="paths-modernity-v3-backup-") as raw:
        backup = Path(raw) / "plan"
        shutil.copytree(legacy, backup)
        try:
            current.parent.mkdir(parents=True, exist_ok=True)
            legacy.rename(current)

            for path, _ in rewrites:
                moved = current / path.relative_to(legacy)
                moved.write_text(_rewrite(moved.read_text(encoding="utf-8")), encoding="utf-8")

            if replacement is not None:
                agents_path.write_text(replacement, encoding="utf-8")

            for name in TOOL_FILES:
                (current / name).unlink(missing_ok=True)
            # The v3 manifest records v3 ownership and would block a fresh install.
            (current / "install-manifest.json").unlink(missing_ok=True)

            installer.install(repo, update_agents=False)

            if has_block:
                manifest_path = current / "install-manifest.json"
                fresh = json.loads(manifest_path.read_text(encoding="utf-8"))
                fresh["agents"] = {
                    "mode": "appended",
                    "block_sha256": installer._sha256_bytes(
                        installer._fragment().encode("utf-8")
                    ),
                }
                manifest_path.write_text(
                    json.dumps(fresh, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )

            _run(python, current / "validate.py", repo)
            if has_views:
                _run(python, current / "build_graph.py", repo)
        except Exception as exc:
            shutil.rmtree(current, ignore_errors=True)
            shutil.copytree(backup, legacy)
            if saved_agents is not None:
                agents_path.write_bytes(saved_agents)
            raise MigrationError(
                f"migration failed and was rolled back to the v3 tree: {exc}"
            ) from exc

    print("Migrated to Plan Graph v4.")
    print("  next: review the diff, then commit sources and generated views together")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--replace-governance-block",
        action="store_true",
        help="replace a governance block even when local edits cannot be ruled out",
    )
    args = parser.parse_args(argv)
    try:
        migrate(
            args.repository,
            dry_run=args.dry_run,
            replace_governance_block=args.replace_governance_block,
        )
    except MigrationError as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        return 1
    except installer.InstallError as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

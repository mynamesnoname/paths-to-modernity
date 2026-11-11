#!/usr/bin/env python3
"""Regression-check the v4 schema, worked fixture, installer, and removal."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence


SKILL_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_ROOT = SKILL_ROOT / "assets" / "plan-graph"
EXAMPLE_ROOT = BUNDLE_ROOT / "example"
TOOL_NAMES = ("validate.py", "build_graph.py", "test_plan_graph.py")
SCHEMA_VERSION = "paths-to-modernity-plan-graph-v4"


def require_consistent_schema_version() -> None:
    versioned_files = (
        SKILL_ROOT / "references" / "plan-graph.md",
        BUNDLE_ROOT / "AGENTS.plan-management.md",
        BUNDLE_ROOT / "_aiHumanInteract/plan" / "README.md",
        BUNDLE_ROOT / "_aiHumanInteract/plan" / "build_graph.py",
        SKILL_ROOT / "scripts" / "install_plan_graph.py",
    )
    missing = [
        path.relative_to(SKILL_ROOT).as_posix()
        for path in versioned_files
        if SCHEMA_VERSION not in path.read_text(encoding="utf-8")
    ]
    if missing:
        raise RuntimeError(
            "schema version is missing or inconsistent in: " + ", ".join(missing)
        )


def run(command: Sequence[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def run_expect_failure(command: Sequence[str], cwd: Path) -> None:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode == 0:
        raise RuntimeError("command unexpectedly succeeded: " + " ".join(command))


def exercise_installer(root: Path) -> None:
    repository = root / "install-target"
    repository.mkdir()
    installer = SKILL_ROOT / "scripts" / "install_plan_graph.py"
    command = (sys.executable, str(installer), str(repository), "--update-agents")

    run((*command, "--dry-run"), SKILL_ROOT)
    if (repository / "_aiHumanInteract/plan").exists() or (repository / "AGENTS.md").exists():
        raise RuntimeError("installer dry run changed the target repository")

    run(command, SKILL_ROOT)
    manifest = repository / "_aiHumanInteract/plan" / "install-manifest.json"
    if not manifest.is_file():
        raise RuntimeError("installer did not create its ownership manifest")
    original_manifest = manifest.read_bytes()
    run(command, SKILL_ROOT)
    if manifest.read_bytes() != original_manifest:
        raise RuntimeError("reinstallation changed ownership of existing additions")

    remove = (
        sys.executable,
        str(installer),
        str(repository),
        "--uninstall",
    )
    run((*remove, "--dry-run"), SKILL_ROOT)
    if not manifest.exists():
        raise RuntimeError("rollback dry run changed the target repository")
    run(remove, SKILL_ROOT)
    if manifest.exists() or (repository / "AGENTS.md").exists():
        raise RuntimeError("safe rollback left owned files behind")

    appended = root / "install-with-existing-agents"
    appended.mkdir()
    original_agents = "# Local instructions\n\nKeep this project rule.\n"
    (appended / "AGENTS.md").write_text(original_agents, encoding="utf-8")
    appended_command = (
        sys.executable,
        str(installer),
        str(appended),
        "--update-agents",
    )
    run(appended_command, SKILL_ROOT)
    run(
        (sys.executable, str(installer), str(appended), "--uninstall"),
        SKILL_ROOT,
    )
    if (appended / "AGENTS.md").read_text(encoding="utf-8") != original_agents:
        raise RuntimeError("rollback did not preserve pre-existing AGENTS.md content")

    changed = root / "install-with-local-change"
    changed.mkdir()
    changed_command = (sys.executable, str(installer), str(changed))
    run(changed_command, SKILL_ROOT)
    readme = changed / "_aiHumanInteract/plan" / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "Local edit.\n")
    run_expect_failure(
        (sys.executable, str(installer), str(changed), "--uninstall"),
        SKILL_ROOT,
    )
    if not readme.exists() or not (changed / "_aiHumanInteract/plan/install-manifest.json").exists():
        raise RuntimeError("rollback removed content after detecting a local change")

    legacy = root / "legacy-installation"
    (legacy / "_aiHumanInteract/plan").mkdir(parents=True)
    old_manifest = legacy / "_aiHumanInteract/plan/install-manifest.json"
    old_manifest.write_text(json.dumps({
        "manifest_version": 1,
        "profile_version": "paths-to-modernity-mounted-plan-graph-v2",
    }), encoding="utf-8")
    before = old_manifest.read_bytes()
    for flags in (("--dry-run",), (), ("--uninstall", "--dry-run")):
        run_expect_failure(
            (sys.executable, str(installer), str(legacy), *flags),
            SKILL_ROOT,
        )
    if old_manifest.read_bytes() != before or set((legacy / "_aiHumanInteract/plan").iterdir()) != {old_manifest}:
        raise RuntimeError("v4 installer mutated an unsupported legacy installation")

    unmigrated = root / "unmigrated-v3"
    (unmigrated / "_plan").mkdir(parents=True)
    for flags in (("--dry-run",), (), ("--uninstall", "--dry-run")):
        run_expect_failure(
            (sys.executable, str(installer), str(unmigrated), *flags),
            SKILL_ROOT,
        )
    if (unmigrated / "_aiHumanInteract").exists():
        raise RuntimeError("v4 installer built beside an unmigrated v3 tree")


def main() -> int:
    require_consistent_schema_version()
    with tempfile.TemporaryDirectory(prefix="paths-modernity-example-") as raw:
        root = Path(raw)
        exercise_installer(root)
        repository = root / "example"
        shutil.copytree(EXAMPLE_ROOT, repository)
        for name in TOOL_NAMES:
            shutil.copy2(BUNDLE_ROOT / "_aiHumanInteract/plan" / name, repository / "_aiHumanInteract/plan" / name)

        python = sys.executable
        plan_dir = repository / "_aiHumanInteract/plan"
        run((python, "-B", "_aiHumanInteract/plan/validate.py"), repository)
        run((python, "-B", "_aiHumanInteract/plan/build_graph.py", "--check"), repository)
        run(
            (
                python,
                "-B",
                "-m",
                "unittest",
                "discover",
                "-p",
                "test_*.py",
                "-v",
            ),
            plan_dir,
        )
    print("Plan Graph v4 bundle checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

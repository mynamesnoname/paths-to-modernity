#!/usr/bin/env python3
"""Regression-check the v4 schema, worked fixture, installer, and removal."""

from __future__ import annotations

import hashlib
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
TOOL_NAMES = ("validate.py", "build_graph.py", "plan_view.py", "test_plan_graph.py")
INSTALLER = SKILL_ROOT / "scripts" / "install_plan_graph.py"
MIGRATOR = SKILL_ROOT / "scripts" / "migrate_plan_graph_v3.py"
ADOPTER = SKILL_ROOT / "scripts" / "adopt_project.py"
PROTOCOL_BLOCK = SKILL_ROOT / "assets" / "protocol" / "AGENTS.protocol.md"
V3_SCHEMA = "paths-to-modernity-plan-graph-v3"
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


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _to_v3(text: str) -> str:
    return text.replace("_aiHumanInteract/plan/", "_plan/").replace(
        SCHEMA_VERSION, V3_SCHEMA
    )


def build_v3_installation(repo: Path) -> None:
    """Fabricate a plausible v3 install: v3 paths, schema, tools, and governance."""
    run((sys.executable, str(INSTALLER), str(repo), "--update-agents"), SKILL_ROOT)
    plan = repo / "_aiHumanInteract" / "plan"
    shutil.copytree(EXAMPLE_ROOT / "_aiHumanInteract" / "plan", plan, dirs_exist_ok=True)
    legacy = repo / "_plan"
    plan.rename(legacy)
    for file in legacy.rglob("*.md"):
        file.write_text(_to_v3(file.read_text(encoding="utf-8")), encoding="utf-8")
    for file in legacy.glob("*.py"):
        file.write_text(_to_v3(file.read_text(encoding="utf-8")), encoding="utf-8")
    manifest_path = legacy / "install-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = V3_SCHEMA
    for key in ("created_files", "managed_files"):
        manifest[key] = {
            name.replace("_aiHumanInteract/plan/", "_plan/"): digest
            for name, digest in manifest[key].items()
        }
    manifest["created_dirs"] = [
        name.replace("_aiHumanInteract/plan", "_plan")
        for name in manifest.get("created_dirs", [])
    ]
    manifest["managed_files"] = {
        name: _sha256_file(legacy / name[len("_plan/"):])
        for name in manifest["managed_files"]
    }
    agents = repo / "AGENTS.md"
    agents_text = _to_v3(agents.read_text(encoding="utf-8"))
    agents.write_text(agents_text, encoding="utf-8")
    # A real v3 installer recorded the hash of the block it wrote. Recompute it
    # after rewriting the block to v3, or the fixture would describe a block the
    # installer never produced and the migration would rightly distrust it.
    start = agents_text.index("<!-- paths-to-modernity:plan-graph:start -->")
    end = agents_text.index("<!-- paths-to-modernity:plan-graph:end -->", start) + len(
        "<!-- paths-to-modernity:plan-graph:end -->"
    )
    manifest["agents"] = {
        "mode": "appended",
        "block_sha256": hashlib.sha256(
            agents_text[start:end].encode("utf-8")
        ).hexdigest(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def exercise_migration(root: Path) -> None:
    """v3 -> v4 must succeed on a real install, and roll back on failure."""
    repo = root / "migration-target"
    repo.mkdir()
    build_v3_installation(repo)
    node = repo / "_plan" / "work-package" / "WP-001.md"
    node.write_text(
        node.read_text(encoding="utf-8").replace(
            "quietly legible under operational pressure", "legible in a hurry"
        ),
        encoding="utf-8",
    )

    run((sys.executable, str(MIGRATOR), str(repo), "--dry-run"), SKILL_ROOT)
    if not (repo / "_plan").is_dir():
        raise RuntimeError("migration dry run moved the v3 tree")

    run((sys.executable, str(MIGRATOR), str(repo)), SKILL_ROOT)
    if (repo / "_plan").exists():
        raise RuntimeError("migration left the v3 tree in place")
    migrated = repo / "_aiHumanInteract" / "plan"
    text = (migrated / "work-package" / "WP-001.md").read_text(encoding="utf-8")
    if "legible in a hurry" not in text:
        raise RuntimeError("migration lost a user edit")
    if "_plan/" in text:
        raise RuntimeError("migration left a v3 path in a source node")
    manifest = json.loads((migrated / "install-manifest.json").read_text(encoding="utf-8"))
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise RuntimeError("migration did not record the v4 manifest")
    run((sys.executable, "-B", "_aiHumanInteract/plan/validate.py"), repo)

    broken = root / "migration-rollback"
    broken.mkdir()
    build_v3_installation(broken)
    bad = broken / "_plan" / "work-package" / "WP-001.md"
    bad.write_text(
        bad.read_text(encoding="utf-8").replace('status: "ready"', 'status: "nonsense"'),
        encoding="utf-8",
    )
    run_expect_failure((sys.executable, str(MIGRATOR), str(broken)), SKILL_ROOT)
    if not (broken / "_plan").is_dir():
        raise RuntimeError("failed migration did not restore the v3 tree")
    if (broken / "_aiHumanInteract" / "plan").exists():
        raise RuntimeError("failed migration left a second plan tree")
    if not (broken / "AGENTS.md").exists():
        raise RuntimeError("failed migration left AGENTS.md missing")

    edited = root / "migration-edited-tool"
    edited.mkdir()
    build_v3_installation(edited)
    tool = edited / "_plan" / "validate.py"
    tool.write_text(tool.read_text(encoding="utf-8") + "# local rule\n", encoding="utf-8")
    run_expect_failure((sys.executable, str(MIGRATOR), str(edited)), SKILL_ROOT)
    if "# local rule" not in tool.read_text(encoding="utf-8"):
        raise RuntimeError("migration discarded a user-modified tool file")
    if (edited / "_aiHumanInteract" / "plan").exists():
        raise RuntimeError("refused migration still moved the tree")

    governance = root / "migration-edited-governance"
    governance.mkdir()
    build_v3_installation(governance)
    agents = governance / "AGENTS.md"
    end_marker = "<!-- paths-to-modernity:plan-graph:end -->"
    rule = "Local rule: keep billing changes reviewed."
    agents.write_text(
        agents.read_text(encoding="utf-8").replace(
            end_marker, f"\n{rule}\n{end_marker}"
        ),
        encoding="utf-8",
    )
    before = agents.read_text(encoding="utf-8")
    run_expect_failure((sys.executable, str(MIGRATOR), str(governance)), SKILL_ROOT)
    if agents.read_text(encoding="utf-8") != before:
        raise RuntimeError("refused migration changed the governance block")
    if not (governance / "_plan").is_dir():
        raise RuntimeError("refused migration moved the v3 tree")

    run(
        (sys.executable, str(MIGRATOR), str(governance), "--replace-governance-block"),
        SKILL_ROOT,
    )
    replaced = agents.read_text(encoding="utf-8")
    if rule in replaced:
        raise RuntimeError("explicit replacement kept the governed block unchanged")
    if "_aiHumanInteract/plan/" not in replaced:
        raise RuntimeError("migration did not install the v4 governance block")

    unrecorded = root / "migration-unrecorded-block"
    unrecorded.mkdir()
    build_v3_installation(unrecorded)
    manifest_path = unrecorded / "_plan" / "install-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["agents"] = {"mode": "unchanged"}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    run_expect_failure((sys.executable, str(MIGRATOR), str(unrecorded)), SKILL_ROOT)
    if not (unrecorded / "_plan").is_dir():
        raise RuntimeError("unrecorded governance block was replaced anyway")



def exercise_adoption(root: Path) -> None:
    """Protocol adoption must be idempotent, non-destructive, and reversible."""
    repo = root / "adoption"
    repo.mkdir()
    run((sys.executable, str(ADOPTER), str(repo), "--dry-run"), SKILL_ROOT)
    if (repo / "AGENTS.md").exists():
        raise RuntimeError("adoption dry run wrote AGENTS.md")

    run((sys.executable, str(ADOPTER), str(repo)), SKILL_ROOT)
    agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
    if "paths-to-modernity:protocol:start" not in agents:
        raise RuntimeError("adoption did not write the protocol block")
    if not (repo / "CLAUDE.md").is_file():
        raise RuntimeError("adoption did not write the CLAUDE.md pointer")
    state = repo / "_aiHumanInteract" / "state" / "active.md"
    if not state.is_file():
        raise RuntimeError("adoption did not create the state skeleton")

    before = agents
    run((sys.executable, str(ADOPTER), str(repo)), SKILL_ROOT)
    if (repo / "AGENTS.md").read_text(encoding="utf-8") != before:
        raise RuntimeError("adoption is not idempotent")

    state.write_text(state.read_text(encoding="utf-8") + "- local progress\n", encoding="utf-8")
    run((sys.executable, str(ADOPTER), str(repo), "--uninstall"), SKILL_ROOT)
    if (repo / "AGENTS.md").exists():
        raise RuntimeError("uninstall left an AGENTS.md it had created")
    if (repo / "CLAUDE.md").exists():
        raise RuntimeError("uninstall left CLAUDE.md")
    if not state.is_file() or "local progress" not in state.read_text(encoding="utf-8"):
        raise RuntimeError("uninstall discarded an edited state file")

    clash = root / "adoption-clash"
    clash.mkdir()
    (clash / "CLAUDE.md").write_text("project-owned\n", encoding="utf-8")
    run_expect_failure((sys.executable, str(ADOPTER), str(clash)), SKILL_ROOT)
    if (clash / "CLAUDE.md").read_text(encoding="utf-8") != "project-owned\n":
        raise RuntimeError("adoption overwrote an existing CLAUDE.md")

    block = PROTOCOL_BLOCK.read_text(encoding="utf-8").rstrip("\n")
    pointer = (
        "This repository is governed by `AGENTS.md`. Read it before acting; it "
        "takes precedence over tool defaults.\n"
    )
    preexisting = root / "adoption-preexisting"
    preexisting.mkdir()
    (preexisting / "AGENTS.md").write_text(
        "Project rules that predate adoption.\n\n" + block + "\n", encoding="utf-8"
    )
    (preexisting / "CLAUDE.md").write_text(pointer, encoding="utf-8")
    run((sys.executable, str(ADOPTER), str(preexisting)), SKILL_ROOT)
    run((sys.executable, str(ADOPTER), str(preexisting), "--uninstall"), SKILL_ROOT)
    kept = (
        (preexisting / "AGENTS.md").read_text(encoding="utf-8")
        if (preexisting / "AGENTS.md").is_file()
        else ""
    )
    if "Project rules that predate adoption." not in kept or block not in kept:
        raise RuntimeError("uninstall removed a block the project already had")
    if not (preexisting / "CLAUDE.md").is_file():
        raise RuntimeError("uninstall removed a pre-existing CLAUDE.md")

    legacy = root / "adoption-legacy-manifest"
    legacy.mkdir()
    run((sys.executable, str(ADOPTER), str(legacy)), SKILL_ROOT)
    legacy_manifest = legacy / "_aiHumanInteract" / "adopt-manifest.json"
    manifest = json.loads(legacy_manifest.read_text(encoding="utf-8"))
    del manifest["created_block"]
    legacy_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    run((sys.executable, str(ADOPTER), str(legacy), "--uninstall"), SKILL_ROOT)
    if not (legacy / "AGENTS.md").is_file():
        raise RuntimeError("uninstall removed a block without an ownership record")
    if block not in (legacy / "AGENTS.md").read_text(encoding="utf-8"):
        raise RuntimeError("uninstall removed a block without an ownership record")


def exercise_block_upgrade(root: Path) -> None:
    """An unmodified block upgrades after review; an edited one never does."""
    repo = root / "adoption-upgrade"
    repo.mkdir()
    run((sys.executable, str(ADOPTER), str(repo)), SKILL_ROOT)
    original = PROTOCOL_BLOCK.read_text(encoding="utf-8")
    try:
        PROTOCOL_BLOCK.write_text(
            original.replace("paths-to-modernity-protocol-v2", "paths-to-modernity-protocol-v3")
            .replace(
                "are outputs. Never edit them as the authority.",
                "are outputs. Never edit them as the authority. Regenerate them.",
            ),
            encoding="utf-8",
        )
        run_expect_failure((sys.executable, str(ADOPTER), str(repo)), SKILL_ROOT)

        before = (repo / "AGENTS.md").read_text(encoding="utf-8")
        run((sys.executable, str(ADOPTER), str(repo), "--upgrade-block", "--dry-run"), SKILL_ROOT)
        if (repo / "AGENTS.md").read_text(encoding="utf-8") != before:
            raise RuntimeError("upgrade dry run wrote AGENTS.md")

        run((sys.executable, str(ADOPTER), str(repo), "--upgrade-block"), SKILL_ROOT)
        upgraded = (repo / "AGENTS.md").read_text(encoding="utf-8")
        if "Regenerate them." not in upgraded:
            raise RuntimeError("upgrade did not apply the new block")
        manifest = json.loads(
            (repo / "_aiHumanInteract" / "adopt-manifest.json").read_text(encoding="utf-8")
        )
        if manifest["protocol_version"] != "paths-to-modernity-protocol-v3":
            raise RuntimeError("upgrade did not record the new protocol version")

        edited = root / "adoption-upgrade-edited"
        edited.mkdir()
        run((sys.executable, str(ADOPTER), str(edited)), SKILL_ROOT)
        agents = edited / "AGENTS.md"
        agents.write_text(
            agents.read_text(encoding="utf-8").replace(
                "Readiness is relative to the next commitment.",
                "Readiness is whatever feels right.",
            ),
            encoding="utf-8",
        )
        before_edit = agents.read_text(encoding="utf-8")
        run_expect_failure(
            (sys.executable, str(ADOPTER), str(edited), "--upgrade-block"), SKILL_ROOT
        )
        if agents.read_text(encoding="utf-8") != before_edit:
            raise RuntimeError("upgrade overwrote a hand-edited block")
    finally:
        PROTOCOL_BLOCK.write_text(original, encoding="utf-8")


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
        page = (repository / "_aiHumanInteract/plan/structure/graph.html").read_text(
            encoding="utf-8"
        )
        if "LT-001" not in page or "WP-001" not in page or 'id="search-surface"' not in page or 'RELATIONS' not in page or 'id="card-mark-layer"' not in page:
            raise RuntimeError("graph.html does not embed the plan nodes and search")
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
        exercise_migration(root)
        exercise_adoption(root)
        exercise_block_upgrade(root)
    print("Plan Graph v4 bundle checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Publish skills from this repository to an OCI registry via skillctl.

Walks every directory under skills/ that contains a SKILL.md, generates
a skill.yaml SkillCard if one doesn't exist, then packs and pushes
each skill to the configured OCI registry.

Usage:
    python scripts/publish_skills.py . --registry quay.io/rbrhssa/skills
    python scripts/publish_skills.py . --registry quay.io/rbrhssa/skills --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
log = logging.getLogger(__name__)

SKILLCARD_API_VERSION = "skillimage.io/v1alpha1"
SKILLCARD_KIND = "SkillCard"
DEFAULT_VERSION = "1.0.0"


def parse_frontmatter(content: str) -> dict[str, Any] | None:
    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return None
    try:
        fm = yaml.safe_load(m.group(1))
        return fm if isinstance(fm, dict) else None
    except yaml.YAMLError:
        return None


def normalize_semver(version: Any) -> str:
    v = str(version).strip().lstrip("v")
    parts = v.split(".")
    if len(parts) == 1:
        return f"{parts[0]}.0.0"
    if len(parts) == 2:
        return f"{parts[0]}.{parts[1]}.0"
    return v


def derive_namespace(skill_dir: Path, repo_root: Path, fm: dict[str, Any] | None = None) -> str:
    """Derive namespace from frontmatter domain field, falling back to directory.

    Priority: frontmatter 'domain' > directory name > 'default'
    """
    if fm and "domain" in fm:
        return str(fm["domain"])
    rel = skill_dir.relative_to(repo_root / "skills")
    parts = rel.parts
    if len(parts) >= 2:
        return parts[0]
    return "default"


def discover_skills(repo_root: Path) -> list[Path]:
    skills_dir = repo_root / "skills"
    if not skills_dir.is_dir():
        log.error("No skills/ directory found in %s", repo_root)
        return []
    result: list[Path] = []
    for root, _dirs, files in os.walk(skills_dir):
        if "SKILL.md" in files:
            result.append(Path(root))
    return sorted(result)


def ensure_skill_yaml(skill_dir: Path, repo_root: Path) -> dict[str, Any] | None:
    """Read or generate skill.yaml for a skill directory."""
    yaml_path = skill_dir / "skill.yaml"

    if yaml_path.exists():
        with open(yaml_path) as f:
            return yaml.safe_load(f)

    skill_md = skill_dir / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    fm = parse_frontmatter(content)
    if fm is None or "name" not in fm:
        return None

    meta = fm.get("metadata", {}) if isinstance(fm.get("metadata"), dict) else {}
    namespace = derive_namespace(skill_dir, repo_root, fm)
    name = fm["name"]
    version = normalize_semver(meta.get("version", DEFAULT_VERSION))
    description = fm.get("description", "").strip()
    if not description:
        return None

    skill_card: dict[str, Any] = {
        "apiVersion": SKILLCARD_API_VERSION,
        "kind": SKILLCARD_KIND,
        "metadata": {
            "name": name,
            "namespace": namespace,
            "version": version,
            "description": description,
        },
        "spec": {"prompt": "SKILL.md"},
    }

    license_val = fm.get("license")
    if license_val:
        skill_card["metadata"]["license"] = str(license_val)

    author = meta.get("author", meta.get("authors"))
    if author:
        if isinstance(author, list):
            skill_card["metadata"]["authors"] = author
        else:
            skill_card["metadata"]["authors"] = [{"name": str(author)}]

    tags = fm.get("tags", [])
    if tags:
        skill_card["metadata"]["tags"] = tags

    if fm.get("category"):
        skill_card["metadata"]["compatibility"] = fm["category"]

    if fm.get("tools"):
        skill_card["metadata"]["tools"] = fm["tools"]
    if fm.get("plugin"):
        skill_card["metadata"]["plugin"] = fm["plugin"]
    if fm.get("lang"):
        skill_card["metadata"]["lang"] = fm["lang"]

    with open(yaml_path, "w") as f:
        yaml.dump(skill_card, f, default_flow_style=False, sort_keys=False)
    log.info("  generated skill.yaml")

    return skill_card


def build_remote_ref(registry: str, name: str, version: str) -> str:
    parts = registry.rstrip("/").split("/")
    if len(parts) >= 3:
        return f"{registry}:{name}-{version}-draft"
    return f"{registry}/{name}:{version}-draft"


def pack_tag_push(
    skill_dir: Path,
    name: str,
    namespace: str,
    version: str,
    registry: str,
    tls_verify: bool,
) -> bool:
    local_ref = f"{namespace}/{name}:{version}-draft"
    remote_ref = build_remote_ref(registry, name, version)

    result = subprocess.run(
        ["skillctl", "pack", str(skill_dir)],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        log.error("  pack failed: %s", result.stderr.strip())
        return False
    log.info("  packed %s", local_ref)

    result = subprocess.run(
        ["skillctl", "tag", local_ref, remote_ref],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        log.error("  tag failed: %s", result.stderr.strip())
        return False

    cmd = ["skillctl", "push", remote_ref]
    if not tls_verify:
        cmd.append("--tls-verify=false")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        log.error("  push failed: %s", result.stderr.strip())
        return False
    log.info("  pushed %s", remote_ref)
    return True


def trigger_sync(catalog_url: str) -> None:
    try:
        url = f"{catalog_url.rstrip('/')}/api/v1/sync"
        req = urllib.request.Request(url, method="POST")
        ctx = __import__("ssl").create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = __import__("ssl").CERT_NONE
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        body = json.loads(resp.read().decode("utf-8"))
        log.info("Catalog sync triggered: %s", body)
    except Exception as e:
        log.warning("Could not trigger catalog sync: %s", e)


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish skills to OCI registry")
    parser.add_argument("repo_path", type=Path, help="Root of the skills repository")
    parser.add_argument("--registry", required=True, help="OCI registry (e.g. quay.io/rbrhssa/skills)")
    parser.add_argument("--catalog-url", default="", help="Catalog API URL for sync trigger")
    parser.add_argument("--no-tls-verify", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, no pack/push")
    parser.add_argument("--limit", type=int, default=0, help="Process only first N skills")

    args = parser.parse_args()
    repo_root = args.repo_path.resolve()

    skill_dirs = discover_skills(repo_root)
    log.info("Found %d skills", len(skill_dirs))

    if args.limit > 0:
        skill_dirs = skill_dirs[: args.limit]

    converted = 0
    pushed = 0
    errors: list[str] = []

    for skill_dir in skill_dirs:
        rel = skill_dir.relative_to(repo_root)
        log.info("Processing %s", rel)

        card = ensure_skill_yaml(skill_dir, repo_root)
        if card is None:
            errors.append(f"{rel}: no name or description in SKILL.md")
            continue

        name = card["metadata"]["name"]
        namespace = card["metadata"]["namespace"]
        version = card["metadata"]["version"]
        converted += 1

        if args.dry_run:
            log.info("  [dry-run] would push %s:%s-%s-draft", args.registry, name, version)
            continue

        if pack_tag_push(skill_dir, name, namespace, version, args.registry, not args.no_tls_verify):
            pushed += 1
        else:
            errors.append(f"{namespace}/{name}: push failed")

    log.info("")
    log.info("=== Summary ===")
    log.info("Skills found:  %d", len(skill_dirs))
    log.info("Converted:     %d", converted)
    log.info("Pushed:        %d", pushed)
    log.info("Errors:        %d", len(errors))

    if errors:
        for e in errors:
            log.error("  %s", e)

    if pushed > 0 and args.catalog_url:
        trigger_sync(args.catalog_url)

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()

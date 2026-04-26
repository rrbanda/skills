#!/usr/bin/env python3
"""One-time migration: reorganize skills from vendor-centric to domain-centric layout.

Reads each skill's SKILL.md, classifies it into a domain, enriches the
frontmatter with domain/category/tags/tools/plugin/lang fields, and moves
the skill directory to skills/<domain>/<name>/.

Usage:
    python scripts/reorganize.py              # dry-run (default)
    python scripts/reorganize.py --apply      # actually move files
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path
from typing import Any

import yaml

DOMAIN_RULES: list[tuple[list[str], str]] = [
    (["ai-agents", "ai-projects", "ai-openai", "openai", "speech", "vision",
      "imageanalysis", "document-intelligence", "ai-ml", "ai-inference",
      "ai-voicelive", "m365-agents", "copilot", "continual-learning",
      "anomalydetector", "contentsafety", "formrecognizer",
      "contentunderstanding", "language-conversations", "textanalytics",
      "transcription", "translation", "agent-framework", "agents-v2",
      "hosted-agents"], "ai-ml"),
    (["mgmt-", "resource-manager", "-aks-", "containerservice", "network",
      "compute", "appservice", "webpubsub", "signalr", "frontdoor", "cdn",
      "dns", "trafficmanager", "loadbalancer", "virtualnetwork",
      "containerapp", "appcontainers", "appplatform", "springcloud",
      "botservice", "cloud-solution-architect", "appconfiguration",
      "containerregistry", "web-pubsub"], "cloud-infra"),
    (["cosmos", "-sql-", "tables", "blob", "storage", "data-tables",
      "data-lake", "eventhub", "schemaregistry", "synapse", "datafactory",
      "monitor-query", "monitor-ingestion", "loganalytics",
      "postgres"], "data"),
    (["identity", "keyvault", "entra", "authentication-events",
      "attestation"], "identity"),
    (["servicebus", "eventgrid", "api-management", "apicenter",
      "apimanagement", "communication", "notification"], "integration"),
    (["security", "defender", "sentinel"], "security"),
    (["wiki", "docs", "changelog", "deep-wiki", "onboarding",
      "microsoft-docs", "llms-txt", "vitepress"], "documentation"),
    (["monitor", "insights", "container-registry", "applicationinsights",
      "webtest", "search-documents", "maps-search", "playwright", "kql",
      "github-issue", "mcp-builder"], "devops"),
    (["frontend", "react-flow", "zustand", "dark-ts", "fastapi", "pydantic",
      "ui-"], "development"),
]

LANG_SUFFIXES = {"-py": "python", "-dotnet": "dotnet", "-ts": "typescript",
                 "-java": "java", "-rust": "rust"}

NS_TO_PLUGIN = {
    "azure-sdk-python": "azure-sdk-python",
    "azure-sdk-dotnet": "azure-sdk-dotnet",
    "azure-sdk-java": "azure-sdk-java",
    "azure-sdk-typescript": "azure-sdk-typescript",
    "azure-sdk-rust": "azure-sdk-rust",
    "azure-skills": "azure-skills",
    "deep-wiki": "deep-wiki",
}


def classify_domain(name: str, old_ns: str) -> str:
    name_lower = name.lower()
    for patterns, domain in DOMAIN_RULES:
        for p in patterns:
            if p in name_lower:
                return domain
    if old_ns == "deep-wiki":
        return "documentation"
    if old_ns == "azure-skills":
        return "cloud-infra"
    return "general"


def derive_lang(name: str) -> str | None:
    for suffix, lang in LANG_SUFFIXES.items():
        if name.endswith(suffix):
            return lang
    return None


def derive_tags(name: str, domain: str, lang: str | None, old_ns: str) -> list[str]:
    tags: list[str] = []
    if lang:
        tags.append(lang)
    if "azure" in name.lower() or "azure" in old_ns.lower():
        tags.append("azure")
    if domain not in tags:
        tags.append(domain)
    return tags


def derive_category(name: str, domain: str) -> str:
    """Derive a finer-grained category within the domain."""
    name_lower = name.lower()
    if domain == "ai-ml":
        if "openai" in name_lower:
            return "llm-apis"
        if "vision" in name_lower or "imageanalysis" in name_lower:
            return "computer-vision"
        if "speech" in name_lower or "transcription" in name_lower:
            return "speech"
        if "translation" in name_lower:
            return "translation"
        if "agent" in name_lower:
            return "agents"
        return "ai-services"
    if domain == "cloud-infra":
        if "mgmt-" in name_lower:
            return "resource-management"
        if "aks" in name_lower or "container" in name_lower:
            return "containers"
        return "infrastructure"
    if domain == "data":
        if "cosmos" in name_lower:
            return "nosql"
        if "sql" in name_lower or "postgres" in name_lower:
            return "relational"
        if "eventhub" in name_lower:
            return "streaming"
        if "storage" in name_lower or "blob" in name_lower:
            return "object-storage"
        return "data-services"
    if domain == "identity":
        if "keyvault" in name_lower:
            return "secrets-management"
        return "authentication"
    if domain == "integration":
        if "servicebus" in name_lower:
            return "messaging"
        if "eventgrid" in name_lower:
            return "event-routing"
        return "api-management"
    return domain


def parse_frontmatter(content: str) -> tuple[dict[str, Any] | None, str]:
    """Return (frontmatter_dict, body_after_frontmatter)."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", content, re.DOTALL)
    if not m:
        return None, content
    try:
        fm = yaml.safe_load(m.group(1))
        return (fm if isinstance(fm, dict) else None), m.group(2)
    except yaml.YAMLError:
        return None, content


def rebuild_skill_md(fm: dict[str, Any], body: str) -> str:
    """Rebuild SKILL.md with enriched frontmatter."""
    fm_str = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return f"---\n{fm_str}---\n{body}"


def enrich_frontmatter(
    fm: dict[str, Any],
    domain: str,
    category: str,
    plugin: str | None,
    lang: str | None,
    tags: list[str],
) -> dict[str, Any]:
    """Add graph-aligned fields to frontmatter without overwriting existing ones."""
    if "domain" not in fm:
        fm["domain"] = domain
    if "category" not in fm:
        fm["category"] = category
    if "plugin" not in fm and plugin:
        fm["plugin"] = plugin
    if "lang" not in fm and lang:
        fm["lang"] = lang
    if "tags" not in fm and tags:
        fm["tags"] = tags
    return fm


def main() -> None:
    parser = argparse.ArgumentParser(description="Reorganize skills by domain")
    parser.add_argument("--apply", action="store_true", help="Actually move files (default is dry-run)")
    parser.add_argument("--repo", type=Path, default=Path("."), help="Repository root")
    args = parser.parse_args()

    repo_root = args.repo.resolve()
    skills_dir = repo_root / "skills"

    if not skills_dir.is_dir():
        print(f"ERROR: {skills_dir} not found")
        return

    moves: list[tuple[Path, Path, str]] = []

    for ns_dir in sorted(os.listdir(skills_dir)):
        ns_path = skills_dir / ns_dir
        if not ns_path.is_dir():
            continue
        for skill_name in sorted(os.listdir(ns_path)):
            skill_path = ns_path / skill_name
            skill_md = skill_path / "SKILL.md"
            if not skill_md.exists():
                continue

            content = skill_md.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(content)
            if fm is None or "name" not in fm:
                print(f"SKIP (no frontmatter): {ns_dir}/{skill_name}")
                continue

            domain = classify_domain(skill_name, ns_dir)
            category = derive_category(skill_name, domain)
            lang = derive_lang(skill_name)
            plugin = NS_TO_PLUGIN.get(ns_dir)
            tags = derive_tags(skill_name, domain, lang, ns_dir)

            fm = enrich_frontmatter(fm, domain, category, plugin, lang, tags)

            new_dir = skills_dir / domain / skill_name
            moves.append((skill_path, new_dir, domain))

            if args.apply:
                skill_md.write_text(rebuild_skill_md(fm, body), encoding="utf-8")

    print(f"\n{'APPLYING' if args.apply else 'DRY-RUN'}: {len(moves)} skills to reorganize\n")

    import collections
    counts = collections.Counter(d for _, _, d in moves)
    for d, c in sorted(counts.items()):
        print(f"  {d}: {c}")

    if not args.apply:
        print("\nRun with --apply to execute moves.")
        return

    for src, dst, domain in moves:
        if src == dst:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            shutil.rmtree(dst)
        shutil.move(str(src), str(dst))

    for ns_dir in os.listdir(skills_dir):
        ns_path = skills_dir / ns_dir
        if ns_path.is_dir() and not any(ns_path.iterdir()):
            ns_path.rmdir()
            print(f"  removed empty dir: {ns_dir}/")

    print(f"\nDone. {len(moves)} skills reorganized.")


if __name__ == "__main__":
    main()

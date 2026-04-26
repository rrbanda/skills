# Skills Repository

A collection of AI agent skills stored as OCI images. Skills are automatically
published to [quay.io/rbrhssa/skills](https://quay.io/repository/rbrhssa/skills)
on every push to `main`, and indexed by the Skill Catalog API.

## Repository Structure

```
skills/
  <namespace>/
    <skill-name>/
      SKILL.md            # Skill prompt (required)
      skill.yaml          # SkillCard metadata (auto-generated if missing)
      references/         # Supporting documents (optional)
```

## How It Works

```
git push → GitHub Actions → skillctl pack → skillctl push → Catalog API syncs
```

1. **Add a skill**: create `skills/<namespace>/<name>/SKILL.md`
2. **Push to main**: the CI pipeline automatically packs and pushes to the OCI registry
3. **Catalog indexes**: the Skill Catalog API discovers new tags and indexes them
4. **Any app queries**: `GET /api/v1/skills` returns all published skills

## Adding a New Skill

Create a `SKILL.md` with YAML frontmatter:

```markdown
---
name: my-new-skill
description: What this skill does in one sentence.
license: Apache-2.0
metadata:
  version: 1.0.0
  author: Your Name
---

# My New Skill

Instructions for the AI agent go here...
```

Place it under `skills/<namespace>/<skill-name>/SKILL.md` and push.

## Manual Publish

```bash
# Dry run (validate only)
python scripts/publish_skills.py . --registry quay.io/rbrhssa/skills --dry-run

# Publish all
python scripts/publish_skills.py . --registry quay.io/rbrhssa/skills

# Publish first 5 only
python scripts/publish_skills.py . --registry quay.io/rbrhssa/skills --limit 5
```

## Catalog API

Once skills are published, query them at:

```bash
# List all skills
curl https://skillctl-catalog-skill-catalog.apps.ocp.v7hjl.sandbox2288.opentlc.com/api/v1/skills

# Search by keyword
curl ".../api/v1/skills?q=docker"

# Get skill detail
curl ".../api/v1/skills/rbrhssa/skills/hello-world-1.0.0-draft"

# Get skill content (SKILL.md)
curl ".../api/v1/skills/rbrhssa/skills/hello-world-1.0.0-draft/content"
```

## Required Secrets

The GitHub Actions workflow requires these repository secrets:

| Secret | Description |
|--------|-------------|
| `QUAY_USERNAME` | Quay.io username (e.g. `rbrhssa`) |
| `QUAY_PASSWORD` | Quay.io password or robot token |

## Namespaces

| Namespace | Description |
|-----------|-------------|
| `core` | General-purpose skills |
| `examples` | Example/template skills |
| `azure-sdk-python` | Azure SDK for Python |
| `azure-sdk-dotnet` | Azure SDK for .NET |
| `azure-sdk-java` | Azure SDK for Java |
| `azure-sdk-typescript` | Azure SDK for TypeScript |
| `azure-sdk-rust` | Azure SDK for Rust |
| `azure-skills` | Azure infrastructure skills |
| `deep-wiki` | Documentation generation |

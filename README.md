# Skills Repository

A collection of AI agent skills organized by functional domain, stored as OCI
images, and automatically published to
[quay.io/rbrhssa/skills](https://quay.io/repository/rbrhssa/skills).

Skills are indexed by the Skill Catalog API and synced into a Neo4j graph
database where they become `(:Skill)` nodes connected to `(:Domain)`, `(:Tag)`,
and `(:Tool)` nodes via typed relationships.

## Repository Structure

```
skills/
  <domain>/                     # Functional domain (= Neo4j Domain node)
    <skill-name>/
      SKILL.md                  # Skill prompt + enriched frontmatter (required)
      references/               # Supporting documents (optional)
```

### Domain Taxonomy

The top-level directories map directly to `(:Domain)` nodes in the graph:

| Domain | Description | Example Skills |
|--------|-------------|----------------|
| `ai-ml` | AI/ML services, LLMs, vision, speech, agents | `azure-ai-openai-py`, `azure-ai-voicelive-dotnet` |
| `cloud-infra` | Infrastructure management, VMs, networking, containers | `azure-mgmt-compute-py`, `azure-appconfiguration-ts` |
| `data` | Databases, storage, streaming, analytics | `azure-cosmos-py`, `azure-eventhub-dotnet` |
| `development` | Frontend, frameworks, UI libraries | `react-flow-node-ts`, `fastapi-router-py` |
| `devops` | CI/CD, monitoring, observability, testing | `azure-applicationinsights-py`, `playwright-testing-ts` |
| `documentation` | Docs generation, wikis, knowledge bases | `wiki-page-writer`, `deep-wiki-onboarding` |
| `general` | Cross-cutting meta-skills | `skill-creator`, `hello-world` |
| `identity` | Authentication, secrets, key management | `azure-identity-py`, `azure-keyvault-dotnet` |
| `integration` | Messaging, events, API management | `azure-servicebus-py`, `azure-eventgrid-dotnet` |
| `security` | Security scanning, compliance, threat detection | `azure-security-py`, `azure-defender-dotnet` |

This taxonomy is **vendor-neutral**: Azure, Google, AWS, or any other vendor's
skills fit under the same domains.

## Graph Data Model Mapping

Every field in the `SKILL.md` frontmatter maps to the Neo4j graph:

```
SKILL.md frontmatter          Neo4j graph
─────────────────────          ─────────────────
domain: ai-ml           →     (:Skill)-[:BELONGS_TO]->(:Domain {name:"ai-ml"})
tags: [python, azure]   →     (:Skill)-[:TAGGED_WITH]->(:Tag {name:"python"})
tools: [AzureOpenAI]    →     (:Skill)-[:USES_TOOL]->(:Tool {name:"AzureOpenAI"})
plugin: azure-sdk-python →    (:Skill)-[:SAME_PLUGIN]-(:Skill)
category: llm-apis      →     (:Skill {category:"llm-apis"})
lang: python             →    (:Skill)-[:CROSS_LANGUAGE]-(:Skill)  (same name, different lang)
```

## How It Works

```
git push → GitHub Actions → skillctl pack → skillctl push → Catalog API syncs → Neo4j graph
```

1. **Add a skill**: create `skills/<domain>/<name>/SKILL.md`
2. **Push to main**: the CI pipeline packs and pushes to the OCI registry
3. **Catalog indexes**: the Skill Catalog API discovers new tags and indexes them
4. **Graph syncs**: `sync_catalog_to_neo4j.py` creates Skill, Domain, Tag, and Tool nodes
5. **Any app queries**: `GET /api/v1/skills` or Cypher queries return skills

## Adding a New Skill

### 1. Choose the right domain

Pick from the domain taxonomy above. If the skill doesn't fit any domain, use
`general`.

### 2. Create the SKILL.md

```markdown
---
name: my-new-skill
description: What this skill does in one sentence.
license: Apache-2.0
metadata:
  version: 1.0.0
  author: Your Name

# Graph-aligned fields
domain: ai-ml                    # Required: which domain directory
category: llm-apis               # Finer classification within domain
plugin: azure-sdk-python         # SDK/package grouping (SAME_PLUGIN edges)
lang: python                     # Programming language
tags:                            # Creates (:Tag) nodes
  - python
  - azure
  - openai
tools:                           # Creates (:Tool) nodes
  - AzureOpenAI
  - ChatCompletions
---

# My New Skill

Instructions for the AI agent go here...
```

### 3. Place and push

```bash
mkdir -p skills/ai-ml/my-new-skill
# Write your SKILL.md
git add skills/ai-ml/my-new-skill/SKILL.md
git commit -m "Add my-new-skill to ai-ml domain"
git push
```

### Adding Skills for a New Vendor

The domain structure is vendor-neutral. To add Google Cloud or AWS skills:

```bash
# Google Cloud AI skill
mkdir -p skills/ai-ml/google-vertex-ai-py
# Write SKILL.md with domain: ai-ml, plugin: google-cloud-sdk, tags: [python, gcp]

# AWS data skill
mkdir -p skills/data/aws-dynamodb-py
# Write SKILL.md with domain: data, plugin: aws-sdk-python, tags: [python, aws]
```

The `plugin` field preserves the vendor/SDK grouping without polluting the
directory structure.

## Manual Operations

```bash
# Dry run (validate only)
python scripts/publish_skills.py . --registry quay.io/rbrhssa/skills --dry-run

# Publish all
python scripts/publish_skills.py . --registry quay.io/rbrhssa/skills

# Publish first 5 only
python scripts/publish_skills.py . --registry quay.io/rbrhssa/skills --limit 5

# Reorganize from vendor to domain layout (one-time migration)
python scripts/reorganize.py --apply
```

## Catalog API

Once published, query skills at:

```bash
# List all skills
curl https://skillctl-catalog-skill-catalog.apps.ocp.v7hjl.sandbox2288.opentlc.com/api/v1/skills

# Search by keyword
curl ".../api/v1/skills?q=openai"

# Get skill detail
curl ".../api/v1/skills/rbrhssa/skills/azure-ai-openai-py-1.0.0-draft"

# Get SKILL.md content
curl ".../api/v1/skills/rbrhssa/skills/azure-ai-openai-py-1.0.0-draft/content"
```

## Required Secrets

| Secret | Description |
|--------|-------------|
| `QUAY_USERNAME` | Quay.io username |
| `QUAY_PASSWORD` | Quay.io password or robot token |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/publish_skills.py` | Pack and push skills to OCI registry |
| `scripts/reorganize.py` | One-time migration from vendor to domain layout |

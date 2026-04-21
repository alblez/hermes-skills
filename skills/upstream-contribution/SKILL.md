---
name: upstream-contribution
version: 1.1.0
description: >
  Contribute your derivative project back to the upstream OSS project it builds on.
  Detects upstream relationships, forks the upstream repo, adds your project to their
  ecosystem/community section, and opens a PR. Also finds relevant awesome lists.
author: Alberto Gonzalez Rouille
license: Apache-2.0
metadata:
  hermes:
    tags: [github, open-source, upstream, contribution, ecosystem, community, pr]
    related_skills: [github-auth, github-pr-workflow, github-repo-management]
required_environment_variables:
  - name: GITHUB_TOKEN
    prompt: "GitHub personal access token"
    help: "Classic token with public_repo scope. Fine-grained tokens scoped to your repos only will FAIL on external repos (403). Create one at https://github.com/settings/tokens"
    required_for: "forking upstream repos, opening PRs, scanning repos"
---

# Upstream OSS Contribution

Automate the "give back" step when you build something on top of an open-source project.
When you ship a tool, voice pack, plugin, extension, or wrapper built on an OSS project,
this skill helps you contribute back by adding your project to their ecosystem.

## When to Use

- You shipped a project that builds on, extends, or wraps another OSS project
- The upstream project has a README but no "Community Projects" or "Ecosystem" section (or has one you're not in)
- You want to submit your project to relevant awesome lists
- A cron job flagged an upstream contribution opportunity

## Prerequisites

- Load `github-auth` skill first — need GITHUB_TOKEN with cross-repo PR permissions
- Classic token with public_repo scope works for any public repo
- Fine-grained tokens scoped to "your repos only" will FAIL on external repos (403)

## Step 1: Identify Upstream Relationship

Detect what OSS project(s) your repo builds on:

- Check README for upstream links: grep for "built on", "powered by", "based on", "using", "fork of"
- Check repo topics via GitHub API (GET repos/OWNER/REPO/topics)
- Check dependencies (pyproject.toml, package.json, Cargo.toml, go.mod)
- Check GitHub dependency graph via SBOM endpoint

Document the relationship:
- **Your project**: owner/repo, one-line description
- **Upstream project**: owner/repo, what section to target (README, docs, wiki)
- **Relationship type**: extension, voice pack, plugin, wrapper, integration, language pack

## Step 2: Analyze Upstream README

Before forking, check what exists:

- Fetch upstream README via GitHub API (GET repos/OWNER/REPO/contents/README.md with raw accept header)
- Search for existing community/ecosystem sections (keywords: community, ecosystem, built with, projects using, awesome, third-party, integrations, extensions, plugins)

**Decision tree:**
- Has a community section → add your entry to it
- Has no community section → add one before "Citation" or "License" (whichever comes last)
- Has a CONTRIBUTING.md → read it and follow their format
- Has explicit "no external links" policy → respect it, don't PR

## Step 3: Fork and Branch

1. Fork upstream via GitHub API (POST repos/UPSTREAM_OWNER/UPSTREAM_REPO/forks)
2. Wait 5 seconds for fork to be ready
3. Clone your fork to /tmp/UPSTREAM_REPO
4. Add upstream remote
5. Create branch: `add-community-project`

## Step 4: Add Your Project

### If no community section exists — create one

Insert before the last structural section (Citation, License, Star History):

```markdown
## Community Projects

Projects built by the community on top of PROJECT_NAME:

| Project | Description |
|---------|-------------|
| [your-project](link) | One-line description. Key features. |

> Have a project built on PROJECT_NAME? Open a PR to add it here.
```

### If a community section already exists — add a row

Match the existing table format exactly.

### Writing guidelines

- Keep description to ONE line (< 120 chars if possible)
- Mention concrete value: what it does, who it helps, what it covers
- DON'T be salesy or use superlatives
- DO mention key differentiators (language, platform, use case)

## Step 5: Commit and PR

1. Commit with descriptive message
2. Push to your fork
3. Open PR via GitHub API (POST repos/UPSTREAM_OWNER/UPSTREAM_REPO/pulls)
4. If API returns 403 (fine-grained token), fall back to browser URL:
   `https://github.com/YOU/UPSTREAM_REPO/compare/main...add-community-project?expand=1`

PR body template:
- What your project does (one paragraph)
- How it relates to upstream
- Offer to adjust formatting
- Thank the maintainers

## Step 6: Find Relevant Awesome Lists (Optional)

1. Search GitHub for awesome lists in your domain (search repos with "awesome+DOMAIN" in name, sort by stars)
2. For each relevant list: read CONTRIBUTING.md, fork, add entry in correct position, open PR

## Automation: Scan Script for Cron Job

The companion cron job uses this logic to detect opportunities:

1. List all your GitHub repos
2. For each repo, extract upstream references from README + topics + dependencies
3. Check if upstream has a community/ecosystem section
4. Check if your project is already listed
5. Flag repos where you could contribute but haven't yet

See: `${HERMES_SKILL_DIR}/scripts/scan-upstream-opportunities.py`

## Cron Job Setup

The companion script `${HERMES_SKILL_DIR}/scripts/scan-upstream-opportunities.py` is designed to run as a
cron job that feeds its stdout into an agent prompt. Key setup details:

- Copy script to the Hermes scripts directory for cron access
- Weekly schedule is sufficient (e.g. Mondays 10 AM)
- Set delivery to the user's actual chat (e.g. Telegram), NOT local — local saves
  to disk silently and the user never sees the report
- Auth: ensure the GitHub auth token is available in the agent environment (the cron
  runner inherits configured environment variables automatically)
- Attach the upstream-contribution skill so the agent has the workflow if action needed

## Novelty Note

As of 2026-04, no widely-known tool automates upstream ecosystem contributions. Building
blocks exist (github-dependents-info for discovery, peter-evans/create-pull-request for
PR automation, ecosyste.ms for dependency mapping) but nobody has assembled the full
"detect derivative project and contribute back upstream" workflow. This skill and scan
script is the first implementation. No need to search for alternatives — iterate on these.

## Pitfalls

1. **Fine-grained tokens can't interact with external repos** — affects BOTH issue
   creation AND PR creation (403 on any write to repos you don't own). Use a classic
   token with public_repo scope. If the API call fails with 403, provide the user a
   browser fallback URL for manual PR creation
2. **Don't spam** — one PR per upstream project, wait for response before follow-ups
3. **Read CONTRIBUTING.md first** — some projects have strict PR guidelines
4. **Check existing PRs** — someone may have already proposed a community section
5. **Respect "no" gracefully** — if PR is declined, don't re-submit
6. **Fork may already exist** — check before forking via API
7. **Base branch may not be "main"** — check default_branch in repo metadata
8. **Large READMEs with HTML tables** — use patch tool carefully, HTML tables are fragile
9. **Awesome lists have strict quality requirements** — minimum stars, docs, tests
10. **Scan script garbage upstreams** — README regex picks up template/placeholder URLs
    (e.g. your-org/repo, GIT_USER_ID/GIT_REPO_ID). The script has an UPSTREAM_BLACKLIST
    set to filter these; add new patterns as discovered
11. **Redundant API calls drain rate limits** — upstream README is needed for both
    "is my project mentioned?" and "does a community section exist?". The script uses
    lru_cache on get_readme_content() and a combined analyze_upstream() function to
    avoid double-fetching. Maintain this pattern if modifying the script

## Verification

- PR was created successfully on the upstream repo (check GitHub API response or browser URL)
- The added entry matches the upstream's existing table format (if any)
- CONTRIBUTING.md guidelines were followed
- No duplicate PRs exist for the same project
- Scan script output lists the opportunity as "already contributed" on the next run

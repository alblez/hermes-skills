---
name: hermes-tweet
version: 0.1.8
description: >
  Use the native Hermes Tweet plugin for X research, monitoring, and
  approval-gated actions through Xquik. Use when the user asks to search X,
  inspect replies or trends, monitor X, or perform an approved X action.
author: Burak Bayır (@kriptoburak), Xquik
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [twitter, x, social-media, hermes-plugin, xquik, tweet-search]
    related_skills: [upstream-contribution]
required_environment_variables:
  - name: XQUIK_API_KEY
    prompt: "Xquik API key"
    help: "Create an API key at https://dashboard.xquik.com. tweet_explore works without a key."
    required_for: "tweet_read, tweet_action, authenticated X reads, monitoring, and approval-gated X actions"
---

# Hermes Tweet

Hermes Tweet is a native Hermes Agent plugin for X/Twitter automation through
Xquik. Use it when an agent needs structured tools for tweet search, account
reads, reply reads, trend monitoring, or approved X account actions.

Repo: https://github.com/Xquik-dev/hermes-tweet

Guide: https://docs.xquik.com/guides/hermes-tweet

PyPI: https://pypi.org/project/hermes-tweet/

Xquik is an independent third-party service. Not affiliated with X Corp.
"Twitter" and "X" are trademarks of X Corp.

## When To Use

- Search tweets from Hermes Agent.
- Read tweet replies and public tweet context.
- Look up users and account status.
- Monitor tweets, keywords, X trends, and social signals.
- Prepare post tweets, post replies, DMs, follows, monitor changes, and webhook
  changes behind a human approval step.

## Install

Install from GitHub through Hermes:

```bash
hermes plugins install Xquik-dev/hermes-tweet --enable
```

Or install the published Python package into the Hermes Python environment:

```bash
uv pip install --python ~/.hermes/hermes-agent/venv/bin/python hermes-tweet
hermes plugins enable hermes-tweet
```

Verify the toolset is visible:

```bash
hermes tools list
```

## Configure

Create an API key in Xquik and expose it to the Hermes runtime:

```bash
export XQUIK_API_KEY="xq_..."
export HERMES_TWEET_ENABLE_ACTIONS="false"
```

Keep `HERMES_TWEET_ENABLE_ACTIONS=false` for research, monitoring, and cron
workflows. Set it to `true` only when the workflow has explicit human approval
for account actions.

Do not paste API keys, X passwords, cookies, or login material into prompts or
tool arguments.

## Tool Model

| Tool | Purpose |
|------|---------|
| `tweet_explore` | Search the bundled endpoint catalog. No API call. |
| `tweet_read` | Call catalog-listed read-only endpoints. |
| `tweet_action` | Call write-like or private endpoints. Disabled by default. |

Start with `tweet_explore`, then use `tweet_read` for searches, replies, user
lookup, trends, monitors, and audits. Use `tweet_action` only after the user
approves the exact final action.

## Verification

Discovery check:

```bash
hermes -z "Use tweet_explore to find tweet search endpoints. Do not call tweet_action." --toolsets hermes-tweet
```

Authenticated read check:

```bash
hermes -z "Use tweet_explore, then read /api/v1/account. Do not call tweet_action." --toolsets hermes-tweet
```

Expected behavior:

- `tweet_explore` works without `XQUIK_API_KEY`.
- `tweet_read` works after `XQUIK_API_KEY` is configured.
- `tweet_action` stays hidden or disabled unless
  `HERMES_TWEET_ENABLE_ACTIONS=true`.

## Agent Workflow

1. Decide whether the request is read-only or action-taking.
2. Use `tweet_explore` to identify the endpoint path.
3. Use `tweet_read` for tweet search, replies, user lookup, trends, and
   monitoring.
4. Summarize searched terms, endpoint paths, timestamps, and any rate-limit or
   permission errors.
5. For post tweets, post replies, DMs, follows, monitor changes, or webhook
   changes, draft the exact action first.
6. Call `tweet_action` only after explicit approval.

## Example Prompts

```text
Use tweet_explore to find tweet search. Search X for recent posts about Hermes
Agent plugins and summarize recurring questions. Do not call tweet_action.
```

```text
Use tweet_explore to find the tweet reply read endpoint. Read replies for this
tweet URL and group the responses by sentiment and product question.
```

```text
Use tweet_read to inspect the thread. Draft a reply for approval. Only call
tweet_action after I approve the exact final text.
```

## Pitfalls

- Long-running Hermes sessions may need reload or restart after `.env` changes.
- Missing API keys should expose only safe discovery behavior.
- Action endpoints are intentionally unavailable unless actions are explicitly
  enabled.
- Do not use browser automation or cookie scraping as a fallback for this skill.

#!/usr/bin/env python3
"""
Scan GitHub repos for upstream contribution opportunities.

For each of the user's public repos, detects upstream OSS projects
(from README links, topics, dependencies) and checks if the user's
project is already mentioned in the upstream's README.

Outputs a structured report suitable for injection into a cron job prompt.

Usage:
  GITHUB_TOKEN=... python3 scan-upstream-opportunities.py [--user alblez]
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from functools import lru_cache

GITHUB_API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
DEFAULT_USER = "alblez"

# Known upstream mappings: topic -> upstream GitHub repo
TOPIC_TO_UPSTREAM = {
    "qwen3-tts": "QwenLM/Qwen3-TTS",
    "whisper": "openai/whisper",
    "llama-cpp": "ggml-org/llama.cpp",
    "stable-diffusion": "Stability-AI/stablediffusion",
    "vllm": "vllm-project/vllm",
    "mlx": "ml-explore/mlx",
    "langchain": "langchain-ai/langchain",
    "llamaindex": "run-llama/llama_index",
    "fastapi": "fastapi/fastapi",
    "pytorch": "pytorch/pytorch",
    "transformers": "huggingface/transformers",
}

# Patterns in README that indicate upstream relationship
UPSTREAM_PATTERNS = [
    # Contextual: "built on [Name](github.com/owner/repo)"
    r'(?:built on|based on|powered by|using|fork of|wrapper for|extension for)\s+\[([^\]]+)\]\(https?://github\.com/([^/]+/[^/)\s]+)',
    # Bare GitHub URLs
    r'https?://github\.com/([^/\s]+/[^/\s#)\"\']+)',
]

# Placeholder/template owners to filter out from upstream detection
UPSTREAM_BLACKLIST = {
    "your-org", "git_user_id", "username", "owner", "user",
    "example", "path", "organization", "yourusername",
    "github", "docs", "www", "shields", "img", "badge",
}


def api_get(path, accept="application/vnd.github+json"):
    """Make authenticated GitHub API GET request."""
    url = f"{GITHUB_API}{path}" if path.startswith("/") else path
    req = urllib.request.Request(url)
    req.add_header("Accept", accept)
    if TOKEN:
        req.add_header("Authorization", f"token {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        return None


def get_user_repos(user):
    """Get all public, non-fork repos for a user."""
    repos = []
    page = 1
    while True:
        data = api_get(f"/users/{user}/repos?type=owner&sort=updated&per_page=100&page={page}")
        if not data or len(data) == 0:
            break
        repos.extend(data)
        page += 1
        if len(data) < 100:
            break
    return [r for r in repos if not r.get("fork") and not r.get("private")]


def get_repo_topics(owner, repo):
    """Get topics for a repo."""
    data = api_get(f"/repos/{owner}/{repo}/topics")
    return data.get("names", []) if data else []


@lru_cache(maxsize=128)
def get_readme_content(owner, repo):
    """Get raw README content. Cached to avoid duplicate fetches."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/readme"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3.raw")
    if TOKEN:
        req.add_header("Authorization", f"token {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return ""


def find_upstream_from_topics(topics):
    """Map repo topics to known upstream projects."""
    upstreams = set()
    for topic in topics:
        topic_lower = topic.lower()
        if topic_lower in TOPIC_TO_UPSTREAM:
            upstreams.add(TOPIC_TO_UPSTREAM[topic_lower])
    return upstreams


def _is_valid_upstream(owner, repo, user):
    """Check if an owner/repo pair looks like a real upstream project."""
    owner_lower = owner.lower()
    if owner_lower in UPSTREAM_BLACKLIST:
        return False
    if owner_lower == user.lower():
        return False
    if repo.endswith((".git\"", ".git'", ".git")):
        return False
    if len(repo) <= 1:
        return False
    return True


def find_upstream_from_readme(readme_text, user):
    """Extract GitHub repo references from README using both patterns."""
    upstreams = set()

    # Pattern 0: contextual "built on [Name](github.com/owner/repo)"
    for match in re.finditer(UPSTREAM_PATTERNS[0], readme_text, re.IGNORECASE):
        repo_path = match.group(2).strip().rstrip(".")
        parts = repo_path.split("/")
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1].split("#")[0].split("?")[0].rstrip(")")
            if _is_valid_upstream(owner, repo, user):
                upstreams.add(f"{owner}/{repo}")

    # Pattern 1: bare github.com URLs
    for match in re.finditer(UPSTREAM_PATTERNS[1], readme_text):
        full = match.group(1).strip().rstrip(".\"'")
        parts = full.split("/")
        if len(parts) >= 2:
            owner = parts[0]
            repo = parts[1].split("#")[0].split("?")[0].rstrip(")\"'")
            if _is_valid_upstream(owner, repo, user):
                upstreams.add(f"{owner}/{repo}")

    return upstreams


def analyze_upstream(upstream_owner, upstream_repo, our_repo_name):
    """Check upstream README for mentions and community section in a single fetch.

    Returns (mentioned: bool|None, has_section: bool|None).
    None means the README couldn't be read.
    """
    readme = get_readme_content(upstream_owner, upstream_repo)
    if not readme:
        return None, None

    readme_lower = readme.lower()
    mentioned = our_repo_name.lower() in readme_lower

    keywords = [
        "community project", "ecosystem", "built with", "projects using",
        "third.party", "integration", "extension", "plugin", "awesome",
    ]
    has_section = any(re.search(kw, readme_lower) for kw in keywords)

    return mentioned, has_section


def parse_args():
    """Parse CLI arguments. Returns the GitHub username."""
    user = DEFAULT_USER
    if "--user" in sys.argv:
        idx = sys.argv.index("--user")
        if idx + 1 < len(sys.argv):
            user = sys.argv[idx + 1]
    return user


def process_repository(repo_data, user, opportunities, already_contributed, skipped):
    """Analyze a single repo for upstream contribution opportunities."""
    repo_name = repo_data["name"]
    full_name = repo_data["full_name"]
    description = repo_data.get("description", "") or ""

    topics = get_repo_topics(user, repo_name)
    readme = get_readme_content(user, repo_name)

    if not readme and not topics:
        skipped.append(f"{repo_name}: no README or topics")
        return

    # Find upstream candidates from topics + README
    upstreams = set()
    upstreams.update(find_upstream_from_topics(topics))
    if readme:
        upstreams.update(find_upstream_from_readme(readme, user))

    # Filter out own repos
    upstreams = {u for u in upstreams if "/" in u and u.split("/")[0].lower() != user.lower()}

    if not upstreams:
        return

    for upstream in upstreams:
        up_owner, up_repo = upstream.split("/", 1)

        # Analyze upstream README (single cached fetch)
        mentioned, has_section = analyze_upstream(up_owner, up_repo, repo_name)
        if mentioned is True:
            already_contributed.append(f"{repo_name} → {upstream} (already mentioned)")
            continue
        elif mentioned is None:
            skipped.append(f"{repo_name} → {upstream} (couldn't read upstream README)")
            continue

        opportunities.append({
            "your_repo": full_name,
            "your_description": description,
            "upstream": upstream,
            "has_community_section": has_section,
            "topics": topics,
        })


def print_report(user, repos_count, opportunities, already_contributed, skipped):
    """Print the scan results."""
    print("=" * 60)
    print("UPSTREAM CONTRIBUTION OPPORTUNITIES SCAN")
    print(f"User: {user} | Repos scanned: {repos_count}")
    print("=" * 60)

    if opportunities:
        print(f"\n🎯 OPPORTUNITIES FOUND: {len(opportunities)}\n")
        for i, opp in enumerate(opportunities, 1):
            section_status = "has community section" if opp["has_community_section"] else "NO community section yet"
            print(f"  {i}. {opp['your_repo']} → {opp['upstream']}")
            print(f"     Description: {opp['your_description']}")
            print(f"     Upstream status: {section_status}")
            print(f"     Topics: {', '.join(opp['topics'])}")
            print()
    else:
        print("\nNo new opportunities found.")

    if already_contributed:
        print(f"\n✅ ALREADY CONTRIBUTED: {len(already_contributed)}")
        for item in already_contributed:
            print(f"  - {item}")

    if skipped:
        print(f"\n⏭️  SKIPPED: {len(skipped)}")
        for item in skipped[:10]:
            print(f"  - {item}")
        if len(skipped) > 10:
            print(f"  ... and {len(skipped) - 10} more")

    print()


def main():
    user = parse_args()

    if not TOKEN:
        print("ERROR: GITHUB_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    repos = get_user_repos(user)
    if not repos:
        print("No public repos found.")
        return

    opportunities = []
    already_contributed = []
    skipped = []

    for repo_data in repos:
        process_repository(repo_data, user, opportunities, already_contributed, skipped)

    print_report(user, len(repos), opportunities, already_contributed, skipped)


if __name__ == "__main__":
    main()

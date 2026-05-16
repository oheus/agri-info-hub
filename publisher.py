#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_REPOSITORY = "oheus/agri-info-hub"
DEFAULT_BRANCH = "main"
DEFAULT_TOKEN_FILE = Path.home() / ".agri-info-hub" / "github.env"
FILES_TO_PUBLISH = [
    ("data/items.json", ROOT / "data" / "items.json"),
    ("data/summary.json", ROOT / "data" / "summary.json"),
    ("public/data/items.json", ROOT / "data" / "items.json"),
    ("public/data/summary.json", ROOT / "data" / "summary.json"),
]


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def request_json(method: str, url: str, token: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "AgriInfoHubPublisher/0.1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {method} {url} failed: HTTP {exc.code}: {detail}") from exc


def api_url(repository: str, path: str, branch: str) -> str:
    encoded_path = urllib.parse.quote(path)
    query = urllib.parse.urlencode({"ref": branch})
    return f"https://api.github.com/repos/{repository}/contents/{encoded_path}?{query}"


def fetch_sha(repository: str, path: str, branch: str, token: str) -> str | None:
    try:
        response = request_json("GET", api_url(repository, path, branch), token)
    except RuntimeError as exc:
        if "HTTP 404" in str(exc):
            return None
        raise
    sha = response.get("sha")
    return sha if isinstance(sha, str) else None


def publish_file(repository: str, branch: str, token: str, repo_path: str, local_path: Path, message: str) -> str:
    if not local_path.exists():
        raise FileNotFoundError(f"Missing local file: {local_path}")

    content = base64.b64encode(local_path.read_bytes()).decode("ascii")
    sha = fetch_sha(repository, repo_path, branch, token)
    payload: dict[str, Any] = {
        "message": message,
        "content": content,
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    url = f"https://api.github.com/repos/{repository}/contents/{urllib.parse.quote(repo_path)}"
    response = request_json("PUT", url, token, payload)
    commit = response.get("commit", {})
    commit_sha = commit.get("sha")
    return commit_sha if isinstance(commit_sha, str) else "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish Agri Info Hub JSON data to GitHub.")
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPOSITORY))
    parser.add_argument("--branch", default=os.environ.get("GITHUB_BRANCH", DEFAULT_BRANCH))
    parser.add_argument("--token-file", default=str(DEFAULT_TOKEN_FILE))
    parser.add_argument("--message", default="Update agriculture data")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env_file(Path(args.token_file).expanduser())
    token = os.environ.get("GITHUB_TOKEN")
    if not token and not args.dry_run:
        print(f"Missing GITHUB_TOKEN. Create {args.token_file} first.", file=sys.stderr)
        return 2

    for repo_path, local_path in FILES_TO_PUBLISH:
        if args.dry_run:
            print(f"Would publish {local_path} -> {args.repository}:{repo_path}")
            continue
        commit_sha = publish_file(args.repository, args.branch, token or "", repo_path, local_path, args.message)
        print(f"Published {repo_path}: {commit_sha}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from app.core.env import load_env_file

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "evals" / "real_repo_analysis.json"
MAX_FILES = 14
MAX_SNIPPET = 2000
INTERESTING_FILE_NAMES = {
    "readme.md",
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "pom.xml",
    "build.gradle",
    "go.mod",
    "cargo.toml",
    "dockerfile",
    "serverless.yml",
    "serverless.yaml",
    "cdk.json",
    "docker-compose.yml",
    "docker-compose.yaml",
}


def _github_request(path: str, token: str) -> dict | list:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(
        url=url,
        method="GET",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "Sketch-to-Cloud-eval-builder",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _decode_blob(blob: dict[str, Any]) -> str:
    if str(blob.get("encoding", "")).lower() != "base64":
        return ""
    content = blob.get("content")
    if not isinstance(content, str):
        return ""
    raw = base64.b64decode(content.encode("utf-8"), validate=False)
    return raw.decode("utf-8", errors="ignore")[:MAX_SNIPPET]


def _build_prompt(repo_full_name: str, repo_meta: dict[str, Any], files: list[str], snippets: dict[str, str]) -> str:
    default_branch = str(repo_meta.get("default_branch", "main"))
    description = str(repo_meta.get("description") or "")
    topics = repo_meta.get("topics") if isinstance(repo_meta.get("topics"), list) else []
    topics_text = ", ".join(str(t) for t in topics[:10])
    file_list = "\n".join(f"- {path}" for path in files[:200])
    snippet_text = "\n\n".join(f"[{path}]\n{text}" for path, text in snippets.items())
    return (
        f"Repository: {repo_full_name}\n"
        f"Default branch: {default_branch}\n"
        f"Description: {description}\n"
        f"Topics: {topics_text}\n\n"
        f"File tree sample:\n{file_list}\n\n"
        f"Important file snippets:\n{snippet_text}\n\n"
        "Task: Infer realistic AWS deployment architecture for this repository."
    )


def _build_case(repo_full_name: str, token: str) -> dict[str, Any]:
    encoded = urllib.parse.quote(repo_full_name, safe="/")
    repo_meta = _github_request(f"/repos/{encoded}", token)
    if not isinstance(repo_meta, dict):
        raise RuntimeError(f"Invalid repo meta for {repo_full_name}")
    default_branch = str(repo_meta.get("default_branch", "main"))
    tree = _github_request(
        f"/repos/{encoded}/git/trees/{urllib.parse.quote(default_branch, safe='')}?recursive=1",
        token,
    )
    tree_items = tree.get("tree") if isinstance(tree, dict) else None
    if not isinstance(tree_items, list):
        raise RuntimeError(f"Tree unavailable for {repo_full_name}")

    files = [str(item.get("path")) for item in tree_items if isinstance(item, dict) and item.get("type") == "blob" and isinstance(item.get("path"), str)]
    candidates: list[tuple[str, str]] = []
    for item in tree_items:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        sha = item.get("sha")
        if not isinstance(path, str) or not isinstance(sha, str):
            continue
        normalized = path.lower()
        filename = normalized.split("/")[-1]
        if filename in INTERESTING_FILE_NAMES or normalized.startswith(".github/workflows/"):
            candidates.append((normalized, sha))
        if len(candidates) >= MAX_FILES:
            break

    snippets: dict[str, str] = {}
    for path, sha in candidates:
        blob = _github_request(f"/repos/{encoded}/git/blobs/{sha}", token)
        if isinstance(blob, dict):
            decoded = _decode_blob(blob)
            if decoded:
                snippets[path] = decoded

    prompt = _build_prompt(repo_full_name, repo_meta, files, snippets)
    return {
        "id": repo_full_name.replace("/", "_"),
        "repo": repo_full_name,
        "repo_prompt": prompt,
        "expected": {
            "recommended_any": [],
            "forbidden_all": [],
            "ec2_max": 10,
            "rds_enabled": False,
            "architecture_services_any": [],
            "must_be_korean": True,
        },
    }


def main() -> int:
    load_env_file()
    parser = argparse.ArgumentParser(description="Build real repository eval dataset skeleton.")
    parser.add_argument("--repos", nargs="+", required=True, help="owner/repo list")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--token-env", default="GITHUB_PERSONAL_TOKEN")
    args = parser.parse_args()

    token = os.getenv(args.token_env) or os.getenv("GITHUB_EVAL_TOKEN")
    if not token:
        print(f"Missing GitHub token in env `{args.token_env}` or `GITHUB_EVAL_TOKEN`")
        return 1

    cases: list[dict[str, Any]] = []
    for repo in args.repos:
        try:
            cases.append(_build_case(repo, token))
            print(f"[OK] built case for {repo}")
        except urllib.error.HTTPError as exc:
            print(f"[FAIL] {repo}: GitHub HTTP {exc.code}")
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {repo}: {exc}")

    payload = {
        "version": "v1",
        "description": "Real repository regression set. Fill expected fields after first run.",
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(cases)} cases to {args.output}")
    return 0 if cases else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""
AI Code Review script.

Called by the ai-code-review GitHub Actions workflow.
Reads the git diff for the latest commit, sends it to the OpenAI Chat
Completions API, and posts the resulting review as a commit comment.

Required environment variables
--------------------------------
OPENAI_API_KEY  – OpenAI secret key (stored as a GitHub Actions secret)
GITHUB_TOKEN    – Automatically provided by GitHub Actions
COMMIT_SHA      – SHA of the commit being reviewed  (${{ github.sha }})
REPO            – <owner>/<repo> slug              (${{ github.repository }})
"""

import json
import os
import subprocess
import sys
import urllib.request
import urllib.error


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL = "gpt-4o"
# Conservative character limit; gpt-4o averages ~4 chars/token so 15 000
# chars ≈ 3 750 tokens – well within the 128 k-token context window while
# keeping API calls reasonably sized.
MAX_DIFF_CHARS = 15_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def validate_env(*names: str) -> None:
    """Exit with a clear error message if any required variable is missing."""
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        print(f"Error: required environment variable(s) not set: {', '.join(missing)}")
        sys.exit(1)


def get_diff() -> str:
    """Return the unified diff between the previous commit and HEAD."""
    result = subprocess.run(
        ["git", "diff", "HEAD~1", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Likely the very first commit – show the full diff of HEAD instead.
        result = subprocess.run(
            ["git", "show", "HEAD"],
            capture_output=True,
            text=True,
        )
    return result.stdout


def review_code(diff: str) -> str:
    """Send *diff* to OpenAI and return the review text."""
    if not diff.strip():
        return "No code changes detected – nothing to review."

    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + "\n\n… (diff truncated to fit token limit)"

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert code reviewer. "
                    "Review the following git diff and provide clear, "
                    "constructive feedback covering: code quality, potential "
                    "bugs, security issues, performance, and best practices. "
                    "Be concise and specific. Use markdown formatting."
                ),
            },
            {
                "role": "user",
                "content": f"Please review this code change:\n\n```diff\n{diff}\n```",
            },
        ],
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=data,
        method="POST",
    )
    req.add_header("Authorization", f"Bearer {os.environ['OPENAI_API_KEY']}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"OpenAI API error: {exc.code} {exc.reason}")
        print(exc.read().decode())
        raise
    except urllib.error.URLError as exc:
        print(f"Network error when calling OpenAI API: {exc.reason}")
        raise

    return body["choices"][0]["message"]["content"]


def post_commit_comment(body: str, commit_sha: str, repo: str) -> None:
    """Post *body* as a commit comment on GitHub."""
    token = os.environ["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/commits/{commit_sha}/comments"

    data = json.dumps({"body": f"## 🤖 AI Code Review\n\n{body}"}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")

    try:
        with urllib.request.urlopen(req) as resp:
            print(f"Commit comment posted (HTTP {resp.status}).")
    except urllib.error.HTTPError as exc:
        print(f"Failed to post commit comment: {exc.code} {exc.reason}")
        print(exc.read().decode())
        raise


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    validate_env("OPENAI_API_KEY", "COMMIT_SHA", "REPO")

    diff = get_diff()
    print("--- diff preview (first 500 chars) ---")
    print(diff[:500])
    print("--------------------------------------")

    review = review_code(diff)
    print("\n--- AI review ---")
    print(review)
    print("-----------------\n")

    post_commit_comment(review, os.environ["COMMIT_SHA"], os.environ["REPO"])

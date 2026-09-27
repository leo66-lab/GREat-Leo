from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

import requests

from .config import DB_PATH


DEFAULT_REPO = "leo66-lab/GREat-Leo"
DEFAULT_BRANCH = "main"
DEFAULT_DB_PATH = "gre_vocab.db"
API_ROOT = "https://api.github.com"


def _secret_value(name: str, default: str = "") -> str:
    env_value = os.environ.get(name)
    if env_value:
        return env_value.strip()
    try:
        import streamlit as st

        value = st.secrets.get(name, default)
    except Exception:  # noqa: BLE001 - secrets are optional outside Streamlit.
        value = default
    return str(value or default).strip()


def github_sync_enabled() -> bool:
    explicit = _secret_value("GITHUB_DB_SYNC", "").lower()
    if explicit in {"0", "false", "no", "off"}:
        return False
    if explicit in {"1", "true", "yes", "on"}:
        return bool(_secret_value("GITHUB_TOKEN"))
    return bool(_secret_value("GITHUB_TOKEN"))


def sync_config() -> dict[str, str]:
    return {
        "token": _secret_value("GITHUB_TOKEN"),
        "repo": _secret_value("GITHUB_REPO", DEFAULT_REPO),
        "branch": _secret_value("GITHUB_BRANCH", DEFAULT_BRANCH),
        "db_path": _secret_value("GITHUB_DB_PATH", DEFAULT_DB_PATH),
    }


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _content_url(repo: str, db_path: str) -> str:
    return f"{API_ROOT}/repos/{repo}/contents/{db_path}"


def _remote_file(config: dict[str, str]) -> dict[str, Any]:
    response = requests.get(
        _content_url(config["repo"], config["db_path"]),
        headers=_headers(config["token"]),
        params={"ref": config["branch"]},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def pull_database_from_github() -> dict[str, Any]:
    if not github_sync_enabled():
        return {"status": "skipped", "reason": "not_configured"}
    config = sync_config()
    remote = _remote_file(config)
    content = base64.b64decode(remote["content"])
    if DB_PATH.exists() and DB_PATH.read_bytes() == content:
        return {"status": "unchanged"}

    temp_path = Path(str(DB_PATH) + ".download")
    temp_path.write_bytes(content)
    temp_path.replace(DB_PATH)
    return {"status": "pulled", "sha": remote.get("sha", "")}


def push_database_to_github(message: str = "Update GRE vocabulary database") -> dict[str, Any]:
    if not github_sync_enabled():
        return {"status": "skipped", "reason": "not_configured"}
    if not DB_PATH.exists():
        return {"status": "skipped", "reason": "missing_database"}

    config = sync_config()
    remote = _remote_file(config)
    encoded = base64.b64encode(DB_PATH.read_bytes()).decode("ascii")
    if remote.get("content", "").replace("\n", "") == encoded:
        return {"status": "unchanged", "sha": remote.get("sha", "")}

    response = requests.put(
        _content_url(config["repo"], config["db_path"]),
        headers=_headers(config["token"]),
        json={
            "message": message,
            "content": encoded,
            "sha": remote["sha"],
            "branch": config["branch"],
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return {"status": "pushed", "sha": data.get("content", {}).get("sha", "")}

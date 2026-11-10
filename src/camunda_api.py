"""Client tối giản cho Orchestration Cluster REST API (Camunda 8.8+, endpoint /v2).

Camunda 8 Run mặc định không bật xác thực cho API. Nếu bật, đặt biến môi trường
CAMUNDA_USER / CAMUNDA_PASSWORD (Basic auth, mặc định của C8 Run là demo/demo).
"""
import os
from pathlib import Path

import requests

BASE_URL = os.getenv("CAMUNDA_URL", "http://localhost:8080/v2").rstrip("/")
_AUTH = None
if os.getenv("CAMUNDA_USER"):
    _AUTH = (os.getenv("CAMUNDA_USER"), os.getenv("CAMUNDA_PASSWORD", ""))

_session = requests.Session()


def _post(path: str, **kwargs) -> dict:
    resp = _session.post(f"{BASE_URL}{path}", auth=_AUTH, timeout=kwargs.pop("timeout", 30), **kwargs)
    if resp.status_code >= 400:
        raise RuntimeError(f"POST {path} -> {resp.status_code}: {resp.text}")
    return resp.json() if resp.content else {}


def topology() -> dict:
    resp = _session.get(f"{BASE_URL}/topology", auth=_AUTH, timeout=10)
    resp.raise_for_status()
    return resp.json()


def deploy(paths: list[Path]) -> dict:
    """POST /deployments (multipart, field 'resources', nhiều file)."""
    files = [("resources", (p.name, p.read_bytes(), "application/octet-stream")) for p in paths]
    return _post("/deployments", files=files)


def start_instance(process_id: str, variables: dict) -> dict:
    """POST /process-instances theo BPMN process id, phiên bản mới nhất."""
    return _post("/process-instances", json={"processDefinitionId": process_id, "variables": variables})


def search_user_tasks(process_instance_key: str) -> list[dict]:
    """Return created Camunda user tasks for one process instance."""
    return search("user-tasks", {"processInstanceKey": str(process_instance_key), "state": "CREATED"})


def complete_user_task(user_task_key: str, variables: dict) -> None:
    """Complete a Camunda user task with form variables."""
    _post(f"/user-tasks/{user_task_key}/completion", json={"variables": variables})


def activate_jobs(job_type: str, worker: str, max_jobs: int = 5,
                  timeout_ms: int = 30_000, request_timeout_ms: int = 20_000) -> list[dict]:
    """POST /jobs/activation, long polling tối đa request_timeout_ms."""
    body = {"type": job_type, "worker": worker, "timeout": timeout_ms,
            "maxJobsToActivate": max_jobs, "requestTimeout": request_timeout_ms}
    return _post("/jobs/activation", json=body, timeout=request_timeout_ms / 1000 + 10).get("jobs", [])


def complete_job(job_key: str, variables: dict | None = None) -> None:
    _post(f"/jobs/{job_key}/completion", json={"variables": variables or {}})


def fail_job(job_key: str, retries: int, message: str) -> None:
    _post(f"/jobs/{job_key}/failure", json={"retries": retries, "errorMessage": message})


def search(resource: str, filter_: dict, limit: int = 200) -> list[dict]:
    """POST /<resource>/search, ví dụ resource='element-instances'. Tự lật trang theo offset."""
    items, start = [], 0
    while True:
        page = _post(f"/{resource}/search", json={"filter": filter_, "page": {"from": start, "limit": limit}})
        batch = page.get("items", [])
        items += batch
        if len(batch) < limit:
            return items
        start += limit

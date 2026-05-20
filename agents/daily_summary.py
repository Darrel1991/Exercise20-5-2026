"""
/pipeline:daily-summary — Posts a daily activity summary to Zoho Projects.

Usage:
    python agents/daily_summary.py --summary "Your summary text" --date "2026-05-12"

The script will:
1. Load Zoho credentials from .env
2. Get a fresh access token
3. Find the "Internal" project (fallback: "TNB Mobile GIS")
4. Create a new task with the summary as the description
5. Log the action to logs/audit.log via the Logger Service
"""

import argparse
import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime

# ── Load .env ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_env():
    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        print("ERROR: .env file not found. Copy .env.example to .env and fill in credentials.")
        sys.exit(1)
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

load_env()

ZOHO_CLIENT_ID     = os.environ.get("ZOHO_CLIENT_ID", "")
ZOHO_CLIENT_SECRET = os.environ.get("ZOHO_CLIENT_SECRET", "")
ZOHO_REFRESH_TOKEN = os.environ.get("ZOHO_REFRESH_TOKEN", "")
PORTAL_ID          = "662990611"
USER_EMAIL         = "darrel.low@redplanet.com.my"
USER_ZPUID         = "1234245000000894129"
LOGGER_URL         = "http://localhost:5000"
PREFERRED_PROJECT  = "Internal"
FALLBACK_PROJECT   = "TNB Mobile GIS"

# ── Helpers ───────────────────────────────────────────────────────────────────

def zoho_request(method, url, data=None, token=None):
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if token:
        headers["Authorization"] = f"Zoho-oauthtoken {token}"
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def get_access_token():
    resp = zoho_request("POST", "https://accounts.zoho.com/oauth/v2/token", {
        "grant_type": "refresh_token",
        "client_id": ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "refresh_token": ZOHO_REFRESH_TOKEN,
    })
    token = resp.get("access_token")
    if not token:
        print(f"ERROR: Could not get access token — {resp}")
        sys.exit(1)
    return token


def get_projects(token):
    resp = zoho_request("GET", f"https://projectsapi.zoho.com/restapi/portal/{PORTAL_ID}/projects/", token=token)
    return resp.get("projects", [])


def find_project(projects, name):
    for p in projects:
        if p["name"].lower() == name.lower():
            return p["id_string"]
    return None


def create_task(token, project_id, task_name, description):
    data = {
        "name": task_name,
        "description": description,
        "person_responsible": USER_ZPUID,
    }
    resp = zoho_request("POST",
        f"https://projectsapi.zoho.com/restapi/portal/{PORTAL_ID}/projects/{project_id}/tasks/",
        data=data, token=token)
    tasks = resp.get("tasks", [])
    if tasks:
        return tasks[0]
    return None


def log_audit(action, status):
    try:
        payload = json.dumps({
            "user": USER_EMAIL,
            "command": "/pipeline:daily-summary",
            "classification": "INTERNAL",
            "action": action,
            "status": status,
        }).encode()
        req = urllib.request.Request(
            f"{LOGGER_URL}/audit",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass  # Logger may not be running — don't block the main flow


def log_error(message):
    try:
        payload = json.dumps({
            "level": "ERROR",
            "service": "DailySummary",
            "user": USER_EMAIL,
            "message": message,
        }).encode()
        req = urllib.request.Request(
            f"{LOGGER_URL}/log",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Post daily summary to Zoho Projects")
    parser.add_argument("--summary", required=True, help="Summary text to post")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Date (YYYY-MM-DD)")
    args = parser.parse_args()

    task_name = f"Daily Summary - {args.date}"
    summary_text = args.summary

    print(f"\nPosting to Zoho Projects...")
    print(f"Task: {task_name}\n")

    # Get token
    token = get_access_token()

    # Find project
    projects = get_projects(token)
    project_id = find_project(projects, PREFERRED_PROJECT)
    project_name = PREFERRED_PROJECT

    if not project_id:
        print(f'Project "{PREFERRED_PROJECT}" not found — falling back to "{FALLBACK_PROJECT}"')
        project_id = find_project(projects, FALLBACK_PROJECT)
        project_name = FALLBACK_PROJECT

    if not project_id:
        msg = f'Neither "{PREFERRED_PROJECT}" nor "{FALLBACK_PROJECT}" found in Zoho Projects.'
        print(f"ERROR: {msg}")
        log_error(msg)
        sys.exit(1)

    # Create task
    task = create_task(token, project_id, task_name, summary_text)

    if task:
        print(f"[OK] Task created successfully!")
        print(f"   Project:  {project_name}")
        print(f"   Task:     {task.get('name')}")
        print(f"   Task ID:  {task.get('id_string')}")
        log_audit(f"Daily summary posted to Zoho Projects ({project_name}) — Task: {task_name}", "approved")
    else:
        print("ERROR: Task creation failed.")
        log_error(f"Failed to create task '{task_name}' in project '{project_name}'")
        sys.exit(1)


if __name__ == "__main__":
    main()

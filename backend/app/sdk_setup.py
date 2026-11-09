"""One-time ServiceNow SDK setup for flow deployment, with its progress on screen.

    cd backend
    .venv\\Scripts\\Activate.ps1
    python -m app.sdk_setup

For every connected Development / Test instance that has a username and password saved, this
creates the scoped SDK project in data/sdk/<instance>/ (scope x_<vendor prefix>_nbuild), runs
`npm install` (downloads @servicenow/sdk; the slow part), and stores the SDK sign-in. After it says
"ready", flows deploy from the chat in about a minute. Safe to run again.
"""
from __future__ import annotations

import sys

from sqlalchemy import select


def main() -> int:
    from .db import SessionLocal, init_db
    from .models import Instance
    from .security import decrypt
    from .services import sdk_deploy
    from .services.servicenow import ServiceNowClient

    init_db()
    node = sdk_deploy.node_version()
    print(f"Node.js: {node or 'NOT FOUND'}")
    if not node:
        print("Install Node.js 20 or later from https://nodejs.org (LTS), reopen the terminal, and run this again.")
        return 1
    if int(node.lstrip("v").split(".")[0]) < 20:
        print(f"Node.js {node} is too old: the ServiceNow SDK needs 20 or later. Install the LTS from https://nodejs.org.")
        return 1

    db = SessionLocal()
    try:
        instances = [i for i in db.scalars(select(Instance)) if i.instance_type != "Production" and i.password_enc]
        if not instances:
            print("No Development/Test instance with a username and password is connected yet. Connect one in "
                  "Settings → ServiceNow instances, then run this again.")
            return 1
        failed = 0
        for inst in instances:
            print(f"\n=== {inst.name}: {inst.url} ===")
            try:
                project, alias = sdk_deploy.ensure_project(
                    inst.url, inst.username, decrypt(inst.password_enc), ServiceNowClient(inst, db),
                    on_status=lambda s: print(f"-- {s}", flush=True), live=True)
                print(f"\nReady. SDK project: {project} (credential alias {alias}).")
            except sdk_deploy.SDKDeployError as e:
                failed += 1
                print(f"\nFAILED: {e}")
        if not failed:
            print("\nAll set. Flows now deploy when you click Deploy on the plan card (Deploy the remaining N retries one that waited).")
        return 1 if failed else 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())

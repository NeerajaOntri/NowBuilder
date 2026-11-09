"""Collect what the installed ServiceNow SDK says about flow logic, Global applications and Send Email,
so nowBuilder's flow exporter can be extended from the SDK's own documentation instead of guesses.

    python -m app.sdk_probe

Runs only local, read-only commands (`now-sdk --version`, `now-sdk explain ...`) and reads files inside
the SDK project's node_modules/@servicenow. Nothing is sent to an instance, and no credentials are read.
Writes backend/data/sdk_probe.md; send that file to whoever maintains nowBuilder.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from .services import sdk_deploy

KEYWORDS = ("flow", "logic", "global", "wait", "email", "notification")
TOPIC = re.compile(r"\b[a-z][a-z0-9]*(?:-[a-z0-9]+)+\b")
FILE_HINTS = ("doTheFollowingUntil", "waitForADuration", "DoTheFollowingUntil", "WaitForADuration")
MAX_BYTES = 3_000_000


def _run(cwd: Path, cmd: list[str]) -> str:
    try:
        # The SDK prints UTF-8; Windows would otherwise decode it with its own code page and fail.
        out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                             timeout=180, check=False, stdin=subprocess.DEVNULL)
        stdout, stderr = out.stdout or "", out.stderr or ""
        return (stdout + ("\n" + stderr if stderr.strip() else "")).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return f"(could not run: {exc})"


def _snippets(root: Path) -> list[str]:
    out: list[str] = []
    base = root / "node_modules" / "@servicenow"
    if not base.is_dir():
        return ["(no node_modules/@servicenow in this project)"]
    for path in base.rglob("*"):
        if not path.is_file() or path.suffix not in (".ts", ".js", ".json", ".mjs", ".cjs"):
            continue
        if path.stat().st_size > 4_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        name_hit = any(h.lower().replace("thefollowing", "") in path.name.lower() for h in ("wait-for", "do-the-following"))
        hits = [m.start() for h in FILE_HINTS for m in re.finditer(re.escape(h), text)][:3]
        if name_hit and not hits:
            hits = [0]
        for at in hits:
            out.append(f"### {path.relative_to(root)} @ {at}\n```\n{text[max(0, at - 1500):at + 2500]}\n```")
        if len(out) > 60:
            return out
    return out or ["(nothing in node_modules mentions waitForADuration / doTheFollowingUntil)"]


def probe(project: Path) -> str:
    sdk = sdk_deploy._local_sdk(project)
    parts = [f"# SDK project {project.name}", "## now-sdk --version", "```", _run(project, [*sdk, "--version"]), "```"]
    topics: list[str] = []
    for word in KEYWORDS:
        listing = _run(project, [*sdk, "explain", word, "--list", "--format", "raw"])
        parts += [f"## now-sdk explain {word} --list", "```", listing[:20000], "```"]
        topics += [t for t in TOPIC.findall(listing) if any(k in t for k in KEYWORDS) and t not in topics]
    for topic in topics[:20]:
        parts += [f"## now-sdk explain {topic}", "```", _run(project, [*sdk, "explain", topic, "--format", "raw"])[:60000], "```"]
    parts += ["## SDK files about Wait / Do the following until", *_snippets(project)]
    return "\n".join(parts)


def main() -> int:
    root = sdk_deploy._data_root()
    projects = sorted(p.parent for p in root.glob("*/now.config.json") if (p.parent / "node_modules").is_dir())
    if not projects:
        print("No ServiceNow SDK project is set up yet. Run setup-flows.ps1 first.")
        return 1
    print(f"Reading the ServiceNow SDK's own documentation from {projects[0]} (a minute or two)...", flush=True)
    text = probe(projects[0]).encode("utf-8")[:MAX_BYTES].decode("utf-8", errors="ignore")
    out = root.parent / "sdk_probe.md"
    out.write_text(text, encoding="utf-8")
    print(f"Done. Send this file: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

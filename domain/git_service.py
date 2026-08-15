import subprocess
import os
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models import Thread, Surface, Event, utcnow

GIT_CACHE: Dict[str, Dict[str, Any]] = {}
GIT_CACHE_TTL = 5.0

def _run_git_command(repo_path: str, args: list, timeout: float = 1.5) -> Optional[str]:
    try:
        if not os.path.exists(repo_path) or not os.path.isdir(repo_path):
            return None
        res = subprocess.run(
            ['git'] + args,
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            shell=False
        )
        if res.returncode == 0:
            return res.stdout.strip()
        return None
    except Exception:
        return None

def inspect_git_working_set(repo_path: Optional[str]) -> Dict[str, Any]:
    if not repo_path or not os.path.exists(repo_path):
        return {}

    now = time.time()
    if repo_path in GIT_CACHE:
        cached_entry = GIT_CACHE[repo_path]
        if now - cached_entry['timestamp'] < GIT_CACHE_TTL:
            return cached_entry['data']

    is_git = _run_git_command(repo_path, ['rev-parse', '--is-inside-work-tree'])
    if not is_git or is_git.lower() != 'true':
        return {}

    branch = _run_git_command(repo_path, ['symbolic-ref', '--short', 'HEAD'])
    if not branch:
        branch = _run_git_command(repo_path, ['rev-parse', '--short', 'HEAD']) or 'HEAD'

    commit = _run_git_command(repo_path, ['rev-parse', '--short', 'HEAD'])

    status_output = _run_git_command(repo_path, ['status', '--porcelain'])
    changed_files = [line for line in status_output.splitlines() if line.strip()] if status_output else []
    files_changed_count = len(changed_files)

    additions = 0
    deletions = 0
    diff_stat = _run_git_command(repo_path, ['diff', '--shortstat'])
    if diff_stat:
        parts = diff_stat.split(',')
        for p in parts:
            if 'insertion' in p:
                additions += int(''.join(filter(str.isdigit, p))  or 0)
            elif 'deletion' in p:
                deletions += int(''.join(filter(str.isdigit, p)) or 0)

    cached_diff_stat = _run_git_command(repo_path, ['diff', '--cached', '--shortstat'])
    if cached_diff_stat:
        parts = cached_diff_stat.split(',')
        for p in parts:
            if 'insertion' in p:
                additions += int(''.join(filter(str.isdigit, p))  or 0)
            elif 'deletion' in p:
                deletions += int(''.join(filter(str.isdigit, p))  or 0)

    repo_name = Path(repo_path).name or repo_path

    working_set = {
        'repo': repo_name,
        'repo_path': repo_path.replace('\\', '/'),
        'branch': branch,
        'commit': commit,
        'files_changed_count': files_changed_count,
        'additions': additions,
        'deletions': deletions,
        'is_dirty': files_changed_count > 0,
        'synced_at': time.strftime('%H:%M:%S')
    }

    GIT_CACHE[repo_path] = {
        'timestamp': now,
        'data': working_set
    }

    return working_set

def sync_thread_git_working_set(db: Session, thread_id: int, append_diff_event: bool = False) -> Optional[Dict[str, Any]]:
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        return None

    repo_path = None
    existing_ws = thread.get_working_set()
    if existing_ws.get('repo_path') and os.path.exists(existing_ws.get('repo_path')):
        repo_path = existing_ws.get('repo_path')
    else:
        for s in thread.surfaces:
            if s.local_path and os.path.exists(s.local_path):
                repo_path = s.local_path
                break

    if not repo_path:
        cwd = os.getcwd()
        if os.path.exists(os.path.join(cwd, '.git')):
            repo_path = cwd

    if not repo_path:
        return existing_ws

    live_ws = inspect_git_working_set(repo_path)
    if not live_ws:
        return existing_ws

    merged_ws = {**existing_ws, **live_ws}
    thread.working_set_json = json.dumps(merged_ws)
    thread.last_active_at = utcnow()

    # If a new commit was made externally and working tree is now clean, auto-advance frontier
    old_commit = existing_ws.get('commit')
    new_commit = live_ws.get('commit')
    if new_commit and old_commit and new_commit != old_commit and not live_ws.get('is_dirty'):
        commit_msg = _run_git_command(repo_path, ["log", "-1", "--format=%s"]) or "Checkpoint commit"
        thread.frontier = f"Checkpointed @{new_commit}: {commit_msg}. Working tree clean."
        thread.next_action = f"Proceed from checkpoint @{new_commit} or review next architectural milestone."

    if append_diff_event and live_ws.get('is_dirty'):
        br = live_ws.get('branch')
        cm = live_ws.get('commit')
        fc = live_ws.get('files_changed_count')
        ad = live_ws.get('additions')
        dl = live_ws.get('deletions')
        summary = f"Git working set synced: {br} @{cm} ({fc} files changed, +{ad}/-{dl})."
        event = Event(
            thread_id=thread.id,
            event_type='GIT_DIFF',
            summary=summary,
            payload_json=json.dumps(live_ws),
            occurred_at=utcnow()
        )
        db.add(event)

    db.commit()
    db.refresh(thread)
    return merged_ws


def git_commit_working_set(repo_path: str, commit_message: str, do_push: bool = False) -> Dict[str, Any]:
    """
    Stages all changes, creates a Git commit, optionally pushes,
    and returns status with the new commit hash.
    """
    if not repo_path or not os.path.exists(repo_path):
        return {"error": "Invalid repository path", "status": "failed"}

    # 1. Stage all changes
    _run_git_command(repo_path, ["add", "-A"])

    # 2. Create commit
    commit_res = _run_git_command(repo_path, ["commit", "-m", commit_message.strip()])
    if commit_res is None:
        # Check if working tree was already clean
        status_out = _run_git_command(repo_path, ["status", "--porcelain"])
        if not status_out:
            cur_commit = _run_git_command(repo_path, ["rev-parse", "--short", "HEAD"])
            return {"status": "clean", "commit": cur_commit, "message": "Nothing to commit, working tree clean"}
        return {"error": "Git commit failed", "status": "failed"}

    # 3. Get new short commit hash
    new_commit = _run_git_command(repo_path, ["rev-parse", "--short", "HEAD"])

    # 4. Optional push
    pushed = False
    if do_push:
        push_res = _run_git_command(repo_path, ["push"])
        pushed = push_res is not None

    # Invalidate cache
    if repo_path in GIT_CACHE:
        del GIT_CACHE[repo_path]

    return {
        "status": "success",
        "commit": new_commit,
        "message": commit_message,
        "pushed": pushed
    }



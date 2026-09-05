# -*- coding: utf-8 -*-
"""
Create or remove a Windows Scheduled Task for daily SMA database backups.

This wraps scripts/backup_db.py so Windows Task Scheduler handles the cron-like
scheduling (the app itself has no internal scheduler).

Usage (run from the project root):
    python scripts/schedule_backup.py --install      # register the daily task
    python scripts/schedule_backup.py --remove       # unregister the task
    python scripts/schedule_backup.py --run          # run a backup now (same as backup_db.py)

The task runs under the current user account, whether logged on or not,
at 02:00 every day. Backups go to the ``backups/`` directory with the
configured retention (default 30 days).

Requirements:
    - Windows OS with schtasks available (Windows 10/11, Server 2016+)
    - The Python interpreter on PATH (or set SMA_PYTHON)
    - Project root detectable (uses this file's location)
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

TASK_NAME = "SarkinMota Daily Backup"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKUP_SCRIPT = PROJECT_ROOT / "scripts" / "backup_db.py"
LOG_DIR = PROJECT_ROOT / "logs"


def _python_exe() -> str:
    return os.environ.get("SMA_PYTHON", sys.executable)


def _build_run_command() -> list[str]:
    return [
        _python_exe(),
        str(BACKUP_SCRIPT),
        "--retention",
        os.environ.get("SMA_BACKUP_RETENTION_DAYS", "30"),
    ]


def install() -> int:
    LOG_DIR.mkdir(exist_ok=True)
    # schtasks /Create /SC DAILY /ST 02:00 /TN "name" /TR "command" /F /RL LIMITED
    # Use pythonw.exe so no console window flashes on the desktop.
    pythonw = _python_exe().replace("python.exe", "pythonw.exe")
    if not Path(pythonw).exists():
        pythonw = _python_exe()

    run_cmd = f'"{pythonw}" "{BACKUP_SCRIPT}" --retention {os.environ.get("SMA_BACKUP_RETENTION_DAYS", "30")}'
    cmd = [
        "schtasks",
        "/Create",
        "/SC", "DAILY",
        "/ST", "02:00",
        "/TN", TASK_NAME,
        "/TR", run_cmd,
        "/F",
        "/RL", "LIMITED",
    ]
    print(f"Registering scheduled task: {TASK_NAME}")
    print(f"Command: {run_cmd}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        print("Failed to register the scheduled task. Try running as Administrator.", file=sys.stderr)
        return result.returncode
    print("Task registered successfully. Backups will run daily at 02:00.")
    return 0


def remove() -> int:
    cmd = ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"]
    print(f"Removing scheduled task: {TASK_NAME}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return result.returncode
    print("Task removed.")
    return 0


def run_now() -> int:
    from scripts.backup_db import main
    return main()


def main() -> int:
    parser = argparse.ArgumentParser(description="SMA backup scheduler helper")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--install", action="store_true", help="Register the daily backup task")
    group.add_argument("--remove", action="store_true", help="Remove the daily backup task")
    group.add_argument("--run", action="store_true", help="Run a backup immediately")
    args = parser.parse_args()

    if args.install:
        return install()
    if args.remove:
        return remove()
    return run_now()


if __name__ == "__main__":
    sys.exit(main())

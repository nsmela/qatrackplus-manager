from __future__ import annotations
import os
from typing import List
from ..transport.base import Transport
from . import TestResult
from ..config.models import ManagerState

def test_app_files(transport: Transport, state: ManagerState) -> List[TestResult]:
    results = []
    app_dir = state.servers[0].app_dir
    
    # manage.py
    if transport.file_exists(os.path.join(app_dir, "manage.py")):
        results.append(TestResult("manage.py present", "pass"))
    else:
        results.append(TestResult("manage.py present", "fail"))

    # local_settings.py
    if state.local_settings_file and transport.file_exists(state.local_settings_file):
        results.append(TestResult("local_settings.py present", "pass"))
    else:
        results.append(TestResult("local_settings.py present", "fail", "File missing or path not detected"))

    return results

def test_django_checks(transport: Transport, state: ManagerState) -> List[TestResult]:
    results = []
    app_dir = state.servers[0].app_dir
    venv_dir = os.path.join(app_dir, "venv")
    python_bin = os.path.join(venv_dir, "bin", "python")
    env = {"DJANGO_SETTINGS_MODULE": state.django_settings}
    
    # manage.py check
    res = transport.run([python_bin, "manage.py", "check"], env=env, cwd=app_dir)
    if res.succeeded:
        if "System check identified no issues" in res.output:
            results.append(TestResult("Django system check", "pass"))
        else:
            results.append(TestResult("Django system check", "warn", res.output))
    else:
        results.append(TestResult("Django system check", "fail", res.output))

    # manage.py showmigrations
    res = transport.run([python_bin, "manage.py", "showmigrations"], env=env, cwd=app_dir)
    if res.succeeded:
        if "[ ]" in res.output:
            results.append(TestResult("Unapplied migrations", "fail", "One or more migrations have not been applied"))
        else:
            results.append(TestResult("Migrations", "pass", "All migrations applied"))
    else:
        results.append(TestResult("Show migrations failed", "fail", res.output))

    return results

def run_all_tests(transport: Transport, state: ManagerState) -> List[List[TestResult]]:
    return [
        test_app_files(transport, state),
        test_django_checks(transport, state),
        # ... other groups T3-T7
    ]

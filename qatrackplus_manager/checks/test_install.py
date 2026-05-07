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

def test_diagnostics(transport: Transport, state: ManagerState) -> List[TestResult]:
    results = []
    results.append(TestResult("Detected Major Version", "info", str(state.qatrack_version_major)))
    results.append(TestResult("Settings Module", "info", state.django_settings or "None"))
    results.append(TestResult("Local Settings Path", "info", state.local_settings_file or "None"))
    return results

def test_web_accessibility(transport: Transport, state: ManagerState) -> List[TestResult]:
    results = []
    
    # Try localhost
    # -L to follow redirects (e.g. to /accounts/login/)
    # -I for just the header
    res = transport.run(["curl", "-s", "-L", "-I", "http://localhost"])
    
    if res.succeeded:
        lines = res.output.splitlines()
        status_line = lines[0] if lines else "No output"
        
        # Check Server header to see if it's actually our stack
        server_header = ""
        for line in lines:
            if line.lower().startswith("server:"):
                server_header = line
                break
        
        is_qatrack = "gunicorn" in server_header.lower() or "nginx" in server_header.lower()
        
        if "200" in status_line or "301" in status_line or "302" in status_line:
            if not is_qatrack and server_header:
                results.append(TestResult(
                    "Web Access (Localhost)", 
                    "warn", 
                    f"Connected, but response is from '{server_header.split(':')[-1].strip()}' not QATrack+. Possible port conflict."
                ))
            else:
                results.append(TestResult("Web Access (Localhost)", "pass", status_line))
        elif "405" in status_line:
             results.append(TestResult(
                 "Web Access (Localhost)", 
                 "fail", 
                 f"405 Method Not Allowed. Intercepted by '{server_header.split(':')[-1].strip()}'. Check Apache/Nginx config."
             ))
        else:
            results.append(TestResult("Web Access (Localhost)", "fail", f"Unexpected response: {status_line}"))
    else:
        results.append(TestResult("Web Access (Localhost)", "fail", "Connection failed or timeout. Check Nginx/Gunicorn."))
        
    return results


def run_all_tests(transport: Transport, state: ManagerState) -> List[List[TestResult]]:
    return [
        test_diagnostics(transport, state),
        test_app_files(transport, state),
        test_django_checks(transport, state),
        test_web_accessibility(transport, state),
    ]



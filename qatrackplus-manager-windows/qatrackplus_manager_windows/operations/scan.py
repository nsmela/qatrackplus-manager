from ..transport.powershell import PowerShellTransport
from typing import Dict, Any

def run_system_scan(transport: PowerShellTransport) -> Dict[str, Any]:
    """Scans the system for QATrack+ prerequisites."""
    results = {}
    
    # 1. Python Check
    try:
        import sys
        # Default to current interpreter info
        results['python'] = {
            "status": "Found",
            "type": "Active",
            "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "path": sys.executable
        }

        # Check for global 'python'
        py_path_check = transport.run("(Get-Command python -ErrorAction SilentlyContinue).Source", log_errors=False).stdout.strip()
        if py_path_check and "WindowsApps" not in py_path_check:
            py_ver = transport.run("python --version", log_errors=False).stdout.strip()
            results['python'] = {
                "status": "Found",
                "type": "Global",
                "version": py_ver.replace("Python ", ""),
                "path": py_path_check
            }
        else:
            # Check for local install
            local_py = transport.run("Get-ChildItem -Path \"$env:LOCALAPPDATA\Programs\Python\Python*\python.exe\" -ErrorAction SilentlyContinue | Select-Object -First 1 | Select-Object -ExpandProperty FullName", log_errors=False).stdout.strip()
            if local_py:
                # Get version of the local py
                try:
                    ver_cmd = transport.run(f"& '{local_py}' --version", log_errors=False).stdout.strip()
                    results['python'] = {
                        "status": "Found",
                        "type": "Local",
                        "version": ver_cmd.replace("Python ", ""),
                        "path": local_py
                    }
                except:
                    results['python']['type'] = "Local (Error checking version)"
    except Exception as e:
        results['python'] = {"status": "Error", "details": str(e)}
        
    # 2. Git Check
    try:
        git_ver = transport.run("git --version").stdout.strip()
        results['git'] = {"status": "Found", "version": git_ver}
    except Exception:
        results['git'] = {"status": "Missing", "version": None}
        
    # 3. SQL Server (Check for instances and versions)
    try:
        # Get all services starting with MSSQL
        sql_services = transport.run("Get-Service -Name MSSQL* -ErrorAction SilentlyContinue | Select-Object Name, Status, DisplayName").stdout.strip()
        if sql_services:
            results['sql_server'] = {"status": "Found", "instances": []}
            # Try to get version info using sqlcmd if available
            for line in sql_services.splitlines():
                if not line.strip(): continue
                # Basic parsing (PowerShell output can be messy)
                parts = line.split()
                if len(parts) >= 2:
                    svc_name = parts[0]
                    svc_status = parts[1]
                    instance_name = svc_name.replace("MSSQL$", "") if "$" in svc_name else "Default"
                    
                    version = "Unknown"
                    if svc_status == "Running":
                        try:
                            # Try to get version via sqlcmd
                            # -E for trusted, -S for server/instance
                            server_str = "." if instance_name == "Default" else f".\\{instance_name}"
                            ver_check = transport.run(f"sqlcmd -S {server_str} -E -Q \"SELECT @@VERSION\" -h -1 -t 2", log_errors=False).stdout.strip()
                            if ver_check:
                                version = ver_check.splitlines()[0][:50] + "..."
                        except:
                            pass
                            
                    results['sql_server']['instances'].append({
                        "name": instance_name,
                        "service": svc_name,
                        "status": svc_status,
                        "version": version
                    })
        else:
            results['sql_server'] = {"status": "Missing", "details": "No MSSQL services found"}
    except Exception as e:
        results['sql_server'] = {"status": "Error", "details": str(e)}

    # 4. ODBC Driver Check
    try:
        odbc_check = transport.run("Get-OdbcDriver -Name 'ODBC Driver * for SQL Server' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name", log_errors=False).stdout.strip()
        if odbc_check:
            # Get the unique names
            drivers = list(set([d.strip() for d in odbc_check.splitlines() if d.strip()]))
            results['odbc_driver'] = {"status": "Found", "drivers": drivers}
        else:
            results['odbc_driver'] = {"status": "Missing", "details": "Microsoft ODBC Driver for SQL Server not found"}
    except Exception:
        results['odbc_driver'] = {"status": "Missing"}

    # 5. IIS Check
    try:
        iis_status = transport.get_service_status("W3SVC")
        if iis_status != "NotFound":
            # Check for specific modules (URL Rewrite and ARR)
            rewrite_found = transport.file_exists("C:\\Windows\\System32\\inetsrv\\rewrite.dll")
            arr_found = transport.file_exists("C:\\Windows\\System32\\inetsrv\\requestRestriction.dll") # Part of ARR
            
            results['iis'] = {
                "status": iis_status,
                "service": "W3SVC",
                "modules": {
                    "URL Rewrite": "Installed" if rewrite_found else "Missing",
                    "ARR": "Installed" if arr_found else "Missing"
                }
            }
            # Try to get IIS version
            try:
                ver_check = transport.run("(Get-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\InetStp\\').VersionString", log_errors=False).stdout.strip()
                results['iis']['version'] = ver_check
            except:
                results['iis']['version'] = "Unknown"
        else:
            results['iis'] = {"status": "Missing", "details": "IIS (W3SVC) not found"}
    except Exception as e:
        results['iis'] = {"status": "Error", "details": str(e)}
        
    # 6. Python Packages Check
    try:
        packages = ['django', 'cherrypy']
        pkg_results = {}
        for pkg in packages:
            # Check via pip
            check = transport.run(f"python -m pip show {pkg}", log_errors=False).stdout.strip()
            if check:
                # Extract version
                for line in check.splitlines():
                    if line.startswith("Version:"):
                        pkg_results[pkg] = line.replace("Version:", "").strip()
                        break
            else:
                pkg_results[pkg] = "Missing"
        results['packages'] = pkg_results
    except Exception:
        results['packages'] = {}
        
    # 7. Chrome Check (for PDF reports)
    chrome_paths = [
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
    ]
    chrome_found = any(transport.file_exists(p) for p in chrome_paths)
    results['chrome'] = {"status": "Found" if chrome_found else "Missing"}
    
    return results

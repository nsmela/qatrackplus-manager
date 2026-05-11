from ..transport.powershell import PowerShellTransport
import logging
from typing import Dict, Any

def install_iis(transport: PowerShellTransport) -> Dict[str, Any]:
    """Enables IIS and required sub-features."""
    features = [
        "IIS-WebServerRole",
        "IIS-WebServer",
        "IIS-CommonHttpFeatures",
        "IIS-StaticContent",
        "IIS-DefaultDocument",
        "IIS-DirectoryBrowsing",
        "IIS-HttpErrors",
        "IIS-HttpRedirection",
        "IIS-ApplicationDevelopment",
        "IIS-CGI",
        "IIS-ISAPIExtensions",
        "IIS-ISAPIFilter",
        "IIS-HealthAndDiagnostics",
        "IIS-HttpLogging",
        "IIS-RequestMonitor",
        "IIS-Security",
        "IIS-BasicAuthentication",
        "IIS-WindowsAuthentication",
        "IIS-RequestFiltering",
        "IIS-WebServerManagementTools",
        "IIS-ManagementConsole"
    ]
    
    logging.info(f"Starting IIS installation. Features: {len(features)}")
    try:
        # We use a loop or join them. Join is faster.
        # DISM or Enable-WindowsOptionalFeature
        # Enable-WindowsOptionalFeature is more robust in PS
        cmd = f"Enable-WindowsOptionalFeature -Online -FeatureName {','.join(features)} -All -NoRestart"
        transport.run(cmd, capture_output=False)
        logging.info("IIS features enabled successfully.")
        return {"status": "Success", "message": "IIS features enabled."}
    except Exception as e:
        logging.error(f"Failed to install IIS: {e}")
        return {"status": "Failed", "message": str(e)}

def install_iis_modules(transport: PowerShellTransport) -> Dict[str, Any]:
    """Installs URL Rewrite and ARR modules via winget."""
    results = {}
    
    # 1. URL Rewrite
    logging.info("Attempting to install URL Rewrite module...")
    try:
        transport.run("winget install --id Microsoft.IIS.URLRewrite --source winget --exact --silent --accept-package-agreements --accept-source-agreements", capture_output=False)
        results['URL Rewrite'] = "Success"
        logging.info("URL Rewrite module installed successfully.")
    except Exception as e:
        results['URL Rewrite'] = f"Failed: {str(e)}"
        logging.error(f"Failed to install URL Rewrite: {e}")
        
    # 2. ARR (Application Request Routing)
    logging.info("Attempting to install ARR module...")
    try:
        # Note: ARR depends on Web Farm Framework, but winget usually handles it or ARR installer does.
        transport.run("winget install --id Microsoft.IIS.ApplicationRequestRouting --source winget --exact --silent --accept-package-agreements --accept-source-agreements", capture_output=False)
        results['ARR'] = "Success"
        logging.info("ARR module installed successfully.")
    except Exception as e:
        results['ARR'] = f"Failed: {str(e)}"
        logging.error(f"Failed to install ARR: {e}")
        
    return results

def manage_iis_service(transport: PowerShellTransport, action: str) -> Dict[str, Any]:
    """Manages the W3SVC service (IIS)."""
    if action.lower() not in ["start", "stop", "restart"]:
        return {"status": "Error", "message": "Invalid action"}
        
    logging.info(f"Performing action '{action}' on W3SVC service.")
    try:
        transport.run(f"{action.capitalize()}-Service -Name W3SVC")
        logging.info(f"IIS service {action}ed successfully.")
        return {"status": "Success", "message": f"IIS service {action}ed."}
    except Exception as e:
        logging.error(f"Failed to {action} IIS service: {e}")
        return {"status": "Failed", "message": str(e)}

def get_iis_status(transport: PowerShellTransport) -> Dict[str, Any]:
    """Returns a summary of IIS status."""
    from .scan import run_system_scan
    scan = run_system_scan(transport)
    return scan.get('iis', {"status": "Unknown"})

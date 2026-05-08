from ..transport.powershell import PowerShellTransport
from typing import Dict, Any

def test_db_connection(transport: PowerShellTransport, db_type: str, config: Dict[str, str]) -> Dict[str, Any]:
    """Tests connection to various database types."""
    
    if db_type == "sqlite":
        path = config.get("path")
        if transport.file_exists(path):
            return {"status": "Success", "message": f"SQLite database found at {path}"}
        else:
            return {"status": "Failed", "message": f"SQLite database not found at {path}"}
            
    elif db_type == "mssql":
        # Using sqlcmd or Invoke-SqlCmd
        server = config.get("server", "localhost")
        db_name = config.get("name")
        user = config.get("user")
        password = config.get("password")
        
        auth = f"-U {user} -P '{password}'" if user else "-E" # -E for Trusted Connection
        cmd = f"sqlcmd -S {server} -d {db_name} {auth} -Q 'SELECT 1' -t 5"
        
        try:
            transport.run(cmd)
            return {"status": "Success", "message": f"Connected to SQL Server {server}"}
        except Exception as e:
            return {"status": "Failed", "message": str(e)}
            
    elif db_type == "postgresql":
        # Assuming psql is in path
        host = config.get("host", "localhost")
        user = config.get("user")
        db_name = config.get("name")
        
        # We might need to set PGPASSWORD env var for the command
        cmd = f"$env:PGPASSWORD='{config.get('password')}'; psql -h {host} -U {user} -d {db_name} -c 'SELECT 1'"
        try:
            transport.run(cmd)
            return {"status": "Success", "message": f"Connected to PostgreSQL {host}"}
        except Exception as e:
            return {"status": "Failed", "message": str(e)}

    elif db_type == "mysql":
        # Assuming mysql is in path
        host = config.get("host", "localhost")
        user = config.get("user")
        password = config.get("password")
        db_name = config.get("name")
        
        cmd = f"mysql -h {host} -u {user} -p'{password}' -e 'SELECT 1' {db_name}"
        try:
            transport.run(cmd)
            return {"status": "Success", "message": f"Connected to MySQL {host}"}
        except Exception as e:
            return {"status": "Failed", "message": str(e)}
            
def create_db_backup(transport: PowerShellTransport, db_type: str, config: Dict[str, str], backup_path: str) -> Dict[str, Any]:
    """Creates a backup of the database."""
    if db_type == "mssql":
        server = config.get("server", "localhost")
        db_name = config.get("name")
        user = config.get("user")
        password = config.get("password")
        
        auth = f"-U {user} -P '{password}'" if user else "-E"
        # We need to ensure the SQL Server service account has access to the backup_path
        cmd = f"sqlcmd -S {server} {auth} -Q \"BACKUP DATABASE [{db_name}] TO DISK = '{backup_path}' WITH FORMAT, MEDIANAME = 'QATrackPlusBackup', NAME = 'Full Backup of {db_name}'\""
        
        try:
            transport.run(cmd)
            return {"status": "Success", "message": f"Backup created at {backup_path}"}
        except Exception as e:
            return {"status": "Failed", "message": str(e)}
    
    return {"status": "Error", "message": f"Backup not yet implemented for {db_type}"}

def restore_db_backup(transport: PowerShellTransport, db_type: str, config: Dict[str, str], backup_path: str) -> Dict[str, Any]:
    """Restores a database from a backup."""
    if db_type == "mssql":
        server = config.get("server", "localhost")
        db_name = config.get("name")
        user = config.get("user")
        password = config.get("password")
        
        auth = f"-U {user} -P '{password}'" if user else "-E"
        # Restoring requires closing other connections
        cmd = f"sqlcmd -S {server} {auth} -Q \"ALTER DATABASE [{db_name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; RESTORE DATABASE [{db_name}] FROM DISK = '{backup_path}' WITH REPLACE; ALTER DATABASE [{db_name}] SET MULTI_USER;\""
        
        try:
            transport.run(cmd)
            return {"status": "Success", "message": f"Database {db_name} restored from {backup_path}"}
        except Exception as e:
            return {"status": "Failed", "message": str(e)}

def create_full_backup(transport: PowerShellTransport, config: Dict[str, str], backup_dir: str) -> Dict[str, Any]:
    """Creates a full backup (DB + Media files)."""
    db_type = config.get("db_type", "").lower()
    install_path = config.get("install_path", "")
    
    # 1. DB Backup
    db_backup_file = os.path.join(backup_dir, f"database_{db_type}.bak")
    db_res = create_db_backup(transport, db_type, {
        "server": config.get("db_server"),
        "name": config.get("db_name"),
        "user": config.get("db_user"),
        "password": config.get("password")
    }, db_backup_file)
    
    if db_res['status'] != "Success":
        return db_res
        
    # 2. Media Backup
    media_path = os.path.join(install_path, "qatrack", "media")
    media_backup_zip = os.path.join(backup_dir, "uploaded_files.zip")
    
    console_print = transport.run(f"if (Test-Path '{media_path}') {{ Compress-Archive -Path '{media_path}' -DestinationPath '{media_backup_zip}' -Force; echo 'Success' }} else {{ echo 'NotFound' }}", log_errors=False).stdout.strip()
    
    if console_print == "Success":
        return {"status": "Success", "message": f"Full backup created in {backup_dir}. Includes database and uploaded files."}
    elif console_print == "NotFound":
        return {"status": "Partial", "message": f"Database backed up, but media folder not found at {media_path}."}
    else:
        return {"status": "Partial", "message": f"Database backed up, but failed to zip media folder."}

def create_portable_backup(transport: PowerShellTransport, config: Dict[str, str], backup_dir: str) -> Dict[str, Any]:
    """Creates a portable JSON backup using Django's dumpdata."""
    install_path = config.get("install_path", "")
    venv_python = os.path.join(install_path, ".venv", "Scripts", "python.exe")
    
    if not transport.file_exists(venv_python):
        # Fallback to global python if venv not found
        venv_python = "python"

    # 1. Dump Database to JSON
    json_backup = os.path.join(backup_dir, "database_portable.json")
    # We exclude certain system tables that can cause conflicts on restore
    dump_cmd = f"& '{venv_python}' manage.py dumpdata --exclude auth.permission --exclude contenttypes --indent 2 --output '{json_backup}'"
    
    try:
        transport.run(dump_cmd, cwd=install_path)
    except Exception as e:
        return {"status": "Failed", "message": f"Failed to dump database: {str(e)}"}

    # 2. Media Backup (same as full backup)
    media_path = os.path.join(install_path, "qatrack", "media")
    media_backup_zip = os.path.join(backup_dir, "uploaded_files.zip")
    transport.run(f"if (Test-Path '{media_path}') {{ Compress-Archive -Path '{media_path}' -DestinationPath '{media_backup_zip}' -Force }}", log_errors=False)

    return {"status": "Success", "message": f"Portable backup created in {backup_dir}. Use 'loaddata' to restore on any OS."}

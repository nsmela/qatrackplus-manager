from __future__ import annotations
import os
import time
from typing import Optional
from ..transport.base import Transport
from ..exceptions import DatabaseError

def backup(
    transport: Transport,
    app_dir: str,
    backup_dir: str,
    db_type: str,
    db_config: dict,
    label: str = ""
) -> str:
    """
    Perform a backup of the QA Track Plus installation.
    Returns the path to the created archive.
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    name = f"qatrack_backup_{timestamp}"
    if label:
        name = f"{name}_{label}"
    
    tmp_dir = f"/tmp/{name}"
    transport.make_dirs(tmp_dir)
    transport.make_dirs(backup_dir)

    # 1. DB Dump
    if db_type == 'postgresql':
        env = {'PGPASSWORD': db_config.get('password', '')}
        dump_file = f"{tmp_dir}/db.dump"
        # We need to write to file. Since transport.run doesn't support redirects easily,
        # we can use a shell command or implement redirection.
        cmd = [
            "pg_dump", "-Fc",
            "-h", db_config.get('host', 'localhost'),
            "-p", db_config.get('port', '5432'),
            "-U", db_config.get('user', 'qatrack'),
            "-f", dump_file,
            db_config.get('name', 'qatrackplus')
        ]
        res = transport.run(cmd, env=env)
        if not res.succeeded:
            raise DatabaseError(f"pg_dump failed: {res.stderr}")

    elif db_type == 'mysql':
        dump_file = f"{tmp_dir}/db.sql"
        cmd = [
            "mysqldump", "--single-transaction",
            "-h", db_config.get('host', 'localhost'),
            "-P", db_config.get('port', '3306'),
            "-u", db_config.get('user', 'qatrack'),
            f"-p{db_config.get('password', '')}",
            f"--result-file={dump_file}",
            db_config.get('name', 'qatrackplus')
        ]
        res = transport.run(cmd)
        if not res.succeeded:
            raise DatabaseError(f"mysqldump failed: {res.stderr}")

    elif db_type == 'sqlite':
        sqlite_file = os.path.join(app_dir, "qatrackplus.sqlite3")
        if transport.file_exists(sqlite_file):
            transport.run(["cp", sqlite_file, f"{tmp_dir}/db.sqlite3"])
    
    # 2. Write db_type file
    transport.write_file(f"{tmp_dir}/db_type", db_type)

    # 3. Media files
    media_dir = os.path.join(app_dir, "media")
    if transport.dir_exists(media_dir):
        transport.run(["tar", "-czf", f"{tmp_dir}/media.tar.gz", "-C", media_dir, "."])

    # 4. local_settings.py
    # We'd need the path from state, but for now let's assume common paths
    # or just try both.
    ls_paths = [
        os.path.join(app_dir, "qatrack/local_settings.py"),
        os.path.join(app_dir, "qatrack/settings/local_settings.py")
    ]
    for p in ls_paths:
        if transport.file_exists(p):
            transport.run(["cp", p, f"{tmp_dir}/local_settings.py"])
            break

    # 5. Final archive
    archive_path = os.path.join(backup_dir, f"{name}.tar.gz")
    transport.run(["tar", "-czf", archive_path, "-C", tmp_dir, "."])
    
    # Cleanup
    transport.run(["rm", "-rf", tmp_dir])
    
    return archive_path

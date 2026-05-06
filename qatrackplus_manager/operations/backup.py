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
    from ..services.database import get_database_engine
    engine = get_database_engine(transport, db_type, db_config)
    
    # Engine specific dump file name/path
    dump_filename = "db.dump" if db_type == 'postgresql' else ("db.sql" if db_type == 'mysql' else "db.sqlite3")
    dump_file = f"{tmp_dir}/{dump_filename}"
    
    res = engine.dump(dump_file)
    if not res.succeeded:
        raise DatabaseError(f"{db_type} dump failed: {res.stderr}")
    
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

from __future__ import annotations
import os
from ..transport.base import Transport
from ..exceptions import DatabaseError

def restore(
    transport: Transport,
    archive_path: str,
    app_dir: str,
    db_config: dict
) -> None:
    """
    Restore from a backup archive.
    """
    tmp_dir = "/tmp/qatrack_restore"
    transport.run(["rm", "-rf", tmp_dir])
    transport.make_dirs(tmp_dir)
    
    # 1. Extract
    transport.run(["tar", "-xzf", archive_path, "-C", tmp_dir])
    
    # 2. Read db_type
    db_type = transport.read_file(f"{tmp_dir}/db_type").strip()
    
    # 3. Restore DB
    from ..services.database import get_database_engine
    engine = get_database_engine(transport, db_type, db_config)
    
    # Engine specific dump file name/path
    dump_filename = "db.dump" if db_type == 'postgresql' else ("db.sql" if db_type == 'mysql' else "db.sqlite3")
    dump_file = f"{tmp_dir}/{dump_filename}"
    
    res = engine.restore(dump_file)
    if not res.succeeded:
        raise DatabaseError(f"{db_type} restore failed: {res.stderr}")

    # 4. Restore media
    media_tar = f"{tmp_dir}/media.tar.gz"
    if transport.file_exists(media_tar):
        media_dir = os.path.join(app_dir, "media")
        transport.make_dirs(media_dir)
        transport.run(["tar", "-xzf", media_tar, "-C", media_dir])

    # 5. Restore local_settings.py
    ls_backup = f"{tmp_dir}/local_settings.py"
    if transport.file_exists(ls_backup):
        # We need to find where it should go now
        from ..config.detect import detect_qatrack_version
        _, target_path, _ = detect_qatrack_version(transport, app_dir)
        transport.run(["cp", ls_backup, target_path])

    # Cleanup
    transport.run(["rm", "-rf", tmp_dir])

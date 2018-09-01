def apply_migration_0(conn):
    cur = conn.cursor()
    init_required = False

    cur.execute('PRAGMA schema_version')
    schema_version = int(cur.fetchone()[0])
    if schema_version == 0:
        init_required = True

    if init_required:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL,
                value VARCHAR(255) NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS uidx_settings_name ON settings(name);

            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_id INTEGER NOT NULL,
                media_id INTEGER NOT NULL,
                title varchar(255) not null,
                downloaded tinyint(1) not null default 0,
                filename varchar(255) not null,
                filesize integer not null default 0,
                media_type VARCHAR(50) not null
            );
            CREATE UNIQUE INDEX IF NOT EXISTS uidx_items_sync_id_media_id ON items(sync_id, media_id);
            CREATE INDEX IF NOT EXISTS idx_items_sync_id ON items(sync_id);
            CREATE INDEX IF NOT EXISTS idx_items_downloaded ON items(downloaded);

            CREATE TABLE IF NOT EXISTS syncs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id varchar(255) not null,
                sync_id INTEGER NOT NULL,
                title varchar(255) not null,
                version integer not null default 1
            );
            CREATE UNIQUE INDEX IF NOT EXISTS uidx_syncs_machine_id_media_id ON syncs(machine_id, sync_id);
        """)
    else:
        conn.execute('ALTER TABLE items ADD COLUMN media_type VARCHAR(50)')


def apply_migration_1(conn):
    conn.executescript("""
        DROP INDEX idx_items_downloaded;
        CREATE INDEX IF NOT EXISTS idx_items_downloaded_media_type ON items(downloaded, media_type)
    """)


def apply_migration_2(conn):
    from .mobile_sync import MobileSync

    conn.executescript("""
        CREATE TABLE tmp_syncs AS SELECT * FROM syncs;
        DROP TABLE syncs;
        CREATE TABLE IF NOT EXISTS syncs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id varchar(255) not null,
            sync_type VARCHAR(50) NOT NULL,
            sync_id VARCHAR(255) NOT NULL,
            title varchar(255) not null,
            version integer not null default 1
        );
        INSERT INTO syncs SELECT id, machine_id, '%s', sync_id, title, version FROM tmp_syncs;
        CREATE UNIQUE INDEX uidx_syncs_machine_id_sync_type_sync_id ON syncs(machine_id, sync_type, sync_id);
        DROP TABLE tmp_syncs;
    """ % (MobileSync.name, ))

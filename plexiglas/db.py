import sqlite3
from contextlib import contextmanager
from uuid import uuid4

from plexapi.base import Playable
from plexapi.sync import SyncItem


@contextmanager
def _get_db():
    conn = sqlite3.connect('.plexiglas.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row

    _init_db(conn)
    yield conn

    conn.close()


def _init_db(conn):
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
        filesize integer not null default 0
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
    conn.commit()


def get_client_uuid():
    with _get_db() as conn:
        cur = conn.cursor()
        cur.execute('SELECT value FROM settings WHERE name = ?', ('client_uuid', ))
        uuid = cur.fetchone()

        if uuid:
            uuid = uuid[0]
        else:
            uuid = str(uuid4()).upper()
            cur.execute('INSERT INTO settings (name, value) VALUES (?, ?)', ('client_uuid', uuid))
            conn.commit()

        return uuid


def mark_downloaded(item: SyncItem, media: Playable, filesize: int, filename=None):
    with _get_db() as conn:
        cur = conn.cursor()
        cur.execute('INSERT OR IGNORE INTO syncs (machine_id, sync_id, title) VALUES (?, ?, ?)',
                    (item.machineIdentifier, item.id, item.title))

        cur.execute('SELECT id FROM syncs WHERE machine_id = ? AND sync_id = ?', (item.machineIdentifier, item.id))
        sync_id = cur.fetchone()[0]

        cur.execute('UPDATE syncs SET title = ?, version = ? WHERE id = ?', (item.title, item.version, sync_id))

        cur.execute('INSERT OR IGNORE INTO items (sync_id, media_id, title, filename) VALUES (?, ?, "", "")',
                    (sync_id, media.ratingKey))
        cur.execute('SELECT id FROM items WHERE sync_id = ? and media_id = ?', (sync_id, media.ratingKey))
        item_id = cur.fetchone()[0]

        cur.execute('UPDATE items SET downloaded = 1, title = ?, filename = ?, filesize = ? WHERE id = ?',
                    (media.title, filename, filesize, item_id))

        conn.commit()


def remove_downloaded(item_id: int=None, machine_id: str=None, sync_id: int=None, media_id: int=None):
    with _get_db() as conn:
        if item_id:
            conn.execute('DELETE FROM items WHERE id = ?', (item_id, ))
        else:
            conn.execute('DELETE FROM items WHERE media_id = ? AND '
                         'sync_id = (SELECT id FROM syncs WHERE machine_id = ? AND sync_id = ?)', (media_id, machine_id,
                                                                                                   sync_id))
        conn.commit()


def get_all_downloaded():
    with _get_db() as conn:
        cur = conn.cursor()
        cur.execute('SELECT i.id, s.machine_id, s.sync_id, i.media_id, s.title, i.filename FROM syncs s '
                    'JOIN items i ON i.sync_id = s.id WHERE i.downloaded = 1')
        return cur.fetchall()


def get_downloaded_size():
    with _get_db() as conn:
        cur = conn.cursor()
        cur.execute('SELECT SUM(filesize) FROM items i WHERE i.downloaded = 1')
        return cur.fetchone()[0]

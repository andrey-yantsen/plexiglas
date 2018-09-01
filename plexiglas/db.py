import sqlite3
from contextlib import contextmanager
from uuid import uuid4
from . import log, db_migrations

CURRENT_VERSION = 3
_skip_migrations = False


@contextmanager
def _get_db():
    conn = sqlite3.connect('.plexiglas.db', detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row

    apply_migrations(conn)
    yield conn

    conn.close()


def apply_migrations(conn):
    global _skip_migrations

    if _skip_migrations:
        return

    cur = conn.cursor()
    cur.execute('PRAGMA user_version')
    db_version = int(cur.fetchone()[0])

    for ver in range(db_version, CURRENT_VERSION):
        log.debug('Applying migration from ver#%d', ver)
        method_name = 'apply_migration_%d' % ver
        getattr(db_migrations, method_name)(conn)

    if db_version != CURRENT_VERSION:
        cur.execute('PRAGMA user_version = ' + str(int(CURRENT_VERSION)))

    conn.commit()

    _skip_migrations = True


def get_param(name, default=None):
    with _get_db() as conn:
        cur = conn.cursor()
        cur.execute('SELECT value FROM settings WHERE name = ?', (name, ))
        ret = cur.fetchone()
        if ret:
            return ret[0]
        else:
            return default


def set_param(name, value):
    with _get_db() as conn:
        conn.execute('INSERT OR IGNORE INTO settings (name, value) VALUES (?, "")', (name, ))
        conn.execute('UPDATE settings SET value = ? WHERE name = ?', (str(value), name))
        conn.commit()


def get_client_uuid():
    uuid = get_param('client_uuid')

    if uuid is None:
        uuid = str(uuid4()).upper()
        set_param('client_uuid', uuid)

    return uuid


def mark_downloaded(machine_id, sync_type, sync_id, sync_title, media, filesize, filename, sync_version=1):
    with _get_db() as conn:
        log.debug('Marking as downloaded item#%s, media#%d', sync_id, media.ratingKey)
        cur = conn.cursor()
        cur.execute('INSERT OR IGNORE INTO syncs (machine_id, sync_type, sync_id, title) VALUES (?, ?, ?, ?)',
                    (machine_id, sync_type, sync_id, sync_title))

        cur.execute('SELECT id FROM syncs WHERE machine_id = ? AND sync_type = ? AND sync_id = ?', (machine_id,
                                                                                                    sync_type, sync_id))
        sync_id = cur.fetchone()[0]
        log.debug('SyncItem id in internal db %d', sync_id)

        cur.execute('UPDATE syncs SET title = ?, version = ? WHERE id = ?', (sync_title, sync_version, sync_id))

        cur.execute('INSERT OR IGNORE INTO items (sync_id, media_id, title, filename, media_type) VALUES '
                    '(?, ?, "", "", "")',
                    (sync_id, media.ratingKey))
        cur.execute('SELECT id FROM items WHERE sync_id = ? and media_id = ?', (sync_id, media.ratingKey))
        item_id = cur.fetchone()[0]
        log.debug('Media id in internal db %d', sync_id)

        cur.execute('UPDATE items SET downloaded = 1, title = ?, filename = ?, filesize = ?, media_type = ? '
                    'WHERE id = ?',
                    (media.title, filename, filesize, media.TYPE, item_id))

        conn.commit()


def remove_downloaded(machine_id, sync_type, sync_id, media_id):
    with _get_db() as conn:
        conn.execute('DELETE FROM items WHERE media_id = ? AND '
                     'sync_id = (SELECT id FROM syncs WHERE machine_id = ? AND sync_type = ? AND sync_id = ?)',
                     (media_id, machine_id, sync_type, sync_id))
        conn.commit()


def get_all_downloaded(sync_type):
    with _get_db() as conn:
        cur = conn.cursor()
        cur.execute('SELECT i.id, s.machine_id, s.sync_type, s.sync_id, i.media_id, s.title as sync_title, '
                    'i.media_type, i.filename as media_filename '
                    'FROM syncs s '
                    'JOIN items i ON i.sync_id = s.id '
                    'WHERE i.downloaded = 1 AND s.sync_type = ?', (sync_type, ))
        return cur.fetchall()


def get_downloaded_for_sync(machine_id, sync_type, sync_id):
    if type(sync_id) is not list:
        sync_id = [sync_id]

    with _get_db() as conn:
        cur = conn.cursor()
        params = (machine_id, sync_type) + tuple(sync_id)
        cur.execute('SELECT i.id, s.machine_id, s.sync_id, i.media_id, s.title, i.media_type, i.filename FROM syncs s '
                    'JOIN items i ON i.sync_id = s.id '
                    'WHERE i.downloaded = 1 AND s.machine_id = ? AND s.sync_type = ? '
                    'AND s.sync_id IN (%s)' % (','.join('?'*len(sync_id)), ), params)
        return cur.fetchall()


def get_downloaded_for_sync_type(machine_id, sync_type):
    with _get_db() as conn:
        cur = conn.cursor()
        cur.execute('SELECT i.id, s.machine_id, s.sync_id, i.media_id, s.title, i.media_type, i.filename FROM syncs s '
                    'JOIN items i ON i.sync_id = s.id '
                    'WHERE i.downloaded = 1 AND s.machine_id = ? AND s.sync_type = ?', (machine_id, sync_type))
        return cur.fetchall()


def get_downloaded_size(media_type=None):
    with _get_db() as conn:
        cur = conn.cursor()
        if media_type:
            cur.execute('SELECT SUM(filesize) FROM items i WHERE i.downloaded = 1 AND media_type = ?', (media_type, ))
        else:
            cur.execute('SELECT SUM(filesize) FROM items i WHERE i.downloaded = 1')
        return cur.fetchone()[0] or 0

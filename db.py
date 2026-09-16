"""Warstwa bazy danych: SQLite (domyslnie) albo PostgreSQL (gdy DATABASE_URL).

Render (darmowy) ma ulotny dysk, dlatego na produkcji uzywamy zewnetrznego
PostgreSQL-a (np. darmowy Neon). Lokalnie dziala SQLite. Kod aplikacji jest
identyczny dla obu silnikow: wrapper tlumaczy placeholdery `?` -> `%s`,
a roznice DDL sa zamkniete w dwoch schematach ponizej.
"""
import os
import sqlite3
from flask import g

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_PG = bool(DATABASE_URL)
DB_PATH = os.environ.get(
    "SPORT_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "sport.db"),
)

TABLES = ["classes", "users", "settings", "connections", "activities", "bonuses",
          "missions", "user_missions", "achievements", "user_achievements",
          "announcements", "announcement_joins", "likes", "comments",
          "contests", "follows", "pending_activities"]

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS classes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'uczen',
    class_id INTEGER REFERENCES classes(id),
    avatar_base TEXT DEFAULT 'biegacz',
    avatar_items TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS settings(
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS connections(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    provider TEXT NOT NULL,
    connected INTEGER DEFAULT 1,
    access_token TEXT,
    refresh_token TEXT,
    expires_at INTEGER,
    athlete_id TEXT,
    athlete_name TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, provider)
);
CREATE TABLE IF NOT EXISTS activities(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    provider TEXT DEFAULT 'manual',
    type TEXT NOT NULL,
    distance_km REAL NOT NULL,
    duration_min INTEGER DEFAULT 0,
    date TEXT NOT NULL,
    points REAL NOT NULL,
    external_id TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS bonuses(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    week_key TEXT NOT NULL,
    days_active INTEGER NOT NULL,
    bonus REAL NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, week_key)
);
CREATE TABLE IF NOT EXISTS missions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    kind TEXT NOT NULL DEFAULT 'dzienna',
    cond_type TEXT NOT NULL,
    cond_sport TEXT DEFAULT 'any',
    cond_value REAL DEFAULT 0,
    cond_period TEXT DEFAULT 'day',
    points REAL DEFAULT 0,
    badge_icon TEXT DEFAULT '',
    avatar_item TEXT DEFAULT '',
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS user_missions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    mission_id INTEGER NOT NULL,
    period_key TEXT NOT NULL,
    progress REAL DEFAULT 0,
    completed INTEGER DEFAULT 0,
    completed_at TEXT DEFAULT '',
    UNIQUE(user_id, mission_id, period_key)
);
CREATE TABLE IF NOT EXISTS achievements(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    category TEXT NOT NULL,
    icon TEXT NOT NULL,
    color TEXT NOT NULL,
    cond_type TEXT NOT NULL,
    cond_sport TEXT DEFAULT 'any',
    cond_value REAL DEFAULT 0,
    reward_points REAL DEFAULT 0,
    reward_item TEXT DEFAULT '',
    rank TEXT DEFAULT 'latwy'
);
CREATE TABLE IF NOT EXISTS user_achievements(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    ach_id INTEGER NOT NULL,
    unlocked_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, ach_id)
);
CREATE TABLE IF NOT EXISTS announcements(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    event_date TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS announcement_joins(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    announcement_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    UNIQUE(announcement_id, user_id)
);
CREATE TABLE IF NOT EXISTS likes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    UNIQUE(activity_id, user_id)
);
CREATE TABLE IF NOT EXISTS comments(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS contests(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    status TEXT DEFAULT 'aktywny',
    winner_id INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS follows(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    follower_id INTEGER NOT NULL,
    followed_id INTEGER NOT NULL,
    UNIQUE(follower_id, followed_id)
);
CREATE INDEX IF NOT EXISTS idx_act_user_date ON activities(user_id, date);
CREATE INDEX IF NOT EXISTS idx_act_date ON activities(date);
CREATE TABLE IF NOT EXISTS pending_activities(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    file_name TEXT DEFAULT '',
    sport TEXT NOT NULL,
    distance_km REAL NOT NULL,
    duration_min INTEGER DEFAULT 0,
    date TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    provider TEXT DEFAULT 'gpx',
    created_at TEXT DEFAULT (datetime('now'))
);
"""

# Wariant pod PostgreSQL: SERIAL zamiast AUTOINCREMENT, now() zamiast
# datetime('now'), cudzyslowy przy nazwach bedacych slowami kluczowymi.
SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS classes(
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS users(
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'uczen',
    class_id INTEGER REFERENCES classes(id),
    avatar_base TEXT DEFAULT 'biegacz',
    avatar_items TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (now()::text)
);
CREATE TABLE IF NOT EXISTS settings(
    "key" TEXT PRIMARY KEY,
    "value" TEXT
);
CREATE TABLE IF NOT EXISTS connections(
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    provider TEXT NOT NULL,
    connected INTEGER DEFAULT 1,
    access_token TEXT,
    refresh_token TEXT,
    expires_at INTEGER,
    athlete_id TEXT,
    athlete_name TEXT,
    created_at TEXT DEFAULT (now()::text),
    UNIQUE(user_id, provider)
);
CREATE TABLE IF NOT EXISTS activities(
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    provider TEXT DEFAULT 'manual',
    type TEXT NOT NULL,
    distance_km REAL NOT NULL,
    duration_min INTEGER DEFAULT 0,
    date TEXT NOT NULL,
    points REAL NOT NULL,
    external_id TEXT,
    created_at TEXT DEFAULT (now()::text)
);
CREATE TABLE IF NOT EXISTS bonuses(
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    week_key TEXT NOT NULL,
    days_active INTEGER NOT NULL,
    bonus REAL NOT NULL,
    created_at TEXT DEFAULT (now()::text),
    UNIQUE(user_id, week_key)
);
CREATE TABLE IF NOT EXISTS missions(
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    kind TEXT NOT NULL DEFAULT 'dzienna',
    cond_type TEXT NOT NULL,
    cond_sport TEXT DEFAULT 'any',
    cond_value REAL DEFAULT 0,
    cond_period TEXT DEFAULT 'day',
    points REAL DEFAULT 0,
    badge_icon TEXT DEFAULT '',
    avatar_item TEXT DEFAULT '',
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (now()::text)
);
CREATE TABLE IF NOT EXISTS user_missions(
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    mission_id INTEGER NOT NULL,
    period_key TEXT NOT NULL,
    progress REAL DEFAULT 0,
    completed INTEGER DEFAULT 0,
    completed_at TEXT DEFAULT '',
    UNIQUE(user_id, mission_id, period_key)
);
CREATE TABLE IF NOT EXISTS achievements(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    category TEXT NOT NULL,
    icon TEXT NOT NULL,
    color TEXT NOT NULL,
    cond_type TEXT NOT NULL,
    cond_sport TEXT DEFAULT 'any',
    cond_value REAL DEFAULT 0,
    reward_points REAL DEFAULT 0,
    reward_item TEXT DEFAULT '',
    "rank" TEXT DEFAULT 'latwy'
);
CREATE TABLE IF NOT EXISTS user_achievements(
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    ach_id INTEGER NOT NULL,
    unlocked_at TEXT DEFAULT (now()::text),
    UNIQUE(user_id, ach_id)
);
CREATE TABLE IF NOT EXISTS announcements(
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    event_date TEXT DEFAULT '',
    created_at TEXT DEFAULT (now()::text)
);
CREATE TABLE IF NOT EXISTS announcement_joins(
    id SERIAL PRIMARY KEY,
    announcement_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    UNIQUE(announcement_id, user_id)
);
CREATE TABLE IF NOT EXISTS likes(
    id SERIAL PRIMARY KEY,
    activity_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    UNIQUE(activity_id, user_id)
);
CREATE TABLE IF NOT EXISTS comments(
    id SERIAL PRIMARY KEY,
    activity_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (now()::text)
);
CREATE TABLE IF NOT EXISTS contests(
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    status TEXT DEFAULT 'aktywny',
    winner_id INTEGER,
    created_at TEXT DEFAULT (now()::text)
);
CREATE TABLE IF NOT EXISTS follows(
    id SERIAL PRIMARY KEY,
    follower_id INTEGER NOT NULL,
    followed_id INTEGER NOT NULL,
    UNIQUE(follower_id, followed_id)
);
CREATE INDEX IF NOT EXISTS idx_act_user_date ON activities(user_id, date);
CREATE INDEX IF NOT EXISTS idx_act_date ON activities(date);
CREATE UNIQUE INDEX IF NOT EXISTS idx_act_ext ON activities(provider, external_id);
CREATE TABLE IF NOT EXISTS pending_activities(
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    file_name TEXT DEFAULT '',
    sport TEXT NOT NULL,
    distance_km REAL NOT NULL,
    duration_min INTEGER DEFAULT 0,
    date TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    provider TEXT DEFAULT 'gpx',
    created_at TEXT DEFAULT (now()::text)
);
"""


class Conn:
    """Jednolite polaczenie dla obu silnikow (tlumaczy placeholdery)."""

    def __init__(self, raw, is_pg):
        self.raw = raw
        self.is_pg = is_pg

    def execute(self, sql, params=None):
        if self.is_pg:
            sql = sql.replace("?", "%s")
        if params is None:
            return self.raw.execute(sql)
        return self.raw.execute(sql, params)

    def commit(self):
        return self.raw.commit()

    def rollback(self):
        return self.raw.rollback()

    def close(self):
        return self.raw.close()


def _pg_connect():
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def get_db():
    if "db" not in g:
        if USE_PG:
            g.db = Conn(_pg_connect(), True)
        else:
            con = sqlite3.connect(DB_PATH)
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA foreign_keys = ON")
            g.db = Conn(con, False)
    return g.db


def close_db(_e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def insert_get_id(sql, params):
    """INSERT zwracajacy id nowego wiersza (oba silniki)."""
    db = get_db()
    if USE_PG:
        return db.execute(sql + " RETURNING id", params).fetchone()["id"]
    return db.execute(sql, params).lastrowid


def init_db():
    if USE_PG:
        con = _pg_connect()
        con.execute(SCHEMA_PG)
        con.commit()
        con.close()
    else:
        con = sqlite3.connect(DB_PATH)
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(SCHEMA_SQLITE)
        con.commit()
        con.close()


def reset_db():
    """Calkowite wyczyszczenie bazy (pod --reset seeda)."""
    if USE_PG:
        con = _pg_connect()
        con.execute("DROP TABLE IF EXISTS " + ", ".join(TABLES) + " CASCADE")
        con.commit()
        con.close()
    elif os.path.exists(DB_PATH):
        os.remove(DB_PATH)


def migrate():
    """Migracja istniejacych baz (dodanie kolumn/tabel integracji)."""
    if USE_PG:
        con = _pg_connect()
        con.execute('CREATE TABLE IF NOT EXISTS settings("key" TEXT PRIMARY KEY, "value" TEXT)')
        con.execute("""CREATE TABLE IF NOT EXISTS pending_activities(
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            file_name TEXT DEFAULT '',
            sport TEXT NOT NULL,
            distance_km REAL NOT NULL,
            duration_min INTEGER DEFAULT 0,
            date TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            provider TEXT DEFAULT 'gpx',
            created_at TEXT DEFAULT (now()::text)
        )""")
        add = [("connections", "access_token", "TEXT"),
               ("connections", "refresh_token", "TEXT"),
               ("connections", "expires_at", "INTEGER"),
               ("connections", "athlete_id", "TEXT"),
               ("connections", "athlete_name", "TEXT"),
               ("activities", "external_id", "TEXT")]
        for t, c, typ in add:
            con.execute(f"ALTER TABLE {t} ADD COLUMN IF NOT EXISTS {c} {typ}")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_act_ext "
                    "ON activities(provider, external_id)")
        con.commit()
        con.close()
        return
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT)")
    con.execute("""CREATE TABLE IF NOT EXISTS pending_activities(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        file_name TEXT DEFAULT '',
        sport TEXT NOT NULL,
        distance_km REAL NOT NULL,
        duration_min INTEGER DEFAULT 0,
        date TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        provider TEXT DEFAULT 'gpx',
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    def cols(table):
        return {r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()}

    cc = cols("connections")
    for col, typ in [("access_token", "TEXT"), ("refresh_token", "TEXT"),
                     ("expires_at", "INTEGER"), ("athlete_id", "TEXT"),
                     ("athlete_name", "TEXT")]:
        if col not in cc:
            con.execute(f"ALTER TABLE connections ADD COLUMN {col} {typ}")
    mc = cols("missions")
    for col, typ in [("title", "TEXT"), ("description", "TEXT"), ("kind", "TEXT"),
                     ("cond_type", "TEXT"), ("cond_sport", "TEXT"),
                     ("cond_value", "REAL"), ("cond_period", "TEXT"),
                     ("points", "REAL"), ("badge_icon", "TEXT"),
                     ("avatar_item", "TEXT"), ("active", "INTEGER")]:
        if col not in mc:
            con.execute(f"ALTER TABLE missions ADD COLUMN {col} {typ}")
    if "external_id" not in cols("activities"):
        con.execute("ALTER TABLE activities ADD COLUMN external_id TEXT")
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_act_ext ON activities(provider, external_id)")
    con.commit()
    con.close()


def row_to_dict(r):
    return dict(r) if r is not None else None


def rows_to_dicts(rows):
    return [dict(r) for r in rows]

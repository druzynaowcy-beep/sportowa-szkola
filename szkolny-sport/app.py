"""Sportowa Szkola - MVP. Backend Flask + SQLite, frontend statyczny (SPA)."""
import csv
import io
import json
import os
import random
import re
import secrets
from datetime import timedelta
from functools import wraps

from flask import Flask, jsonify, redirect, request, send_file, session
from werkzeug.security import check_password_hash, generate_password_hash

import logic
import strava_client as strava
from db import close_db, get_db, init_db, insert_get_id, migrate, row_to_dict, rows_to_dicts
from logic import (
    SPORTS, SPORT_ICON, PROVIDERS, MISSION_KINDS, CATEGORIES,
    AVATAR_BASES, AVATAR_ITEMS, BASE_BY_ID, ITEM_BY_ID,
)

CONNECTABLE = ["strava", "garmin", "googlefit", "applehealth"]

app = Flask(__name__, static_folder="static", static_url_path="")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-zmien-na-produkcji-123")
app.permanent_session_lifetime = timedelta(days=7)
app.teardown_appcontext(close_db)


# --- pomocnicze ---
def current_uid():
    return session.get("uid")


def current_user():
    uid = current_uid()
    if not uid:
        return None
    db = get_db()
    return row_to_dict(db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())


def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not current_uid():
            return jsonify({"error": "Musisz sie zalogowac."}), 401
        return fn(*a, **kw)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        u = current_user()
        if not u or u["role"] != "admin":
            return jsonify({"error": "Brak uprawnien administratora."}), 403
        return fn(*a, **kw)
    return wrapper


def me_dict(uid):
    db = get_db()
    u = db.execute(
        """SELECT u.*, c.name AS class_name FROM users u
           LEFT JOIN classes c ON c.id=u.class_id WHERE u.id=?""", (uid,)
    ).fetchone()
    if not u:
        return None
    d = dict(u)
    d.pop("password_hash", None)
    d["points"] = logic.user_points(uid)
    try:
        d["avatar_items"] = json.loads(d.get("avatar_items") or "[]")
    except Exception:
        d["avatar_items"] = []
    conns = {r["provider"] for r in db.execute(
        "SELECT provider FROM connections WHERE user_id=? AND connected=1", (uid,))}
    d["connections"] = sorted(conns)
    d["avatar_items_available"] = logic.available_items(uid)
    return d


def paginate(items, page, per_page):
    total = len(items)
    start = (page - 1) * per_page
    return {"items": items[start:start + per_page], "total": total,
            "page": page, "per_page": per_page,
            "pages": max(1, (total + per_page - 1) // per_page)}


# --- frontend (SPA) ---
@app.route("/")
def index():
    return send_file("static/index.html")


@app.errorhandler(404)
def spa_fallback(e):
    p = request.path
    if p.startswith("/api/") or "." in p.rsplit("/", 1)[-1]:
        return jsonify({"error": "Nie znaleziono."}), 404
    return send_file("static/index.html")


@app.get("/api/meta")
def meta():
    return jsonify({
        "sports": [{"id": k, "name": v, "icon": SPORT_ICON[k],
                    "mult": logic.SPORT_MULT[k]} for k, v in SPORTS.items()],
        "providers": [{"id": k, "name": v} for k, v in PROVIDERS.items()],
        "connectable": CONNECTABLE,
        "mission_kinds": MISSION_KINDS,
        "categories": CATEGORIES,
        "avatar_bases": AVATAR_BASES,
        "avatar_items": AVATAR_ITEMS,
        "integrations": {"strava_configured": strava.get_config()["configured"]},
    })


# --- autoryzacja ---
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.post("/api/register")
def register():
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()
    class_id = data.get("class_id")
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Podaj poprawny adres e-mail."}), 400
    if len(password) < 6:
        return jsonify({"error": "Haslo musi miec min. 6 znakow."}), 400
    if len(name) < 2:
        return jsonify({"error": "Podaj imie i nazwisko."}), 400
    if not data.get("rodo"):
        return jsonify({"error": "Musisz zaakceptowac polityke prywatnosci (RODO)."}), 400
    db = get_db()
    if class_id:
        c = db.execute("SELECT id FROM classes WHERE id=?", (class_id,)).fetchone()
        if not c:
            return jsonify({"error": "Wybrana klasa nie istnieje."}), 400
    else:
        class_id = None
    if db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
        return jsonify({"error": "Ten e-mail jest juz zarejestrowany."}), 400
    count = db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    role = "admin" if count == 0 else "uczen"
    new_id = insert_get_id(
        "INSERT INTO users(email, password_hash, name, role, class_id) VALUES(?,?,?,?,?)",
        (email, generate_password_hash(password), name, role, class_id),
    )
    db.commit()
    session.permanent = True
    session["uid"] = new_id
    return jsonify({"ok": True, "me": me_dict(new_id)})


@app.post("/api/login")
def login():
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    db = get_db()
    u = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not u or not check_password_hash(u["password_hash"], password):
        return jsonify({"error": "Bledny e-mail lub haslo."}), 401
    session.permanent = True
    session["uid"] = u["id"]
    return jsonify({"ok": True, "me": me_dict(u["id"])})


@app.post("/api/logout")
def logout():
    session.pop("uid", None)
    return jsonify({"ok": True})


@app.get("/api/me")
def me():
    uid = current_uid()
    if not uid:
        return jsonify({"me": None})
    return jsonify({"me": me_dict(uid)})


@app.put("/api/me")
@login_required
def update_me():
    data = request.get_json(force=True) or {}
    uid = current_uid()
    db = get_db()
    updates, params = [], []
    if "name" in data:
        name = (data["name"] or "").strip()
        if len(name) < 2:
            return jsonify({"error": "Za krotkie imie."}), 400
        updates.append("name=?")
        params.append(name)
    if "avatar_base" in data:
        if data["avatar_base"] not in BASE_BY_ID:
            return jsonify({"error": "Nieznana postac."}), 400
        updates.append("avatar_base=?")
        params.append(data["avatar_base"])
    if "class_id" in data:
        # Jednorazowy wybor klasy (np. konta przez Strave); potem tylko admin.
        cur_class = db.execute("SELECT class_id FROM users WHERE id=?", (uid,)).fetchone()["class_id"]
        if cur_class:
            return jsonify({"error": "Klase moze zmienic tylko administrator."}), 400
        cid = data["class_id"]
        if not cid or not db.execute("SELECT id FROM classes WHERE id=?", (cid,)).fetchone():
            return jsonify({"error": "Wybierz istniejaca klase."}), 400
        updates.append("class_id=?")
        params.append(cid)
    if "avatar_items" in data:
        avail = {i["id"] for i in logic.available_items(uid) if i["unlocked"]}
        chosen = [x for x in (data["avatar_items"] or []) if x in avail]
        updates.append("avatar_items=?")
        params.append(json.dumps(chosen[:8]))
    if updates:
        params.append(uid)
        db.execute(f"UPDATE users SET {', '.join(updates)} WHERE id=?", params)
        db.commit()
    return jsonify({"ok": True, "me": me_dict(uid)})


@app.post("/api/me/password")
@login_required
def change_password():
    data = request.get_json(force=True) or {}
    cur = data.get("current") or ""
    new = data.get("new") or ""
    db = get_db()
    u = db.execute("SELECT * FROM users WHERE id=?", (current_uid(),)).fetchone()
    if not check_password_hash(u["password_hash"], cur):
        return jsonify({"error": "Bledne obecne haslo."}), 400
    if len(new) < 6:
        return jsonify({"error": "Nowe haslo musi miec min. 6 znakow."}), 400
    db.execute("UPDATE users SET password_hash=? WHERE id=?",
               (generate_password_hash(new), current_uid()))
    db.commit()
    return jsonify({"ok": True})


@app.get("/api/classes")
def classes():
    db = get_db()
    return jsonify({"classes": rows_to_dicts(
        db.execute("SELECT * FROM classes ORDER BY name").fetchall())})


# --- laczenie kont sportowych + synchronizacja ---
@app.get("/api/connections")
@login_required
def connections():
    db = get_db()
    rows = {r["provider"]: dict(r) for r in db.execute(
        "SELECT * FROM connections WHERE user_id=? AND connected=1", (current_uid(),))}
    out = []
    for p in CONNECTABLE:
        r = rows.get(p)
        out.append({"id": p, "name": PROVIDERS[p], "connected": bool(r),
                    "real": bool(r and r.get("access_token")),
                    "athlete": (r.get("athlete_name") if r else "") or ""})
    return jsonify({"connections": out})


@app.post("/api/connect/<provider>")
@login_required
def connect(provider):
    if provider not in CONNECTABLE:
        return jsonify({"error": "Nieznany dostawca."}), 400
    # Tryb demo (symulacja). Prawdziwa Strava: GET /strava/connect (OAuth2).
    db = get_db()
    db.execute(
        """INSERT INTO connections(user_id, provider, connected) VALUES(?,?,1)
           ON CONFLICT(user_id, provider) DO UPDATE SET connected=1""",
        (current_uid(), provider),
    )
    db.commit()
    return jsonify({"ok": True, "provider": provider})


@app.delete("/api/connect/<provider>")
@login_required
def disconnect(provider):
    db = get_db()
    db.execute("DELETE FROM connections WHERE user_id=? AND provider=?",
               (current_uid(), provider))
    db.commit()
    return jsonify({"ok": True})


@app.post("/api/sync/<provider>")
@login_required
def sync(provider):
    if provider not in CONNECTABLE:
        return jsonify({"error": "Nieznany dostawca."}), 400
    db = get_db()
    c = db.execute("SELECT id FROM connections WHERE user_id=? AND provider=? AND connected=1",
                   (current_uid(), provider)).fetchone()
    if not c:
        return jsonify({"error": f"Najpierw polacz konto {PROVIDERS[provider]}."}), 400
    uid = current_uid()
    # Strava: prawdziwy import, gdy uzytkownik polaczyl konto przez OAuth.
    if provider == "strava":
        try:
            real = try_real_strava_sync(uid)
        except strava.StravaError as e:
            return jsonify({"error": str(e)}), 502
        if real is not None:
            real["me"] = me_dict(uid)
            return jsonify(real)
    # Symulowane pobranie aktywnosci (tryb demo / pozostali dostawcy).
    created, missions, achievements, bonuses = [], [], [], []
    try:
        from datetime import date as _date, timedelta as _td
        n = random.randint(1, 2)
        for _ in range(n):
            sport = random.choices(["bieg", "rower", "spacer"], weights=[4, 3, 3])[0]
            lo, hi = {"bieg": (1, 12), "rower": (5, 40), "spacer": (1, 8)}[sport]
            km = round(random.uniform(lo, hi), 1)
            d = (_date.today() - _td(days=random.randint(0, 1))).isoformat()
            pace = {"bieg": 6, "rower": 3, "spacer": 10}[sport]
            dur = int(km * pace * random.uniform(0.9, 1.2))
            res = logic.add_activity(uid, sport, km, d, provider, dur)
            created.append(res["activity"])
            missions += res["missions"]
            achievements += res["achievements"]
            bonuses += res["bonuses"]
    except Exception as ex:
        return jsonify({"error": f"Synchronizacja nie powiodla sie: {ex}"}), 500
    return jsonify({"ok": True, "created": created, "missions": missions,
                    "achievements": achievements, "bonuses": bonuses, "me": me_dict(uid)})


# --- aktywnosci ---
def activity_full(a, uid):
    d = dict(a)
    d["user"] = logic.user_row(a["user_id"])
    db = get_db()
    d["likes"] = db.execute("SELECT COUNT(*) c FROM likes WHERE activity_id=?",
                            (a["id"],)).fetchone()["c"]
    d["comments_count"] = db.execute("SELECT COUNT(*) c FROM comments WHERE activity_id=?",
                                    (a["id"],)).fetchone()["c"]
    d["liked"] = bool(uid and db.execute(
        "SELECT id FROM likes WHERE activity_id=? AND user_id=?", (a["id"], uid)).fetchone())
    return d


@app.get("/api/feed")
def feed():
    try:
        limit = min(int(request.args.get("limit", 20)), 50)
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({"error": "Bledne parametry."}), 400
    db = get_db()
    rows = db.execute(
        "SELECT * FROM activities ORDER BY date DESC, id DESC LIMIT ? OFFSET ?",
        (limit, offset)).fetchall()
    uid = current_uid()
    return jsonify({"items": [activity_full(a, uid) for a in rows]})


@app.get("/api/activities")
def activities():
    user_id = request.args.get("user_id")
    try:
        limit = min(int(request.args.get("limit", 50)), 100)
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({"error": "Bledne parametry."}), 400
    db = get_db()
    q = "SELECT * FROM activities"
    params = []
    if user_id:
        if user_id == "mine":
            if not current_uid():
                return jsonify({"error": "Musisz sie zalogowac."}), 401
            user_id = current_uid()
        q += " WHERE user_id=?"
        params.append(user_id)
    q += " ORDER BY date DESC, id DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    rows = db.execute(q, params).fetchall()
    return jsonify({"items": [activity_full(a, current_uid()) for a in rows]})


@app.post("/api/activities")
@login_required
def create_activity():
    data = request.get_json(force=True) or {}
    sport = data.get("type")
    if sport not in SPORTS:
        return jsonify({"error": "Wybierz rodzaj aktywnosci."}), 400
    try:
        km = float(data.get("distance_km") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "Podaj dystans w km."}), 400
    if not (0.1 <= km <= 500):
        return jsonify({"error": "Dystans musi wynosic 0,1-500 km."}), 400
    datestr = (data.get("date") or logic.today_str()).strip()
    try:
        from datetime import date as _date
        d = _date.fromisoformat(datestr)
        if d > _date.today():
            return jsonify({"error": "Data nie moze byc z przyszlosci."}), 400
    except ValueError:
        return jsonify({"error": "Bledna data."}), 400
    try:
        dur = int(data.get("duration_min") or 0)
    except (TypeError, ValueError):
        dur = 0
    res = logic.add_activity(current_uid(), sport, km, datestr, "manual", dur)
    res["me"] = me_dict(current_uid())
    res["ok"] = True
    return jsonify(res)


@app.delete("/api/activities/<int:aid>")
@login_required
def delete_activity(aid):
    db = get_db()
    a = db.execute("SELECT * FROM activities WHERE id=?", (aid,)).fetchone()
    if not a:
        return jsonify({"error": "Nie znaleziono."}), 404
    u = current_user()
    if a["user_id"] != u["id"] and u["role"] != "admin":
        return jsonify({"error": "Brak uprawnien."}), 403
    wk = logic.week_key(a["date"])
    db.execute("DELETE FROM likes WHERE activity_id=?", (aid,))
    db.execute("DELETE FROM comments WHERE activity_id=?", (aid,))
    db.execute("DELETE FROM activities WHERE id=?", (aid,))
    db.commit()
    logic.fix_week_bonus(a["user_id"], wk)
    return jsonify({"ok": True})


@app.post("/api/activities/<int:aid>/like")
@login_required
def like(aid):
    db = get_db()
    if not db.execute("SELECT id FROM activities WHERE id=?", (aid,)).fetchone():
        return jsonify({"error": "Nie znaleziono."}), 404
    db.execute("INSERT INTO likes(activity_id, user_id) VALUES(?,?) ON CONFLICT DO NOTHING",
               (aid, current_uid()))
    db.commit()
    a = db.execute("SELECT user_id FROM activities WHERE id=?", (aid,)).fetchone()
    un = logic.check_achievements(current_uid())
    if a["user_id"] != current_uid():
        un += logic.check_achievements(a["user_id"])
    likes = db.execute("SELECT COUNT(*) c FROM likes WHERE activity_id=?", (aid,)).fetchone()["c"]
    return jsonify({"ok": True, "likes": likes, "achievements": un, "me": me_dict(current_uid())})


@app.delete("/api/activities/<int:aid>/like")
@login_required
def unlike(aid):
    db = get_db()
    db.execute("DELETE FROM likes WHERE activity_id=? AND user_id=?", (aid, current_uid()))
    db.commit()
    likes = db.execute("SELECT COUNT(*) c FROM likes WHERE activity_id=?", (aid,)).fetchone()["c"]
    return jsonify({"ok": True, "likes": likes})


@app.get("/api/activities/<int:aid>/comments")
def get_comments(aid):
    db = get_db()
    rows = db.execute(
        """SELECT cm.*, u.name AS user_name, u.avatar_base, c.name AS class_name
           FROM comments cm JOIN users u ON u.id=cm.user_id
           LEFT JOIN classes c ON c.id=u.class_id
           WHERE cm.activity_id=? ORDER BY cm.id""", (aid,)).fetchall()
    return jsonify({"items": rows_to_dicts(rows)})


@app.post("/api/activities/<int:aid>/comments")
@login_required
def add_comment(aid):
    db = get_db()
    if not db.execute("SELECT id FROM activities WHERE id=?", (aid,)).fetchone():
        return jsonify({"error": "Nie znaleziono."}), 404
    data = request.get_json(force=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "Komentarz nie moze byc pusty."}), 400
    if len(content) > 500:
        return jsonify({"error": "Komentarz za dlugi (max 500 znakow)."}), 400
    db.execute("INSERT INTO comments(activity_id, user_id, content) VALUES(?,?,?)",
               (aid, current_uid(), content))
    db.commit()
    un = logic.check_achievements(current_uid())
    mis = logic.check_missions(current_uid())
    return jsonify({"ok": True, "achievements": un, "missions": mis,
                    "me": me_dict(current_uid())})


@app.delete("/api/comments/<int:cid>")
@login_required
def delete_comment(cid):
    db = get_db()
    cm = db.execute("SELECT * FROM comments WHERE id=?", (cid,)).fetchone()
    if not cm:
        return jsonify({"error": "Nie znaleziono."}), 404
    u = current_user()
    if cm["user_id"] != u["id"] and u["role"] != "admin":
        return jsonify({"error": "Brak uprawnien."}), 403
    db.execute("DELETE FROM comments WHERE id=?", (cid,))
    db.commit()
    return jsonify({"ok": True})


# --- statystyki ---
@app.get("/api/stats/mine")
@login_required
def stats_mine():
    return jsonify(logic.stats_user(current_uid()))


@app.get("/api/stats/user/<int:uid>")
def stats_user(uid):
    db = get_db()
    if not db.execute("SELECT id FROM users WHERE id=?", (uid,)).fetchone():
        return jsonify({"error": "Nie znaleziono."}), 404
    return jsonify(logic.stats_user(uid))


# --- rankingi ---
@app.get("/api/rankings/individual")
def ranking_individual():
    role = request.args.get("role", "uczen")
    if role not in ("uczen", "nauczyciel"):
        return jsonify({"error": "Bledna rola."}), 400
    try:
        page = max(int(request.args.get("page", 1)), 1)
        per = min(max(int(request.args.get("per_page", 20)), 5), 100)
    except ValueError:
        return jsonify({"error": "Bledne parametry."}), 400
    class_id = request.args.get("class_id", type=int)
    return jsonify(paginate(logic.all_totals(role, class_id), page, per))


@app.get("/api/rankings/classes")
def ranking_classes():
    return jsonify({"items": logic.rankings_classes()})


@app.get("/api/top")
def top():
    return jsonify({
        "week": logic.top_period("week"),
        "month": logic.top_period("month"),
        "year": logic.top_period("year"),
    })


# --- misje / osiagniecia ---
@app.get("/api/missions")
@login_required
def missions():
    return jsonify({"items": logic.my_missions(current_uid())})


@app.get("/api/achievements")
def achievements():
    user_id = request.args.get("user_id", "mine")
    if user_id == "mine":
        if not current_uid():
            return jsonify({"error": "Musisz sie zalogowac."}), 401
        user_id = current_uid()
    db = get_db()
    alla = rows_to_dicts(db.execute("SELECT * FROM achievements ORDER BY category, cond_value").fetchall())
    un = {r["ach_id"]: r["unlocked_at"] for r in db.execute(
        "SELECT ach_id, unlocked_at FROM user_achievements WHERE user_id=?", (user_id,))}
    for a in alla:
        a["unlocked"] = a["id"] in un
        a["unlocked_at"] = un.get(a["id"])
        a["category_name"] = CATEGORIES.get(a["category"], {}).get("name", a["category"])
    return jsonify({"items": alla})


@app.get("/api/records")
def records():
    return jsonify(logic.records())


@app.get("/api/avatar")
@login_required
def avatar():
    return jsonify({"bases": AVATAR_BASES, "items": logic.available_items(current_uid())})


# --- ogloszenia ---
@app.get("/api/announcements")
def announcements():
    db = get_db()
    rows = db.execute(
        """SELECT an.*, u.name AS user_name, u.avatar_base, c.name AS class_name,
                  (SELECT COUNT(*) FROM announcement_joins j WHERE j.announcement_id=an.id) AS joins
           FROM announcements an JOIN users u ON u.id=an.user_id
           LEFT JOIN classes c ON c.id=u.class_id
           ORDER BY an.created_at DESC, an.id DESC""").fetchall()
    uid = current_uid()
    items = []
    for r in rows:
        d = dict(r)
        d["joined"] = False
        if uid:
            d["joined"] = bool(db.execute(
                "SELECT id FROM announcement_joins WHERE announcement_id=? AND user_id=?",
                (r["id"], uid)).fetchone())
        items.append(d)
    return jsonify({"items": items})


@app.post("/api/announcements")
@login_required
def create_announcement():
    data = request.get_json(force=True) or {}
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    event_date = (data.get("event_date") or "").strip()
    if len(title) < 3:
        return jsonify({"error": "Tytul za krotki."}), 400
    if len(content) < 3:
        return jsonify({"error": "Tresc za krotka."}), 400
    db = get_db()
    db.execute("INSERT INTO announcements(user_id, title, content, event_date) VALUES(?,?,?,?)",
               (current_uid(), title, content, event_date))
    db.commit()
    un = logic.check_achievements(current_uid())
    return jsonify({"ok": True, "achievements": un, "me": me_dict(current_uid())})


@app.delete("/api/announcements/<int:aid>")
@login_required
def delete_announcement(aid):
    db = get_db()
    an = db.execute("SELECT * FROM announcements WHERE id=?", (aid,)).fetchone()
    if not an:
        return jsonify({"error": "Nie znaleziono."}), 404
    u = current_user()
    if an["user_id"] != u["id"] and u["role"] != "admin":
        return jsonify({"error": "Brak uprawnien."}), 403
    db.execute("DELETE FROM announcement_joins WHERE announcement_id=?", (aid,))
    db.execute("DELETE FROM announcements WHERE id=?", (aid,))
    db.commit()
    return jsonify({"ok": True})


@app.post("/api/announcements/<int:aid>/join")
@login_required
def join_announcement(aid):
    db = get_db()
    if not db.execute("SELECT id FROM announcements WHERE id=?", (aid,)).fetchone():
        return jsonify({"error": "Nie znaleziono."}), 404
    db.execute("INSERT INTO announcement_joins(announcement_id, user_id) VALUES(?,?) ON CONFLICT DO NOTHING",
               (aid, current_uid()))
    db.commit()
    un = logic.check_achievements(current_uid())
    mis = logic.check_missions(current_uid())
    return jsonify({"ok": True, "achievements": un, "missions": mis,
                    "me": me_dict(current_uid())})


@app.delete("/api/announcements/<int:aid>/join")
@login_required
def leave_announcement(aid):
    db = get_db()
    db.execute("DELETE FROM announcement_joins WHERE announcement_id=? AND user_id=?",
               (aid, current_uid()))
    db.commit()
    return jsonify({"ok": True})


# --- konkursy ---
@app.get("/api/contests")
def contests():
    db = get_db()
    # Lenivy cron: domknij zalegle konkursy przy pierwszym podgladzie po terminie.
    for c in db.execute("SELECT * FROM contests WHERE status='aktywny'").fetchall():
        if c["end_date"] < logic.today_str():
            logic.finish_contest(c["id"])
    rows = rows_to_dicts(db.execute("SELECT * FROM contests ORDER BY end_date DESC").fetchall())
    for c in rows:
        c["winner"] = logic.user_row(c["winner_id"]) if c["winner_id"] else None
    return jsonify({"items": rows})


@app.post("/api/contests")
@login_required
@admin_required
def create_contest():
    data = request.get_json(force=True) or {}
    title = (data.get("title") or "").strip()
    if len(title) < 3:
        return jsonify({"error": "Tytul za krotki."}), 400
    start = (data.get("start_date") or "").strip()
    end = (data.get("end_date") or "").strip()
    if not start or not end or end < start:
        return jsonify({"error": "Bledny zakres dat."}), 400
    db = get_db()
    db.execute("INSERT INTO contests(title, description, start_date, end_date) VALUES(?,?,?,?)",
               (title, (data.get("description") or "").strip(), start, end))
    db.commit()
    return jsonify({"ok": True})


@app.post("/api/contests/<int:cid>/finish")
@login_required
@admin_required
def finish_contest(cid):
    res = logic.finish_contest(cid)
    if res is None:
        return jsonify({"error": "Nie znaleziono."}), 404
    return jsonify({"ok": True, "contest": res})


@app.delete("/api/contests/<int:cid>")
@login_required
@admin_required
def delete_contest(cid):
    db = get_db()
    db.execute("DELETE FROM contests WHERE id=?", (cid,))
    db.commit()
    return jsonify({"ok": True})


# --- obserwowanie ---
@app.post("/api/follow/<int:uid>")
@login_required
def follow(uid):
    if uid == current_uid():
        return jsonify({"error": "Nie mozesz obserwowac samego siebie."}), 400
    db = get_db()
    if not db.execute("SELECT id FROM users WHERE id=?", (uid,)).fetchone():
        return jsonify({"error": "Nie znaleziono."}), 404
    db.execute("INSERT INTO follows(follower_id, followed_id) VALUES(?,?) ON CONFLICT DO NOTHING",
               (current_uid(), uid))
    db.commit()
    un = logic.check_achievements(current_uid())
    return jsonify({"ok": True, "achievements": un, "me": me_dict(current_uid())})


@app.delete("/api/follow/<int:uid>")
@login_required
def unfollow(uid):
    db = get_db()
    db.execute("DELETE FROM follows WHERE follower_id=? AND followed_id=?",
               (current_uid(), uid))
    db.commit()
    return jsonify({"ok": True})


@app.get("/api/follows")
@login_required
def follows():
    db = get_db()
    uid = current_uid()
    following = [r["followed_id"] for r in db.execute(
        "SELECT followed_id FROM follows WHERE follower_id=?", (uid,))]
    followers = db.execute("SELECT COUNT(*) c FROM follows WHERE followed_id=?",
                           (uid,)).fetchone()["c"]
    return jsonify({"following": following, "followers": followers,
                    "following_count": len(following)})


# --- profil publiczny ---
@app.get("/api/users/<int:uid>")
def public_profile(uid):
    db = get_db()
    u = db.execute(
        """SELECT u.id, u.name, u.role, u.avatar_base, u.avatar_items, c.name AS class_name
           FROM users u LEFT JOIN classes c ON c.id=u.class_id WHERE u.id=?""",
        (uid,)).fetchone()
    if not u:
        return jsonify({"error": "Nie znaleziono."}), 404
    d = dict(u)
    try:
        d["avatar_items"] = json.loads(d.get("avatar_items") or "[]")
    except Exception:
        d["avatar_items"] = []
    d["points"] = logic.user_points(uid)
    d["stats"] = logic.stats_user(uid)
    acts = db.execute("SELECT * FROM activities WHERE user_id=? ORDER BY date DESC, id DESC LIMIT 5",
                      (uid,)).fetchall()
    d["recent"] = [activity_full(a, current_uid()) for a in acts]
    ach = rows_to_dicts(db.execute(
        """SELECT a.* FROM achievements a JOIN user_achievements ua ON ua.ach_id=a.id
           WHERE ua.user_id=? ORDER BY ua.unlocked_at DESC LIMIT 12""", (uid,)).fetchall())
    d["achievements_recent"] = ach
    d["achievements_count"] = db.execute(
        "SELECT COUNT(*) c FROM user_achievements WHERE user_id=?", (uid,)).fetchone()["c"]
    d["followers"] = db.execute("SELECT COUNT(*) c FROM follows WHERE followed_id=?",
                                (uid,)).fetchone()["c"]
    me = current_uid()
    d["followed"] = bool(me and db.execute(
        "SELECT id FROM follows WHERE follower_id=? AND followed_id=?", (me, uid)).fetchone())
    return jsonify(d)


# --- panel administratora ---
@app.get("/api/admin/users")
@login_required
@admin_required
def admin_users():
    q = (request.args.get("q") or "").strip().lower()
    role = request.args.get("role", "")
    try:
        page = max(int(request.args.get("page", 1)), 1)
        per = min(max(int(request.args.get("per_page", 20)), 5), 100)
    except ValueError:
        return jsonify({"error": "Bledne parametry."}), 400
    db = get_db()
    rows = db.execute(
        """SELECT u.*, c.name AS class_name FROM users u
           LEFT JOIN classes c ON c.id=u.class_id ORDER BY u.id""").fetchall()
    items = []
    for r in rows:
        d = dict(r)
        d.pop("password_hash", None)
        if q and q not in d["name"].lower() and q not in d["email"].lower():
            continue
        if role and d["role"] != role:
            continue
        d["points"] = logic.user_points(d["id"])["total"]
        items.append(d)
    return jsonify(paginate(items, page, per))


@app.put("/api/admin/users/<int:uid>")
@login_required
@admin_required
def admin_update_user(uid):
    data = request.get_json(force=True) or {}
    db = get_db()
    u = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not u:
        return jsonify({"error": "Nie znaleziono."}), 404
    updates, params = [], []
    if "name" in data:
        name = (data["name"] or "").strip()
        if len(name) < 2:
            return jsonify({"error": "Za krotkie imie."}), 400
        updates += ["name=?"]
        params.append(name)
    if "role" in data:
        if data["role"] not in ("uczen", "nauczyciel", "admin"):
            return jsonify({"error": "Bledna rola."}), 400
        if u["id"] == current_uid() and data["role"] != "admin":
            return jsonify({"error": "Nie mozesz odebrac sobie roli admina."}), 400
        updates += ["role=?"]
        params.append(data["role"])
    if "class_id" in data:
        cid = data["class_id"]
        if cid and not db.execute("SELECT id FROM classes WHERE id=?", (cid,)).fetchone():
            return jsonify({"error": "Taka klasa nie istnieje."}), 400
        updates += ["class_id=?"]
        params.append(cid)
    if updates:
        params.append(uid)
        db.execute(f"UPDATE users SET {', '.join(updates)} WHERE id=?", params)
        db.commit()
    return jsonify({"ok": True})


@app.delete("/api/admin/users/<int:uid>")
@login_required
@admin_required
def admin_delete_user(uid):
    if uid == current_uid():
        return jsonify({"error": "Nie mozesz usunac samego siebie."}), 400
    db = get_db()
    if not db.execute("SELECT id FROM users WHERE id=?", (uid,)).fetchone():
        return jsonify({"error": "Nie znaleziono."}), 404
    for t in ("connections", "bonuses", "user_missions", "user_achievements"):
        db.execute(f"DELETE FROM {t} WHERE user_id=?", (uid,))
    db.execute("DELETE FROM likes WHERE user_id=? OR activity_id IN (SELECT id FROM activities WHERE user_id=?)",
               (uid, uid))
    db.execute("DELETE FROM comments WHERE user_id=? OR activity_id IN (SELECT id FROM activities WHERE user_id=?)",
               (uid, uid))
    db.execute("DELETE FROM announcement_joins WHERE user_id=? OR announcement_id IN (SELECT id FROM announcements WHERE user_id=?)",
               (uid, uid))
    db.execute("DELETE FROM announcements WHERE user_id=?", (uid,))
    db.execute("DELETE FROM follows WHERE follower_id=? OR followed_id=?", (uid, uid))
    db.execute("DELETE FROM activities WHERE user_id=?", (uid,))
    db.execute("DELETE FROM users WHERE id=?", (uid,))
    db.commit()
    return jsonify({"ok": True})


@app.post("/api/admin/classes")
@login_required
@admin_required
def admin_create_class():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if len(name) < 1 or len(name) > 10:
        return jsonify({"error": "Podaj nazwe klasy (np. 5A)."}), 400
    db = get_db()
    try:
        db.execute("INSERT INTO classes(name) VALUES(?)", (name,))
        db.commit()
    except Exception:
        return jsonify({"error": "Taka klasa juz istnieje."}), 400
    return jsonify({"ok": True})


@app.delete("/api/admin/classes/<int:cid>")
@login_required
@admin_required
def admin_delete_class(cid):
    db = get_db()
    n = db.execute("SELECT COUNT(*) c FROM users WHERE class_id=?", (cid,)).fetchone()["c"]
    if n:
        return jsonify({"error": f"Klasa ma przypisanych {n} uzytkownikow."}), 400
    db.execute("DELETE FROM classes WHERE id=?", (cid,))
    db.commit()
    return jsonify({"ok": True})


@app.get("/api/admin/missions")
@login_required
@admin_required
def admin_missions():
    db = get_db()
    return jsonify({"items": rows_to_dicts(
        db.execute("SELECT * FROM missions ORDER BY kind, id").fetchall())})


@app.post("/api/admin/missions")
@login_required
@admin_required
def admin_create_mission():
    data = request.get_json(force=True) or {}
    title = (data.get("title") or "").strip()
    if len(title) < 3:
        return jsonify({"error": "Tytul za krotki."}), 400
    if data.get("kind") not in MISSION_KINDS:
        return jsonify({"error": "Bledny rodzaj misji."}), 400
    db = get_db()
    db.execute(
        """INSERT INTO missions(title, description, kind, cond_type, cond_sport, cond_value,
                                cond_period, points, badge_icon, avatar_item, active)
           VALUES(?,?,?,?,?,?,?,?,?,?,1)""",
        (title, (data.get("description") or "").strip(), data["kind"],
         data.get("cond_type", "distance_total"), data.get("cond_sport", "any"),
         float(data.get("cond_value") or 0), data.get("cond_period", "week"),
         float(data.get("points") or 0), data.get("badge_icon", "⭐"),
         data.get("avatar_item", "")),
    )
    db.commit()
    return jsonify({"ok": True})


@app.put("/api/admin/missions/<int:mid>")
@login_required
@admin_required
def admin_update_mission(mid):
    data = request.get_json(force=True) or {}
    db = get_db()
    if not db.execute("SELECT id FROM missions WHERE id=?", (mid,)).fetchone():
        return jsonify({"error": "Nie znaleziono."}), 404
    fields = ["title", "description", "kind", "cond_type", "cond_sport", "cond_value",
              "cond_period", "points", "badge_icon", "avatar_item", "active"]
    updates = [f"{f}=?" for f in fields if f in data]
    if not updates:
        return jsonify({"ok": True})
    params = [data[f[0:-2]] for f in updates]
    params.append(mid)
    db.execute(f"UPDATE missions SET {', '.join(updates)} WHERE id=?", params)
    db.commit()
    return jsonify({"ok": True})


@app.delete("/api/admin/missions/<int:mid>")
@login_required
@admin_required
def admin_delete_mission(mid):
    db = get_db()
    db.execute("DELETE FROM user_missions WHERE mission_id=?", (mid,))
    db.execute("DELETE FROM missions WHERE id=?", (mid,))
    db.commit()
    return jsonify({"ok": True})


@app.get("/api/admin/overview")
@login_required
@admin_required
def admin_overview():
    db = get_db()
    users = db.execute("SELECT role, COUNT(*) c FROM users GROUP BY role").fetchall()
    acts = db.execute("SELECT COUNT(*) c, COALESCE(SUM(distance_km),0) km FROM activities").fetchone()
    week_ago = (logic.date.today() - timedelta(days=7)).isoformat() if hasattr(logic, "date") else ""
    new_acts = 0
    if week_ago:
        new_acts = db.execute("SELECT COUNT(*) c FROM activities WHERE date>=?",
                              (week_ago,)).fetchone()["c"]
    return jsonify({
        "users_by_role": {r["role"]: r["c"] for r in rows_to_dicts(users)},
        "activities_total": acts["c"],
        "km_total": round(acts["km"], 1),
        "activities_7d": new_acts,
        "classes": logic.rankings_classes(),
    })


@app.get("/api/admin/export/<kind>")
@login_required
@admin_required
def admin_export(kind):
    db = get_db()
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    if kind == "users":
        w.writerow(["id", "email", "imie_nazwisko", "rola", "klasa", "punkty"])
        for u in db.execute(
                """SELECT u.*, c.name AS class_name FROM users u
                   LEFT JOIN classes c ON c.id=u.class_id ORDER BY u.id"""):
            w.writerow([u["id"], u["email"], u["name"], u["role"],
                        u["class_name"] or "", logic.user_points(u["id"])["total"]])
    elif kind == "activities":
        w.writerow(["id", "uczen", "email", "klasa", "rodzaj", "km", "punkty", "data", "zrodlo"])
        for a in db.execute(
                """SELECT a.*, u.name AS uname, u.email, c.name AS class_name FROM activities a
                   JOIN users u ON u.id=a.user_id LEFT JOIN classes c ON c.id=u.class_id
                   ORDER BY a.date DESC"""):
            w.writerow([a["id"], a["uname"], a["email"], a["class_name"] or "",
                        a["type"], a["distance_km"], a["points"], a["date"], a["provider"]])
    elif kind == "points":
        w.writerow(["miejsce", "uczen", "klasa", "razem", "aktywnosci", "misje",
                    "regularnosc", "osiagniecia"])
        for i, u in enumerate(logic.all_totals("uczen"), 1):
            p = logic.user_points(u["id"])
            w.writerow([i, u["name"], u.get("class_name") or "", p["total"],
                        p["aktywnosci"], p["misje"], p["regularnosc"], p["osiagniecia"]])
    else:
        return jsonify({"error": "Nieznany eksport."}), 400
    data = "\ufeff" + buf.getvalue()
    return app.response_class(data, mimetype="text/csv",
                              headers={"Content-Disposition":
                                       f"attachment; filename={kind}.csv"})


# --- Strava (prawdziwa integracja OAuth2) ---
def try_real_strava_sync(uid):
    """Importuje aktywnosci z prawdziwego konta Strava.

    Zwraca dict z wynikiem albo None, gdy brak prawdziwego polaczenia
    (wtedy synchronizacja dziala w trybie demo)."""
    cfg = strava.get_config()
    if not cfg["configured"]:
        return None
    token = strava.ensure_token(uid, cfg)
    if not token:
        return None
    from datetime import datetime, timedelta
    after = (datetime.now() - timedelta(days=30)).timestamp()
    acts = strava.fetch_recent(token, after)
    db = get_db()
    created, missions, achievements, bonuses = [], [], [], []
    seen_m, seen_a = set(), set()
    for a in acts:
        m = strava.map_activity(a)
        if not m or m["date"] > logic.today_str():
            continue
        dup = db.execute(
            "SELECT id FROM activities WHERE provider='strava' AND external_id=?",
            (m["external_id"],)).fetchone()
        if dup:
            continue
        res = logic.add_activity(uid, m["sport"], m["km"], m["date"], "strava", m["dur"])
        db.execute("UPDATE activities SET external_id=? WHERE id=?",
                   (m["external_id"], res["activity"]["id"]))
        db.commit()
        created.append(res["activity"])
        for x in res["missions"]:
            if x["id"] not in seen_m:
                seen_m.add(x["id"])
                missions.append(x)
        for x in res["achievements"]:
            if x["id"] not in seen_a:
                seen_a.add(x["id"])
                achievements.append(x)
        bonuses += res["bonuses"]
    return {"ok": True, "real": True, "fetched": len(acts), "created": created,
            "missions": missions, "achievements": achievements, "bonuses": bonuses}


@app.get("/strava/login")
def strava_login():
    """Logowanie / rejestracja kontem Strava (bez hasla)."""
    cfg = strava.get_config()
    if not cfg["configured"]:
        session["strava_flash"] = "Logowanie Strava jest wylaczone (brak kluczy API)."
        return redirect("/#/login")
    state = secrets.token_urlsafe(16)
    session["strava_login_state"] = state
    redirect_uri = request.host_url.rstrip("/") + "/strava/login-callback"
    return redirect(strava.auth_url(cfg["client_id"], redirect_uri, state))


@app.get("/strava/login-callback")
def strava_login_callback():
    if request.args.get("error"):
        return redirect("/#/login")
    state = request.args.get("state", "")
    if not state or state != session.pop("strava_login_state", ""):
        session["strava_flash"] = "Blad weryfikacji logowania. Sprobuj ponownie."
        return redirect("/#/login")
    try:
        cfg = strava.get_config()
        tok = strava.exchange_code(cfg, request.args.get("code", ""))
    except strava.StravaError as e:
        session["strava_flash"] = f"Nie udalo sie zalogowac: {e}"
        return redirect("/#/login")
    return strava_login_finish(tok)


def strava_login_finish(tok):
    """Loguje lub zaklada konto na podstawie danych sportowca Strava."""
    athlete = tok.get("athlete") or {}
    athlete_id = str(athlete.get("id") or "")
    if not athlete_id:
        session["strava_flash"] = "Strava nie zwrocila identyfikatora sportowca."
        return redirect("/#/login")
    db = get_db()
    row = db.execute(
        "SELECT user_id FROM connections WHERE provider='strava' AND athlete_id=?",
        (athlete_id,)).fetchone()
    if row:
        uid = row["user_id"]
        strava.save_tokens(uid, tok)
        session["strava_flash"] = "Witaj ponownie! Zalogowano przez Strave. 🎉"
    else:
        name = ((athlete.get("firstname") or "") + " " + (athlete.get("lastname") or "")).strip()
        if not name:
            name = "Sportowiec Strava"
        uid = insert_get_id(
            "INSERT INTO users(email, password_hash, name, role, class_id) VALUES(?,?,?,?,?)",
            (f"strava_{athlete_id}@login.local", generate_password_hash(secrets.token_hex(16)),
             name, "uczen", None),
        )
        strava.save_tokens(uid, tok)
        session["strava_flash"] = "Konto utworzone przez Strave! Wybierz swoja klase. 🎉"
    session.permanent = True
    session["uid"] = uid
    return redirect("/#/profil")


@app.get("/strava/connect")
@login_required
def strava_connect():
    cfg = strava.get_config()
    if not cfg["configured"]:
        return jsonify({"error": "Strava nie jest skonfigurowana. Administrator musi wpisac klucze API w panelu (zakladka Integracje)."}), 400
    state = secrets.token_urlsafe(16)
    session["strava_state"] = state
    redirect_uri = request.host_url.rstrip("/") + "/strava/callback"
    return redirect(strava.auth_url(cfg["client_id"], redirect_uri, state))


@app.get("/strava/callback")
def strava_callback():
    if request.args.get("error"):
        session["strava_flash"] = "Polaczenie ze Strava anulowane."
        return redirect("/#/profil")
    state = request.args.get("state", "")
    if not state or state != session.pop("strava_state", ""):
        session["strava_flash"] = "Blad weryfikacji polaczenia (state). Sprobuj ponownie."
        return redirect("/#/profil")
    if not current_uid():
        session["strava_flash"] = "Sesja wygasla - zaloguj sie i sprobuj ponownie."
        return redirect("/#/login")
    try:
        cfg = strava.get_config()
        tok = strava.exchange_code(cfg, request.args.get("code", ""))
        name = strava.save_tokens(current_uid(), tok)
        session["strava_flash"] = (
            f"Polaczono konto Strava ({name or 'sportowiec'})! Kliknij Synchronizuj.")
    except strava.StravaError as e:
        session["strava_flash"] = f"Nie udalo sie polaczyc: {e}"
    return redirect("/#/profil")


@app.get("/api/strava/status")
@login_required
def strava_status():
    cfg = strava.get_config()
    conn = strava.get_conn(current_uid())
    return jsonify({
        "configured": cfg["configured"],
        "connected": bool(conn and conn["connected"]),
        "real": bool(conn and conn["access_token"]),
        "athlete": (conn["athlete_name"] if conn else "") or "",
        "flash": session.pop("strava_flash", None),
    })


@app.get("/api/admin/integrations")
@login_required
@admin_required
def admin_integrations():
    cfg = strava.get_config()
    db = get_db()
    real_users = db.execute(
        "SELECT COUNT(*) c FROM connections WHERE provider='strava' AND access_token IS NOT NULL"
    ).fetchone()["c"]
    return jsonify({"strava": {
        "configured": cfg["configured"],
        "source": cfg["source"],
        "client_id": cfg["client_id"],
        "callback_url": request.host_url.rstrip("/") + "/strava/callback",
        "real_users": real_users,
    }})


@app.post("/api/admin/integrations/strava")
@login_required
@admin_required
def admin_save_strava():
    data = request.get_json(force=True) or {}
    cid = (data.get("client_id") or "").strip()
    sec = (data.get("client_secret") or "").strip()
    if not cid or not sec:
        return jsonify({"error": "Podaj Client ID i Client Secret."}), 400
    strava.set_setting("strava_client_id", cid)
    strava.set_setting("strava_client_secret", sec)
    return jsonify({"ok": True})


@app.delete("/api/admin/integrations/strava")
@login_required
@admin_required
def admin_clear_strava():
    strava.del_setting("strava_client_id")
    strava.del_setting("strava_client_secret")
    return jsonify({"ok": True})


# --- zadania cykliczne (cron) ---
@app.get("/api/cron/daily")
def cron_daily():
    """Wywolywane raz dziennie (np. cron o polnocy): bonusy + koniec konkursow."""
    db = get_db()
    users = db.execute("SELECT id FROM users").fetchall()
    total_bonuses = 0
    for u in users:
        total_bonuses += len(logic.award_regularnosc(u["id"]))
    finished = []
    for c in db.execute("SELECT * FROM contests WHERE status='aktywny'").fetchall():
        if c["end_date"] < logic.today_str():
            finished.append(logic.finish_contest(c["id"])["id"])
    return jsonify({"ok": True, "bonuses_awarded": total_bonuses,
                    "contests_finished": finished})


if __name__ == "__main__":
    init_db()
    migrate()
    app.run(host="0.0.0.0", port=5000, debug=False)

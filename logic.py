"""Logika biznesowa: punkty, regularnosc, misje, osiagniecia, statystyki, rankingi."""
import calendar
import json
from datetime import date, datetime, timedelta

from db import get_db, insert_get_id, rows_to_dicts

# --- Slowniki ---
SPORTS = {"bieg": "Bieganie", "rower": "Jazda na rowerze", "spacer": "Spacer / marsz"}
SPORT_MULT = {"bieg": 1.5, "rower": 0.8, "spacer": 1.0}
SPORT_ICON = {"bieg": "\U0001F3C3", "rower": "\U0001F6B4", "spacer": "\U0001F6B6"}
PROVIDERS = {
    "strava": "Strava",
    "garmin": "Garmin",
    "googlefit": "Google Fit",
    "applehealth": "Apple Health",
    "manual": "R\u0119cznie",
}
MISSION_KINDS = {
    "dzienna": "Dzienne",
    "tygodniowa": "Tygodniowe",
    "miesieczna": "Miesi\u0119czne",
    "okazjonalna": "Okazjonalne",
}
CATEGORIES = {
    "dystans": {"name": "Dystansowe", "color": "#2196F3"},
    "regularnosc": {"name": "Regularno\u015Bciowe", "color": "#4CAF50"},
    "roznorodnosc": {"name": "R\u00F3\u017Cnorodno\u015Bciowe", "color": "#FF9800"},
    "spolecznosc": {"name": "Spo\u0142eczno\u015Bciowe", "color": "#9C27B0"},
    "specjalne": {"name": "Specjalne / rekordy", "color": "#E8A100"},
    "misje": {"name": "Misje", "color": "#F44336"},
}

AVATAR_BASES = [
    {"id": "chlopiec", "name": "Ch\u0142opiec", "icon": "\U0001F466"},
    {"id": "dziewczynka", "name": "Dziewczynka", "icon": "\U0001F467"},
    {"id": "sportowiec", "name": "Sportowiec", "icon": "\U0001F93E"},
    {"id": "biegacz", "name": "Biegacz", "icon": "\U0001F3C3"},
    {"id": "rowerzysta", "name": "Rowerzysta", "icon": "\U0001F6B4"},
    {"id": "maratonczyk", "name": "Marato\u0144czyk", "icon": "\U0001F396\uFE0F"},
    {"id": "kaptur", "name": "Zawodnik w kapturze", "icon": "\U0001F977"},
    {"id": "super", "name": "Super sportowiec", "icon": "\U0001F9B8"},
    {"id": "mistrz", "name": "Mistrz", "icon": "\U0001F934"},
]
AVATAR_ITEMS = [
    {"id": "czapka", "name": "Czapka", "icon": "\U0001F9E2", "min_points": 10},
    {"id": "opaska", "name": "Opaska", "icon": "\U0001F380", "min_points": 25},
    {"id": "okulary", "name": "Okulary", "icon": "\U0001F60E", "min_points": 50},
    {"id": "koszulka", "name": "Koszulka z numerem", "icon": "\U0001F522", "min_points": 80},
    {"id": "buty", "name": "Buty z kolcami", "icon": "\U0001F45F", "min_points": 120},
    {"id": "rekawiczki", "name": "R\u0119kawiczki", "icon": "\U0001F9E4", "min_points": 160},
    {"id": "sluchawki", "name": "S\u0142uchawki", "icon": "\U0001F3A7", "min_points": 200},
    {"id": "bluza", "name": "Bluza", "icon": "\U0001F9E5", "min_points": 250},
    {"id": "szalik", "name": "Szalik", "icon": "\U0001F9E3", "min_points": 300},
    {"id": "plecak", "name": "Plecak", "icon": "\U0001F392", "min_points": 400},
    {"id": "stroj", "name": "Str\u00F3j profesjonalny", "icon": "\U0001F3BD", "min_points": 500},
    {"id": "medal", "name": "Medal", "icon": "\U0001F3C5", "min_points": 600},
    {"id": "tarcza", "name": "Tarcza", "icon": "\U0001F6E1\uFE0F", "min_points": 750},
    {"id": "zlota_opaska", "name": "Z\u0142ota opaska", "icon": "\U0001F947", "min_points": 900},
    {"id": "korona", "name": "Korona", "icon": "\U0001F451", "min_points": 1200},
    {"id": "puchar", "name": "Puchar", "icon": "\U0001F3C6", "min_points": 1500},
]
BASE_BY_ID = {b["id"]: b for b in AVATAR_BASES}
ITEM_BY_ID = {i["id"]: i for i in AVATAR_ITEMS}


# --- Daty / okresy ---
def today_str():
    return date.today().isoformat()


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def week_key(dstr):
    d = date.fromisoformat(dstr)
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def week_range(wk):
    y, w = wk.split("-W")
    mon = date.fromisocalendar(int(y), int(w), 1)
    return mon.isoformat(), (mon + timedelta(days=6)).isoformat()


def month_range(mk):
    y, m = int(mk[:4]), int(mk[5:7])
    last = calendar.monthrange(y, m)[1]
    return f"{y:04d}-{m:02d}-01", f"{y:04d}-{m:02d}-{last:02d}"


def current_key(period):
    t = today_str()
    if period == "day":
        return t
    if period == "week":
        return week_key(t)
    if period == "month":
        return t[:7]
    return "ever"


def period_bounds(period, key):
    if period == "day":
        return key, key
    if period == "week":
        return week_range(key)
    if period == "month":
        return month_range(key)
    return "0000-00-00", "9999-99-99"


def school_year_start():
    t = date.today()
    y = t.year if t.month >= 9 else t.year - 1
    return date(y, 9, 1).isoformat()


# --- Punkty ---
def points_for(sport, km):
    return round(SPORT_MULT.get(sport, 1.0) * float(km), 1)


def user_points(user_id):
    db = get_db()
    a = db.execute(
        "SELECT COALESCE(SUM(points),0) s FROM activities WHERE user_id=?", (user_id,)
    ).fetchone()["s"]
    b = db.execute(
        "SELECT COALESCE(SUM(bonus),0) s FROM bonuses WHERE user_id=?", (user_id,)
    ).fetchone()["s"]
    m = db.execute(
        """SELECT COALESCE(SUM(m.points),0) s FROM user_missions um
           JOIN missions m ON m.id=um.mission_id
           WHERE um.user_id=? AND um.completed=1""",
        (user_id,),
    ).fetchone()["s"]
    o = db.execute(
        """SELECT COALESCE(SUM(a.reward_points),0) s FROM user_achievements ua
           JOIN achievements a ON a.id=ua.ach_id WHERE ua.user_id=?""",
        (user_id,),
    ).fetchone()["s"]
    return {
        "total": round(a + b + m + o, 1),
        "aktywnosci": round(a, 1),
        "regularnosc": round(b, 1),
        "misje": round(m, 1),
        "osiagniecia": round(o, 1),
    }


def points_in_range(user_id, start, end):
    """Punkty zdobyte w przedziale dat (do rankingow okresowych)."""
    db = get_db()
    a = db.execute(
        "SELECT COALESCE(SUM(points),0) s FROM activities WHERE user_id=? AND date>=? AND date<=?",
        (user_id, start, end),
    ).fetchone()["s"]
    b = 0.0
    for r in db.execute(
        "SELECT week_key, bonus FROM bonuses WHERE user_id=? AND bonus>0", (user_id,)
    ).fetchall():
        mon, sun = week_range(r["week_key"])
        if mon >= start and sun <= end:
            b += r["bonus"]
    m = db.execute(
        """SELECT COALESCE(SUM(m.points),0) s FROM user_missions um
           JOIN missions m ON m.id=um.mission_id
           WHERE um.user_id=? AND um.completed=1
           AND substr(um.completed_at,1,10)>=? AND substr(um.completed_at,1,10)<=?""",
        (user_id, start, end),
    ).fetchone()["s"]
    o = db.execute(
        """SELECT COALESCE(SUM(a.reward_points),0) s FROM user_achievements ua
           JOIN achievements a ON a.id=ua.ach_id WHERE ua.user_id=?
           AND substr(ua.unlocked_at,1,10)>=? AND substr(ua.unlocked_at,1,10)<=?""",
        (user_id, start, end),
    ).fetchone()["s"]
    return round(a + b + m + o, 1)


# --- Agregaty aktywnosci ---
def agg_activities(user_id, start, end, sport="any"):
    db = get_db()
    q = "SELECT type, distance_km, date FROM activities WHERE user_id=? AND date>=? AND date<=?"
    params = [user_id, start, end]
    if sport != "any":
        q += " AND type=?"
        params.append(sport)
    rows = db.execute(q, params).fetchall()
    total = 0.0
    mx = 0.0
    days = set()
    sports = set()
    for r in rows:
        total += r["distance_km"]
        mx = max(mx, r["distance_km"])
        days.add(r["date"])
        sports.add(r["type"])
    return {"sum": round(total, 1), "max_single": mx, "days": days,
            "count": len(rows), "sports": sports}


def user_week_km(user_id):
    """{week_key: {'km': x, 'sports': set, 'days': set, 'sum': {sport: km}}}."""
    db = get_db()
    rows = db.execute(
        "SELECT type, distance_km, date FROM activities WHERE user_id=?", (user_id,)
    ).fetchall()
    out = {}
    for r in rows:
        wk = week_key(r["date"])
        e = out.setdefault(wk, {"km": 0.0, "sports": set(), "days": set(), "sum": {}})
        e["km"] += r["distance_km"]
        e["sports"].add(r["type"])
        e["days"].add(r["date"])
        e["sum"][r["type"]] = e["sum"].get(r["type"], 0.0) + r["distance_km"]
    for e in out.values():
        e["km"] = round(e["km"], 1)
    return out


def user_day_sports(user_id):
    db = get_db()
    rows = db.execute(
        "SELECT type, date FROM activities WHERE user_id=?", (user_id,)
    ).fetchall()
    out = {}
    for r in rows:
        out.setdefault(r["date"], set()).add(r["type"])
    return out


def user_month_km(user_id):
    db = get_db()
    rows = db.execute(
        "SELECT type, distance_km, date FROM activities WHERE user_id=?", (user_id,)
    ).fetchall()
    out = {}
    for r in rows:
        mk = r["date"][:7]
        e = out.setdefault(mk, {"km": 0.0, "days": set(), "sum": {}})
        e["km"] += r["distance_km"]
        e["days"].add(r["date"])
        e["sum"][r["type"]] = e["sum"].get(r["type"], 0.0) + r["distance_km"]
    return out


def longest_streak(user_id):
    db = get_db()
    rows = db.execute(
        "SELECT DISTINCT date FROM activities WHERE user_id=? ORDER BY date", (user_id,)
    ).fetchall()
    if not rows:
        return 0
    days = [date.fromisoformat(r["date"]) for r in rows]
    best = cur = 1
    for i in range(1, len(days)):
        if (days[i] - days[i - 1]).days == 1:
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
    return best


def social_counts(user_id):
    db = get_db()
    g = {}
    g["comments"] = db.execute(
        "SELECT COUNT(*) c FROM comments WHERE user_id=?", (user_id,)).fetchone()["c"]
    g["likes_given"] = db.execute(
        "SELECT COUNT(*) c FROM likes WHERE user_id=?", (user_id,)).fetchone()["c"]
    g["likes_received"] = db.execute(
        """SELECT COUNT(*) c FROM likes l JOIN activities a ON a.id=l.activity_id
           WHERE a.user_id=?""", (user_id,)).fetchone()["c"]
    g["announcements"] = db.execute(
        "SELECT COUNT(*) c FROM announcements WHERE user_id=?", (user_id,)).fetchone()["c"]
    g["joins"] = db.execute(
        "SELECT COUNT(*) c FROM announcement_joins WHERE user_id=?", (user_id,)).fetchone()["c"]
    g["follows"] = db.execute(
        "SELECT COUNT(*) c FROM follows WHERE follower_id=?", (user_id,)).fetchone()["c"]
    g["activities"] = db.execute(
        "SELECT COUNT(*) c FROM activities WHERE user_id=?", (user_id,)).fetchone()["c"]
    g["missions_distinct"] = db.execute(
        """SELECT COUNT(DISTINCT mission_id) c FROM user_missions
           WHERE user_id=? AND completed=1""", (user_id,)).fetchone()["c"]
    g["monthly_mission"] = db.execute(
        """SELECT COUNT(*) c FROM user_missions um JOIN missions m ON m.id=um.mission_id
           WHERE um.user_id=? AND um.completed=1 AND m.kind='miesieczna'""",
        (user_id,)).fetchone()["c"]
    g["achievements"] = db.execute(
        "SELECT COUNT(*) c FROM user_achievements WHERE user_id=?", (user_id,)).fetchone()["c"]
    return g


# --- Regularnosc (bonus cotygodniowy) ---
def award_regularnosc(user_id):
    """Przyznaje bonusy za zakonczone tygodnie. Zwraca liste nowych bonusow."""
    db = get_db()
    rows = db.execute(
        "SELECT DISTINCT date FROM activities WHERE user_id=?", (user_id,)
    ).fetchall()
    by_week = {}
    for r in rows:
        by_week.setdefault(week_key(r["date"]), set()).add(r["date"])
    new = []
    today = today_str()
    for wk, days in by_week.items():
        _mon, sun = week_range(wk)
        if sun >= today:
            continue  # tydzien jeszcze trwa
        exists = db.execute(
            "SELECT id FROM bonuses WHERE user_id=? AND week_key=?", (user_id, wk)
        ).fetchone()
        if exists:
            continue
        n = len(days)
        bonus = 10.0 if n >= 7 else (5.0 if n >= 5 else 0.0)
        db.execute(
            "INSERT INTO bonuses(user_id, week_key, days_active, bonus) VALUES(?,?,?,?)",
            (user_id, wk, n, bonus),
        )
        if bonus > 0:
            new.append({"week_key": wk, "days_active": n, "bonus": bonus})
    db.commit()
    return new


def fix_week_bonus(user_id, wk):
    """Po usunieciu aktywnosci przelicza bonus za dany tydzien."""
    db = get_db()
    mon, sun = week_range(wk)
    n = db.execute(
        "SELECT COUNT(DISTINCT date) c FROM activities WHERE user_id=? AND date>=? AND date<=?",
        (user_id, mon, sun),
    ).fetchone()["c"]
    bonus = 10.0 if n >= 7 else (5.0 if n >= 5 else 0.0)
    db.execute(
        "UPDATE bonuses SET days_active=?, bonus=? WHERE user_id=? AND week_key=?",
        (n, bonus, user_id, wk),
    )
    db.commit()


# --- Misje ---
def mission_progress(m, user_id):
    """Zwraca (progress, target) dla biezacego okresu misji."""
    ct = m["cond_type"]
    sport = m["cond_sport"] or "any"
    val = float(m["cond_value"] or 0)
    period = m["cond_period"] or "day"
    key = current_key(period)
    start, end = period_bounds(period, key)
    sc = social_counts(user_id) if ct in (
        "first_activity", "comments_count", "joins_count", "achievements_count") else None
    if ct == "distance_single":
        agg = agg_activities(user_id, start, end, sport)
        return round(agg["max_single"], 1), val, key
    if ct == "distance_total":
        agg = agg_activities(user_id, start, end, sport)
        return agg["sum"], val, key
    if ct == "active_days":
        agg = agg_activities(user_id, start, end)
        return float(len(agg["days"])), val, key
    if ct == "activities_count":
        agg = agg_activities(user_id, start, end)
        return float(agg["count"]), val, key
    if ct == "variety":
        agg = agg_activities(user_id, start, end)
        return float(len(agg["sports"])), val, key
    if ct == "weekend_both":
        mon, _sun = week_range(current_key("week"))
        sat = (date.fromisoformat(mon) + timedelta(days=5)).isoformat()
        sun = (date.fromisoformat(mon) + timedelta(days=6)).isoformat()
        agg = agg_activities(user_id, sat, sun)
        have = (1 if sat in agg["days"] else 0) + (1 if sun in agg["days"] else 0)
        return float(have), 2.0, current_key("week")
    if ct == "first_activity":
        return min(float(sc["activities"]), 1.0), 1.0, "ever"
    if ct == "comments_count":
        return float(sc["comments"]), val, "ever"
    if ct == "joins_count":
        return float(sc["joins"]), val, "ever"
    if ct == "achievements_count":
        return float(sc["achievements"]), val, "ever"
    return 0.0, val, key


def check_missions(user_id):
    db = get_db()
    missions = db.execute("SELECT * FROM missions WHERE active=1").fetchall()
    done = []
    for m in missions:
        prog, target, key = mission_progress(dict(m), user_id)
        row = db.execute(
            "SELECT * FROM user_missions WHERE user_id=? AND mission_id=? AND period_key=?",
            (user_id, m["id"], key),
        ).fetchone()
        if row and row["completed"]:
            continue
        if prog >= target and target > 0:
            if row:
                db.execute(
                    "UPDATE user_missions SET progress=?, completed=1, completed_at=? WHERE id=?",
                    (prog, now_iso(), row["id"]),
                )
            else:
                db.execute(
                    """INSERT INTO user_missions(user_id, mission_id, period_key, progress, completed, completed_at)
                       VALUES(?,?,?,?,1,?)""",
                    (user_id, m["id"], key, prog, now_iso()),
                )
            done.append({"id": m["id"], "title": m["title"], "points": m["points"],
                         "badge_icon": m["badge_icon"], "avatar_item": m["avatar_item"]})
        else:
            if row:
                db.execute("UPDATE user_missions SET progress=? WHERE id=?", (prog, row["id"]))
            else:
                db.execute(
                    "INSERT INTO user_missions(user_id, mission_id, period_key, progress, completed) VALUES(?,?,?,?,0)",
                    (user_id, m["id"], key, prog),
                )
    db.commit()
    return done


def my_missions(user_id):
    db = get_db()
    missions = db.execute("SELECT * FROM missions WHERE active=1 ORDER BY kind, id").fetchall()
    out = []
    for m in missions:
        md = dict(m)
        prog, target, key = mission_progress(md, user_id)
        row = db.execute(
            "SELECT completed FROM user_missions WHERE user_id=? AND mission_id=? AND period_key=?",
            (user_id, m["id"], key),
        ).fetchone()
        md["progress"] = prog
        md["target"] = target
        md["period_key"] = key
        md["completed"] = bool(row and row["completed"])
        out.append(md)
    return out


# --- Osiagniecia ---
def achievement_met(a, user_id, cache):
    ct = a["cond_type"]
    sport = a["cond_sport"] or "any"
    val = float(a["cond_value"] or 0)
    if ct == "total_distance":
        return cache["totals"].get(sport, 0) >= val
    if ct == "streak":
        return cache["streak"] >= val
    if ct == "month_days":
        return any(len(v["days"]) >= val for v in cache["months"].values())
    if ct == "active_months":
        return len(cache["months"]) >= val
    if ct == "variety_week":
        return any(len(v["sports"]) >= 3 for v in cache["weeks"].values())
    if ct == "all_sports_day":
        return any(len(s) >= 3 for s in cache["daysports"].values())
    if ct == "activities_count":
        return cache["social"]["activities"] >= val
    if ct == "sports_min_each":
        return all(cache["totals"].get(s, 0) >= val for s in ("bieg", "rower", "spacer"))
    if ct == "comments_given":
        return cache["social"]["comments"] >= val
    if ct == "likes_given":
        return cache["social"]["likes_given"] >= val
    if ct == "likes_received":
        return cache["social"]["likes_received"] >= val
    if ct == "announcements_created":
        return cache["social"]["announcements"] >= val
    if ct == "joins_count":
        return cache["social"]["joins"] >= val
    if ct == "follows_count":
        return cache["social"]["follows"] >= val
    if ct == "marathon_month":
        return any(v["sum"].get("bieg", 0) >= 42.2 for v in cache["months"].values())
    if ct == "bike100_week":
        return any(v["sum"].get("rower", 0) >= 100 for v in cache["weeks"].values())
    if ct == "longest_activity":
        return cache["longest_any"] >= val
    if ct == "longest_sport":
        return cache["longest"].get(sport, 0) >= val
    if ct == "points_total":
        return cache["points"] >= val
    if ct == "missions_completed":
        return cache["social"]["missions_distinct"] >= val
    if ct == "monthly_mission":
        return cache["social"]["monthly_mission"] >= 1
    return False


def build_cache(user_id):
    db = get_db()
    rows = db.execute(
        "SELECT type, distance_km, date FROM activities WHERE user_id=?", (user_id,)
    ).fetchall()
    totals = {"any": 0.0, "bieg": 0.0, "rower": 0.0, "spacer": 0.0}
    longest = {"bieg": 0.0, "rower": 0.0, "spacer": 0.0}
    longest_any = 0.0
    for r in rows:
        totals["any"] += r["distance_km"]
        totals[r["type"]] = totals.get(r["type"], 0.0) + r["distance_km"]
        longest[r["type"]] = max(longest.get(r["type"], 0), r["distance_km"])
        longest_any = max(longest_any, r["distance_km"])
    totals = {k: round(v, 1) for k, v in totals.items()}
    return {
        "totals": totals,
        "longest": longest,
        "longest_any": longest_any,
        "weeks": user_week_km(user_id),
        "months": user_month_km(user_id),
        "daysports": user_day_sports(user_id),
        "streak": longest_streak(user_id),
        "social": social_counts(user_id),
        "points": user_points(user_id)["total"],
    }


def check_achievements(user_id):
    db = get_db()
    cache = build_cache(user_id)
    have = {r["ach_id"] for r in db.execute(
        "SELECT ach_id FROM user_achievements WHERE user_id=?", (user_id,)).fetchall()}
    new = []
    for a in db.execute("SELECT * FROM achievements").fetchall():
        if a["id"] in have:
            continue
        if achievement_met(dict(a), user_id, cache):
            db.execute(
                "INSERT INTO user_achievements(user_id, ach_id, unlocked_at) VALUES(?,?,?)",
                (user_id, a["id"], now_iso()),
            )
            new.append({"id": a["id"], "name": a["name"], "icon": a["icon"],
                        "color": a["color"], "reward_points": a["reward_points"],
                        "reward_item": a["reward_item"], "rank": a["rank"]})
            cache["social"]["achievements"] += 1
            cache["points"] += float(a["reward_points"] or 0)
    db.commit()
    return new


# --- Dodawanie aktywnosci (silnik) ---
def add_activity(user_id, sport, km, datestr, provider="manual", duration=0):
    db = get_db()
    pts = points_for(sport, km)
    act_id = insert_get_id(
        """INSERT INTO activities(user_id, provider, type, distance_km, duration_min, date, points)
           VALUES(?,?,?,?,?,?,?)""",
        (user_id, provider, sport, float(km), int(duration or 0), datestr, pts),
    )
    db.commit()
    bonuses = award_regularnosc(user_id)
    # 2 przebiegi, zeby zlapac kaskady misje<->osiagniecia
    ach1 = check_achievements(user_id)
    mis1 = check_missions(user_id)
    ach2 = check_achievements(user_id)
    mis2 = check_missions(user_id)
    return {
        "activity": {"id": act_id, "type": sport, "distance_km": float(km),
                     "date": datestr, "points": pts, "provider": provider},
        "missions": mis1 + [m for m in mis2 if m["id"] not in {x["id"] for x in mis1}],
        "achievements": ach1 + [a for a in ach2 if a["id"] not in {x["id"] for x in ach1}],
        "bonuses": bonuses,
    }


# --- Awatar: dostepne dodatki ---
def earned_reward_items(user_id):
    db = get_db()
    items = set()
    for r in db.execute(
        """SELECT m.avatar_item i FROM user_missions um JOIN missions m ON m.id=um.mission_id
           WHERE um.user_id=? AND um.completed=1 AND m.avatar_item<>''""",
        (user_id,)).fetchall():
        items.add(r["i"])
    for r in db.execute(
        """SELECT a.reward_item i FROM user_achievements ua JOIN achievements a ON a.id=ua.ach_id
           WHERE ua.user_id=? AND a.reward_item<>''""",
        (user_id,)).fetchall():
        items.add(r["i"])
    return items


def available_items(user_id):
    pts = user_points(user_id)["total"]
    earned = earned_reward_items(user_id)
    out = []
    for it in AVATAR_ITEMS:
        out.append({**it, "unlocked": pts >= it["min_points"] or it["id"] in earned,
                    "via_reward": it["id"] in earned})
    return out


# --- Statystyki ---
def stats_user(user_id):
    db = get_db()
    cache = build_cache(user_id)
    pts = user_points(user_id)
    counts = {s: 0 for s in SPORTS}
    for r in db.execute(
        "SELECT type, COUNT(*) c FROM activities WHERE user_id=? GROUP BY type", (user_id,)
    ).fetchall():
        counts[r["type"]] = r["c"]
    # srednia tygodniowa (ostatnie 8 tyg.) i najlepszy tydzien
    t = date.today()
    monday = t - timedelta(days=t.weekday())
    weekly = []
    for i in range(7, -1, -1):
        s = (monday - timedelta(days=7 * i)).isoformat()
        e = (monday - timedelta(days=7 * i) + timedelta(days=6)).isoformat()
        if e > today_str():
            e = today_str()
        weekly.append({"start": s, "end": e, "points": points_in_range(user_id, s, e)})
    avg8 = round(sum(w["points"] for w in weekly) / 8, 1)
    best_w = max(weekly, key=lambda w: w["points"])
    # najlepszy miesiac
    months = sorted(cache["months"].keys())
    best_m = None
    best_mv = -1.0
    for mk in months:
        s, e = month_range(mk)
        v = points_in_range(user_id, s, e)
        if v > best_mv:
            best_mv = v
            best_m = mk
    # pozycja w rankingu szkoly (uczniowie)
    allu = db.execute("SELECT id FROM users WHERE role='uczen'").fetchall()
    totals = sorted(((u["id"], user_points(u["id"])["total"]) for u in allu),
                    key=lambda x: x[1], reverse=True)
    rank = next((i + 1 for i, (uid, _) in enumerate(totals) if uid == user_id), None)
    me = db.execute("SELECT class_id FROM users WHERE id=?", (user_id,)).fetchone()
    class_rank = None
    if me and me["class_id"]:
        mates = db.execute("SELECT id FROM users WHERE role='uczen' AND class_id=?",
                           (me["class_id"],)).fetchall()
        mt = sorted(((u["id"], user_points(u["id"])["total"]) for u in mates),
                    key=lambda x: x[1], reverse=True)
        class_rank = next((i + 1 for i, (uid, _) in enumerate(mt) if uid == user_id), None)
    cur_mk = today_str()[:7]
    pm = (date.today().replace(day=1) - timedelta(days=1)).isoformat()[:7]
    cs, ce = month_range(cur_mk)
    ps, pe = month_range(pm)
    return {
        "points": pts,
        "dist_total": cache["totals"],
        "counts": counts,
        "total_activities": cache["social"]["activities"],
        "weekly_avg8": avg8,
        "best_week": best_w,
        "best_month": {"month": best_m, "points": round(best_mv, 1) if best_mv >= 0 else 0},
        "streak": cache["streak"],
        "missions_done": cache["social"]["missions_distinct"],
        "achievements_count": cache["social"]["achievements"],
        "rank_school": rank,
        "rank_class": class_rank,
        "weekly_series": weekly,
        "month_now": {"month": cur_mk, "points": points_in_range(user_id, cs, ce)},
        "month_prev": {"month": pm, "points": points_in_range(user_id, ps, pe)},
    }


# --- Rankingi ---
def user_row(uid):
    db = get_db()
    r = db.execute(
        """SELECT u.id, u.name, u.role, u.avatar_base, c.name AS class_name
           FROM users u LEFT JOIN classes c ON c.id=u.class_id WHERE u.id=?""",
        (uid,)).fetchone()
    return dict(r) if r else None


def all_totals(role="uczen", class_id=None):
    db = get_db()
    q = "SELECT id FROM users WHERE role=?"
    params = [role]
    if class_id:
        q += " AND class_id=?"
        params.append(class_id)
    users = db.execute(q, params).fetchall()
    out = []
    for u in users:
        info = user_row(u["id"])
        if not info:
            continue
        info["points"] = user_points(u["id"])["total"]
        km = db.execute("SELECT COALESCE(SUM(distance_km),0) s FROM activities WHERE user_id=?",
                        (u["id"],)).fetchone()["s"]
        info["km"] = round(km, 1)
        out.append(info)
    out.sort(key=lambda x: x["points"], reverse=True)
    return out


def rankings_classes():
    db = get_db()
    classes = db.execute("SELECT * FROM classes ORDER BY name").fetchall()
    out = []
    for c in classes:
        members = db.execute("SELECT id FROM users WHERE role='uczen' AND class_id=?",
                             (c["id"],)).fetchall()
        pts = [user_points(m["id"])["total"] for m in members]
        km = db.execute(
            """SELECT COALESCE(SUM(a.distance_km),0) s FROM activities a
               JOIN users u ON u.id=a.user_id WHERE u.class_id=? AND u.role='uczen'""",
            (c["id"],)).fetchone()["s"]
        out.append({"id": c["id"], "name": c["name"], "count": len(members),
                    "sum": round(sum(pts), 1),
                    "avg": round(sum(pts) / len(pts), 1) if pts else 0,
                    "km": round(km, 1)})
    out.sort(key=lambda x: x["avg"], reverse=True)
    return out


def top_period(kind):
    """Top 3 uczniow: week / month / year(szkolny)."""
    t = date.today()
    if kind == "week":
        mon = t - timedelta(days=t.weekday())
        start, end = mon.isoformat(), t.isoformat()
        label = f"tydzie\u0144 {week_key(start)}"
    elif kind == "month":
        start, end = month_range(t.isoformat()[:7])
        end = t.isoformat()
        label = t.strftime("%B %Y")
    else:
        start, end = school_year_start(), t.isoformat()
        label = "rok szkolny"
    db = get_db()
    users = db.execute("SELECT id FROM users WHERE role='uczen'").fetchall()
    scored = []
    for u in users:
        p = points_in_range(u["id"], start, end)
        if p > 0:
            info = user_row(u["id"])
            info["points"] = p
            scored.append(info)
    scored.sort(key=lambda x: x["points"], reverse=True)
    return {"label": label, "start": start, "end": end, "top": scored[:3]}


# --- Ksiega rekordow ---
def records():
    db = get_db()
    users = rows_to_dicts(db.execute("SELECT id FROM users WHERE role='uczen'").fetchall())
    best_week = None  # (km, uid, week)
    for u in users:
        for wk, v in user_week_km(u["id"]).items():
            if best_week is None or v["km"] > best_week[0]:
                best_week = (v["km"], u["id"], wk)
    # klasa: suma km w tygodniu
    classes = rows_to_dicts(db.execute("SELECT * FROM classes").fetchall())
    best_class_week = None
    for c in classes:
        members = db.execute("SELECT id FROM users WHERE role='uczen' AND class_id=?",
                             (c["id"],)).fetchall()
        agg = {}
        for m in members:
            for wk, v in user_week_km(m["id"]).items():
                agg[wk] = agg.get(wk, 0.0) + v["km"]
        for wk, km in agg.items():
            if best_class_week is None or km > best_class_week[0]:
                best_class_week = (round(km, 1), c["id"], c["name"], wk)
    # najwiecej punktow w miesiacu
    best_month = None
    for u in users:
        for mk in user_month_km(u["id"]):
            s, e = month_range(mk)
            p = points_in_range(u["id"], s, e)
            if best_month is None or p > best_month[0]:
                best_month = (p, u["id"], mk)
    # najdluzsza seria
    best_streak = None
    for u in users:
        s = longest_streak(u["id"])
        if best_streak is None or s > best_streak[0]:
            best_streak = (s, u["id"])
    def holder(uid):
        return user_row(uid)
    return {
        "week_distance_user": {"km": best_week[0], "week": best_week[2], "user": holder(best_week[1])} if best_week else None,
        "week_distance_class": {"km": best_class_week[0], "week": best_class_week[3],
                                "class": {"id": best_class_week[1], "name": best_class_week[2]}} if best_class_week else None,
        "month_points": {"points": best_month[0], "month": best_month[2], "user": holder(best_month[1])} if best_month else None,
        "streak": {"days": best_streak[0], "user": holder(best_streak[1])} if best_streak and best_streak[0] > 0 else None,
    }


# --- Konkursy ---
def finish_contest(cid):
    db = get_db()
    c = db.execute("SELECT * FROM contests WHERE id=?", (cid,)).fetchone()
    if not c:
        return None
    users = db.execute("SELECT id FROM users WHERE role='uczen'").fetchall()
    best = None
    for u in users:
        p = points_in_range(u["id"], c["start_date"], c["end_date"])
        if best is None or p > best[0]:
            best = (p, u["id"])
    winner = best[1] if best and best[0] > 0 else None
    db.execute("UPDATE contests SET status='zakonczony', winner_id=? WHERE id=?", (winner, cid))
    db.commit()
    row = db.execute("SELECT * FROM contests WHERE id=?", (cid,)).fetchone()
    d = dict(row)
    d["winner"] = user_row(winner) if winner else None
    d["winner_points"] = best[0] if best else 0
    return d

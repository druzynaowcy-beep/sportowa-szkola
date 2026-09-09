"""Integracja ze Strava API: OAuth2 + import aktywnosci.

Tylko biblioteka standardowa (urllib) - brak dodatkowych zaleznosci.
Dokumentacja Strava: https://developers.strava.com/docs/reference/
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from db import get_db

AUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/api/v3/oauth/token"
ACTS_URL = "https://www.strava.com/api/v3/athlete/activities"
SCOPES = "read,activity:read"

# Mapowanie typow Strava -> nasze sporty (reszta pomijana przy imporcie)
TYPE_MAP = {
    "Run": "bieg", "TrailRun": "bieg",
    "Ride": "rower", "EBikeRide": "rower", "VirtualRide": "rower",
    "Walk": "spacer", "Hike": "spacer",
}


class StravaError(Exception):
    pass


# --- ustawienia (klucze API) ---
def get_setting(key):
    db = get_db()
    r = db.execute('SELECT "value" FROM settings WHERE "key"=?', (key,)).fetchone()
    return r["value"] if r else None


def set_setting(key, value):
    db = get_db()
    db.execute(
        'INSERT INTO settings("key", "value") VALUES(?,?) '
        'ON CONFLICT("key") DO UPDATE SET "value"=excluded."value"', 
        (key, value),
    )
    db.commit()


def del_setting(key):
    db = get_db()
    db.execute('DELETE FROM settings WHERE "key"=?', (key,))
    db.commit()


def get_config():
    cid = (os.environ.get("STRAVA_CLIENT_ID") or get_setting("strava_client_id") or "").strip()
    sec = (os.environ.get("STRAVA_CLIENT_SECRET") or get_setting("strava_client_secret") or "").strip()
    if os.environ.get("STRAVA_CLIENT_ID"):
        src = "env"
    elif get_setting("strava_client_id"):
        src = "panel"
    else:
        src = None
    return {"client_id": cid, "client_secret": sec,
            "configured": bool(cid and sec), "source": src}


# --- OAuth2 ---
def auth_url(client_id, redirect_uri, state):
    q = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "approval_prompt": "auto",
    })
    return AUTH_URL + "?" + q


def _post_form(url, data):
    req = urllib.request.Request(
        url, data=urllib.parse.urlencode(data).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        msg = body
        try:
            msg = json.loads(body).get("message", body)
        except Exception:
            pass
        raise StravaError(f"Strava API (HTTP {e.code}): {str(msg)[:220]}")
    except urllib.error.URLError as e:
        raise StravaError(f"Brak polaczenia ze Strava: {e.reason}")


def exchange_code(cfg, code):
    return _post_form(TOKEN_URL, {
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "code": code,
        "grant_type": "authorization_code",
    })


def refresh_access(cfg, refresh_token):
    try:
        return _post_form(TOKEN_URL, {
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        })
    except StravaError:
        raise StravaError("Token Strava wygasl lub zostal cofniety - polacz konto ponownie.")


# --- tokeny uzytkownikow ---
def get_conn(uid):
    db = get_db()
    return db.execute(
        "SELECT * FROM connections WHERE user_id=? AND provider='strava'", (uid,)).fetchone()


def save_tokens(uid, tok):
    db = get_db()
    athlete = tok.get("athlete") or {}
    name = ((athlete.get("firstname") or "") + " " + (athlete.get("lastname") or "")).strip()
    db.execute(
        """INSERT INTO connections(user_id, provider, connected, access_token, refresh_token,
                                    expires_at, athlete_id, athlete_name)
           VALUES(?,?,?,?,?,?,?,?)
           ON CONFLICT(user_id, provider) DO UPDATE SET connected=1,
             access_token=excluded.access_token, refresh_token=excluded.refresh_token,
             expires_at=excluded.expires_at, athlete_id=excluded.athlete_id,
             athlete_name=excluded.athlete_name""",
        (uid, "strava", 1, tok.get("access_token"), tok.get("refresh_token"),
         tok.get("expires_at"), str(athlete.get("id") or ""), name),
    )
    db.commit()
    return name


def ensure_token(uid, cfg):
    """Zwraca wazny access_token albo None (brak prawdziwego polaczenia)."""
    conn = get_conn(uid)
    if not conn or not conn["access_token"]:
        return None
    if conn["expires_at"] and time.time() < int(conn["expires_at"]) - 60:
        return conn["access_token"]
    tok = refresh_access(cfg, conn["refresh_token"])
    save_tokens(uid, tok)
    return tok.get("access_token")


# --- pobieranie aktywnosci ---
def fetch_recent(access_token, after_ts, max_pages=3):
    out = []
    for page in range(1, max_pages + 1):
        url = ACTS_URL + "?" + urllib.parse.urlencode(
            {"after": int(after_ts), "per_page": 100, "page": page})
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                batch = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise StravaError("Brak autoryzacji Strava - polacz konto ponownie.")
            if e.code == 429:
                raise StravaError("Przekroczono limit zapytan Strava - sprobuj za chwile.")
            raise StravaError(f"Strava API (HTTP {e.code}) - sprobuj ponownie pozniej.")
        except urllib.error.URLError as e:
            raise StravaError(f"Brak polaczenia ze Strava: {e.reason}")
        if not batch:
            break
        out.extend(batch)
        if len(batch) < 100:
            break
    return out


def map_activity(a):
    """Mapuje aktywnosc Strava na nasz format albo zwraca None (pomijana)."""
    sport = TYPE_MAP.get(a.get("type"))
    if not sport:
        return None
    km = round(float(a.get("distance") or 0) / 1000, 2)
    if km < 0.1:
        return None
    day = (a.get("start_date_local") or a.get("start_date") or "")[:10]
    if not day:
        return None
    return {"sport": sport, "km": km, "date": day,
            "dur": int((a.get("moving_time") or 0) // 60),
            "external_id": str(a.get("id")), "name": a.get("name") or ""}

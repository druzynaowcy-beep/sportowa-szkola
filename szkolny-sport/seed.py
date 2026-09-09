"""Dane startowe: klasy, 22 misje, 53 osiagniecia, uzytkownicy demo, przykladowe dane."""
import random
import sys
from datetime import date, timedelta

from flask import Flask
from werkzeug.security import generate_password_hash

from db import get_db, init_db, insert_get_id, migrate, reset_db
import logic
from logic import CATEGORIES

CLASSES = ["4A", "4B", "5A", "5B", "6A", "6B", "7A", "8A"]

# tytul, opis, rodzaj, cond_type, cond_sport, cond_value, cond_period, pkt, ikona, dodatek
MISSIONS = [
    ("Poranny rozruch", "Przebiegnij min. 2 km w ciągu dnia.", "dzienna", "distance_single", "bieg", 2, "day", 5, "🏃", ""),
    ("Rowerowa piątka", "Przejedź min. 5 km rowerem w ciągu dnia.", "dzienna", "distance_single", "rower", 5, "day", 5, "🚴", ""),
    ("Spacerowy relaks", "Przejdź min. 3 km w ciągu dnia.", "dzienna", "distance_single", "spacer", 3, "day", 3, "🚶", ""),
    ("Aktywny dzień", "Zdobądź łącznie min. 5 km dowolną aktywnością w ciągu dnia.", "dzienna", "distance_total", "any", 5, "day", 5, "⭐", ""),
    ("Podwójna dawka", "Wykonaj min. 2 aktywności w ciągu dnia.", "dzienna", "activities_count", "any", 2, "day", 4, "✌️", ""),
    ("Wieczorny maratończyk", "Przebiegnij min. 5 km w ciągu dnia.", "dzienna", "distance_single", "bieg", 5, "day", 8, "🌙", ""),
    ("Biegowy tydzień", "Przebiegnij łącznie 15 km w tygodniu.", "tygodniowa", "distance_total", "bieg", 15, "week", 15, "🏃", ""),
    ("Rowerowy tydzień", "Przejedź łącznie 40 km rowerem w tygodniu.", "tygodniowa", "distance_total", "rower", 40, "week", 15, "🚴", ""),
    ("Spacerowy tydzień", "Przejdź łącznie 20 km w tygodniu.", "tygodniowa", "distance_total", "spacer", 20, "week", 12, "🚶", ""),
    ("Pełny tydzień", "Bądź aktywny w min. 5 dni tygodnia.", "tygodniowa", "active_days", "any", 5, "week", 10, "📅", ""),
    ("Wszechstronny", "Wykonaj wszystkie 3 rodzaje aktywności w tygodniu.", "tygodniowa", "variety", "any", 3, "week", 12, "🎯", ""),
    ("Pięćdziesiątka", "Zdobądź łącznie 50 km w tygodniu.", "tygodniowa", "distance_total", "any", 50, "week", 20, "💪", ""),
    ("Weekendowy wojownik", "Bądź aktywny w sobotę i niedzielę.", "tygodniowa", "weekend_both", "any", 2, "week", 8, "⚔️", ""),
    ("Biegowy miesiąc", "Przebiegnij łącznie 60 km w miesiącu.", "miesieczna", "distance_total", "bieg", 60, "month", 30, "🏃", "medal"),
    ("Rowerowy miesiąc", "Przejedź łącznie 150 km rowerem w miesiącu.", "miesieczna", "distance_total", "rower", 150, "month", 30, "🚴", ""),
    ("Wytrwały piechur", "Przejdź łącznie 80 km w miesiącu.", "miesieczna", "distance_total", "spacer", 80, "month", 25, "🥾", "plecak"),
    ("Miesięczna regularność", "Bądź aktywny w min. 20 dni miesiąca.", "miesieczna", "active_days", "any", 20, "month", 30, "📆", "zlota_opaska"),
    ("Setka", "Zdobądź łącznie 100 km w miesiącu.", "miesieczna", "distance_total", "any", 100, "month", 35, "💯", "puchar"),
    ("Pierwszy krok", "Dodaj swoją pierwszą aktywność.", "okazjonalna", "first_activity", "any", 1, "ever", 5, "👣", ""),
    ("Społecznik", "Skomentuj 3 aktywności kolegów.", "okazjonalna", "comments_count", "any", 3, "ever", 6, "💬", ""),
    ("Wspólny start", "Dołącz do wydarzenia z tablicy ogłoszeń.", "okazjonalna", "joins_count", "any", 1, "ever", 6, "🤝", ""),
    ("Kolekcjoner", "Zdobądź 5 osiągnięć.", "okazjonalna", "achievements_count", "any", 5, "ever", 15, "🏆", "tarcza"),
]

# nazwa, opis, kategoria, ikona, cond_type, cond_sport, cond_value, pkt, dodatek, ranga
ACHIEVEMENTS = [
    ("Pierwsze 10 km", "Przebiegnij łącznie 10 km.", "dystans", "👟", "total_distance", "bieg", 10, 5, "", "latwy"),
    ("Biegowe 25 km", "Przebiegnij łącznie 25 km.", "dystans", "👟", "total_distance", "bieg", 25, 10, "", "latwy"),
    ("Biegowe 50 km", "Przebiegnij łącznie 50 km.", "dystans", "👟", "total_distance", "bieg", 50, 15, "", "sredni"),
    ("Setka biegiem", "Przebiegnij łącznie 100 km.", "dystans", "🏃", "total_distance", "bieg", 100, 25, "buty", "sredni"),
    ("Biegowe 200 km", "Przebiegnij łącznie 200 km.", "dystans", "🏃", "total_distance", "bieg", 200, 40, "", "trudny"),
    ("Biegowe 500 km", "Przebiegnij łącznie 500 km.", "dystans", "🏃", "total_distance", "bieg", 500, 80, "korona", "legendarny"),
    ("Rowerowe 25 km", "Przejedź łącznie 25 km rowerem.", "dystans", "🚲", "total_distance", "rower", 25, 8, "", "latwy"),
    ("Rowerowe 50 km", "Przejedź łącznie 50 km rowerem.", "dystans", "🚲", "total_distance", "rower", 50, 12, "", "latwy"),
    ("Rowerowa setka", "Przejedź łącznie 100 km rowerem.", "dystans", "🚴", "total_distance", "rower", 100, 20, "sluchawki", "sredni"),
    ("Rowerowe 250 km", "Przejedź łącznie 250 km rowerem.", "dystans", "🚴", "total_distance", "rower", 250, 35, "", "trudny"),
    ("Rowerowe 500 km", "Przejedź łącznie 500 km rowerem.", "dystans", "🚴", "total_distance", "rower", 500, 60, "", "trudny"),
    ("Rowerowe 1000 km", "Przejedź łącznie 1000 km rowerem.", "dystans", "🚴", "total_distance", "rower", 1000, 120, "puchar", "legendarny"),
    ("Spacerowe 10 km", "Przejdź łącznie 10 km.", "dystans", "🥾", "total_distance", "spacer", 10, 5, "", "latwy"),
    ("Spacerowe 25 km", "Przejdź łącznie 25 km.", "dystans", "🥾", "total_distance", "spacer", 25, 10, "", "latwy"),
    ("Spacerowe 50 km", "Przejdź łącznie 50 km.", "dystans", "🥾", "total_distance", "spacer", 50, 15, "", "sredni"),
    ("Spacerowa setka", "Przejdź łącznie 100 km.", "dystans", "🚶", "total_distance", "spacer", 100, 25, "plecak", "sredni"),
    ("Spacerowe 250 km", "Przejdź łącznie 250 km.", "dystans", "🚶", "total_distance", "spacer", 250, 40, "", "trudny"),
    ("Łącznie 100 km", "Zdobądź łącznie 100 km dowolnymi aktywnościami.", "dystans", "⭐", "total_distance", "any", 100, 20, "", "sredni"),
    ("Łącznie 500 km", "Zdobądź łącznie 500 km dowolnymi aktywnościami.", "dystans", "🌟", "total_distance", "any", 500, 50, "", "trudny"),
    ("Łącznie 1000 km", "Zdobądź łącznie 1000 km dowolnymi aktywnościami.", "dystans", "💫", "total_distance", "any", 1000, 100, "puchar", "legendarny"),
    ("Seria 3 dni", "Bądź aktywny 3 dni z rzędu.", "regularnosc", "🔥", "streak", "any", 3, 5, "", "latwy"),
    ("Seria 7 dni", "Bądź aktywny 7 dni z rzędu.", "regularnosc", "⭐", "streak", "any", 7, 12, "opaska", "sredni"),
    ("Seria 14 dni", "Bądź aktywny 14 dni z rzędu.", "regularnosc", "🔥", "streak", "any", 14, 25, "", "trudny"),
    ("Seria 30 dni", "Bądź aktywny 30 dni z rzędu.", "regularnosc", "🏆", "streak", "any", 30, 50, "zlota_opaska", "trudny"),
    ("Seria 60 dni", "Bądź aktywny 60 dni z rzędu.", "regularnosc", "💎", "streak", "any", 60, 90, "", "trudny"),
    ("Seria 100 dni", "Bądź aktywny 100 dni z rzędu.", "regularnosc", "👑", "streak", "any", 100, 150, "korona", "legendarny"),
    ("Aktywny miesiąc", "Bądź aktywny w 20 dni jednego miesiąca.", "regularnosc", "📆", "month_days", "any", 20, 25, "", "sredni"),
    ("Trzy miesiące ruchu", "Bądź aktywny w 3 różnych miesiącach.", "regularnosc", "🗓️", "active_months", "any", 3, 20, "", "sredni"),
    ("Wszechstronny", "Wykonaj 3 rodzaje aktywności w jednym tygodniu.", "roznorodnosc", "🎯", "variety_week", "any", 3, 15, "", "sredni"),
    ("Dzień triatlonisty", "Wykonaj 3 rodzaje aktywności jednego dnia.", "roznorodnosc", "⚡", "all_sports_day", "any", 3, 20, "", "trudny"),
    ("50 aktywności", "Wykonaj łącznie 50 aktywności.", "roznorodnosc", "🏁", "activities_count", "any", 50, 20, "", "sredni"),
    ("100 aktywności", "Wykonaj łącznie 100 aktywności.", "roznorodnosc", "🎌", "activities_count", "any", 100, 40, "tarcza", "trudny"),
    ("Każdy sport po 25 km", "Zdobądź min. 25 km w każdym z 3 sportów.", "roznorodnosc", "🧩", "sports_min_each", "any", 25, 30, "", "trudny"),
    ("Pierwszy komentarz", "Skomentuj czyjąś aktywność.", "spolecznosc", "💬", "comments_given", "any", 1, 3, "", "latwy"),
    ("Aktywny komentator", "Napisz 10 komentarzy.", "spolecznosc", "💬", "comments_given", "any", 10, 10, "", "sredni"),
    ("Szkolna gaduła", "Napisz 25 komentarzy.", "spolecznosc", "🗨️", "comments_given", "any", 25, 20, "", "trudny"),
    ("Pierwsze wsparcie", "Polub czyjąś aktywność.", "spolecznosc", "👍", "likes_given", "any", 1, 3, "", "latwy"),
    ("Motywator", "Rozdaj 25 polubień.", "spolecznosc", "💪", "likes_given", "any", 25, 15, "", "sredni"),
    ("Lubiany", "Zbierz 10 polubień pod swoimi aktywnościami.", "spolecznosc", "❤️", "likes_received", "any", 10, 15, "", "sredni"),
    ("Organizator", "Dodaj ogłoszenie na tablicy.", "spolecznosc", "📢", "announcements_created", "any", 1, 5, "", "latwy"),
    ("Drużynowy gracz", "Dołącz do 3 wydarzeń z tablicy.", "spolecznosc", "🤝", "joins_count", "any", 3, 10, "", "sredni"),
    ("Obserwator", "Zaobserwuj 5 osób.", "spolecznosc", "👀", "follows_count", "any", 5, 10, "", "sredni"),
    ("Maraton w miesiącu", "Przebiegnij 42,2 km w jednym miesiącu.", "specjalne", "🏅", "marathon_month", "bieg", 42.2, 50, "medal", "trudny"),
    ("Rowerowa setka w tydzień", "Przejedź 100 km rowerem w jednym tygodniu.", "specjalne", "🚀", "bike100_week", "rower", 100, 40, "", "trudny"),
    ("Ultra dystans", "Wykonaj pojedynczą aktywność min. 30 km.", "specjalne", "🦸", "longest_activity", "any", 30, 40, "", "trudny"),
    ("Półmaraton na raz", "Przebiegnij min. 21,1 km podczas jednego biegu.", "specjalne", "🏃", "longest_sport", "bieg", 21.1, 35, "buty", "trudny"),
    ("Mistrz punktów", "Zdobądź łącznie 2000 pkt.", "specjalne", "💯", "points_total", "any", 2000, 60, "tarcza", "trudny"),
    ("Legenda szkoły", "Zdobądź łącznie 5000 pkt.", "specjalne", "👑", "points_total", "any", 5000, 150, "korona", "legendarny"),
    ("Pierwsza misja", "Ukończ swoją pierwszą misję.", "misje", "🎖️", "missions_completed", "any", 1, 5, "", "latwy"),
    ("Łowca misji", "Ukończ 5 różnych misji.", "misje", "🏹", "missions_completed", "any", 5, 15, "", "sredni"),
    ("Mistrz wyzwań", "Ukończ 10 różnych misji.", "misje", "⭐", "missions_completed", "any", 10, 30, "tarcza", "trudny"),
    ("Niezatrzymany", "Ukończ 20 różnych misji.", "misje", "🌟", "missions_completed", "any", 20, 60, "puchar", "legendarny"),
    ("Miesięczny taktyk", "Ukończ misję miesięczną.", "misje", "🗓️", "monthly_mission", "any", 1, 20, "", "trudny"),
]

USERS = [
    ("admin@szkola.pl", "admin123", "Administrator", "admin", None),
    ("marek.tomaszewski@szkola.pl", "nauczyciel123", "Marek Tomaszewski", "nauczyciel", None),
    ("ewa.dabrowska@szkola.pl", "nauczyciel123", "Ewa Dąbrowska", "nauczyciel", None),
    ("anna.kowalska@szkola.pl", "uczen123", "Anna Kowalska", "uczen", "5A"),
    ("jan.nowak@szkola.pl", "uczen123", "Jan Nowak", "uczen", "5A"),
    ("zofia.wisniewska@szkola.pl", "uczen123", "Zofia Wiśniewska", "uczen", "6B"),
    ("kacper.wojcik@szkola.pl", "uczen123", "Kacper Wójcik", "uczen", "6B"),
    ("maria.kaminska@szkola.pl", "uczen123", "Maria Kamińska", "uczen", "4A"),
    ("piotr.lewandowski@szkola.pl", "uczen123", "Piotr Lewandowski", "uczen", "4A"),
    ("aleksandra.zielinska@szkola.pl", "uczen123", "Aleksandra Zielińska", "uczen", "7A"),
    ("jakub.szymanski@szkola.pl", "uczen123", "Jakub Szymański", "uczen", "8A"),
]

BASES = ["chlopiec", "dziewczynka", "sportowiec", "biegacz", "rowerzysta",
         "maratonczyk", "kaptur", "super", "mistrz"]


def add_act(db, uid, sport, km, d, provider="manual"):
    dur = int(km * {"bieg": 6, "rower": 3, "spacer": 10}[sport])
    db.execute(
        """INSERT INTO activities(user_id, provider, type, distance_km, duration_min, date, points)
           VALUES(?,?,?,?,?,?,?)""",
        (uid, provider, sport, km, dur, d, logic.points_for(sport, km)))


def seed():
    init_db()
    migrate()
    app = Flask(__name__)
    with app.app_context():
        db = get_db()
        if db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"] > 0:
            print("Baza zawiera juz uzytkownikow - pomijam seedowanie (uzyj --reset).")
            return
        random.seed(42)
        today = date.today()

        for name in CLASSES:
            db.execute("INSERT INTO classes(name) VALUES(?)", (name,))
        class_id = {r["name"]: r["id"] for r in
                    db.execute("SELECT * FROM classes").fetchall()}

        for m in MISSIONS:
            db.execute(
                """INSERT INTO missions(title, description, kind, cond_type, cond_sport,
                                        cond_value, cond_period, points, badge_icon, avatar_item, active)
                   VALUES(?,?,?,?,?,?,?,?,?,?,1)""", m)
        for a in ACHIEVEMENTS:
            name, desc, cat, icon, ct, sport, val, pts, item, rank = a
            db.execute(
                """INSERT INTO achievements(name, description, category, icon, color, cond_type,
                                            cond_sport, cond_value, reward_points, reward_item, "rank")
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (name, desc, cat, icon, CATEGORIES[cat]["color"], ct, sport, val, pts, item, rank))

        uids = {}
        for i, (email, pw, name, role, cls) in enumerate(USERS):
            uids[email] = insert_get_id(
                "INSERT INTO users(email, password_hash, name, role, class_id, avatar_base) VALUES(?,?,?,?,?,?)",
                (email, generate_password_hash(pw), name, role,
                 class_id.get(cls) if cls else None, BASES[i % len(BASES)]))

        anna = uids["anna.kowalska@szkola.pl"]
        jan = uids["jan.nowak@szkola.pl"]
        zofia = uids["zofia.wisniewska@szkola.pl"]
        kacper = uids["kacper.wojcik@szkola.pl"]
        maria = uids["maria.kaminska@szkola.pl"]
        piotr = uids["piotr.lewandowski@szkola.pl"]
        ola = uids["aleksandra.zielinska@szkola.pl"]
        kuba = uids["jakub.szymanski@szkola.pl"]
        marek = uids["marek.tomaszewski@szkola.pl"]
        ewa = uids["ewa.dabrowska@szkola.pl"]

        for uid, prov in [(anna, "strava"), (jan, "garmin"), (zofia, "googlefit"),
                          (kacper, "strava"), (maria, "applehealth"), (piotr, "strava"),
                          (marek, "garmin")]:
            db.execute("INSERT INTO connections(user_id, provider, connected) VALUES(?,?,1)",
                       (uid, prov))

        # Anna: seria 14 dni + wczesniejsze aktywnosci
        sports_cycle = ["bieg", "spacer", "rower", "bieg", "rower", "spacer", "bieg"]
        for i in range(13, -1, -1):
            d = (today - timedelta(days=i)).isoformat()
            s = sports_cycle[i % len(sports_cycle)]
            km = {"bieg": round(random.uniform(3, 6), 1),
                  "rower": round(random.uniform(8, 15), 1),
                  "spacer": round(random.uniform(2, 4), 1)}[s]
            add_act(db, anna, s, km, d, "strava")
        for i in range(14, 45):
            if random.random() < 0.55:
                d = (today - timedelta(days=i)).isoformat()
                s = random.choice(["bieg", "rower", "spacer"])
                add_act(db, anna, s, round(random.uniform(2, 8), 1), d, "strava")

        # Jan: kolarz, 8 tygodni; tydzien -3 z setka rowerowa
        monday = today - timedelta(days=today.weekday())
        for w in range(8):
            wk_mon = monday - timedelta(weeks=w)
            if w == 3:
                for dd, km in [(0, 25.0), (2, 25.0), (4, 25.0), (6, 32.0)]:
                    add_act(db, jan, "rower", km, (wk_mon + timedelta(days=dd)).isoformat(), "garmin")
            else:
                for dd in (1, 3, 6):
                    if random.random() < 0.85:
                        add_act(db, jan, "rower", round(random.uniform(12, 30), 1),
                                (wk_mon + timedelta(days=dd)).isoformat(), "garmin")
        add_act(db, jan, "bieg", 4.0, (today - timedelta(days=2)).isoformat(), "garmin")

        # Zofia: biegaczka z maratonem w poprzednim miesiacu
        prev_month = (today.replace(day=1) - timedelta(days=1))
        for dd, km in [(3, 8.0), (10, 10.0), (17, 12.0), (24, 15.5)]:
            try:
                d = prev_month.replace(day=min(dd, 28)).isoformat()
                add_act(db, zofia, "bieg", km, d, "googlefit")
            except ValueError:
                pass
        for i in range(0, 50):
            if random.random() < 0.3:
                d = (today - timedelta(days=i)).isoformat()
                add_act(db, zofia, random.choice(["bieg", "bieg", "spacer"]),
                        round(random.uniform(3, 9), 1), d, "googlefit")

        # Pozostali: losowe aktywnosci z 6 tygodni
        for uid, prov in [(kacper, "strava"), (maria, "applehealth"), (piotr, "strava"),
                          (ola, "manual"), (kuba, "manual")]:
            for i in range(0, 42):
                if random.random() < 0.35:
                    d = (today - timedelta(days=i)).isoformat()
                    s = random.choice(["bieg", "rower", "spacer"])
                    km = {"bieg": round(random.uniform(1.5, 9), 1),
                          "rower": round(random.uniform(5, 25), 1),
                          "spacer": round(random.uniform(1, 6), 1)}[s]
                    add_act(db, uid, s, km, d, prov)

        # Nauczyciele: kilka aktywnosci
        for i in range(0, 30):
            if random.random() < 0.25:
                d = (today - timedelta(days=i)).isoformat()
                add_act(db, marek, random.choice(["bieg", "rower"]),
                        round(random.uniform(3, 12), 1), d, "garmin")
                add_act(db, ewa, "spacer", round(random.uniform(2, 6), 1), d, "manual")
        db.commit()

        # Ogloszenia
        db.execute(
            "INSERT INTO announcements(user_id, title, content, event_date) VALUES(?,?,?,?)",
            (marek, "Sobota 10:00 - wspólny bieg w parku",
             "Spotykamy się przy wejściu głównym do parku. Tempo spokojne, każdy da radę!",
             (today + timedelta(days=(5 - today.weekday()) % 7 or 7)).isoformat()))
        db.execute(
            "INSERT INTO announcements(user_id, title, content, event_date) VALUES(?,?,?,?)",
            (anna, "Rowerowa niedziela nad rzeką",
             "Łatwa trasa ok. 20 km. Zabierzcie kaski i wodę!", (today + timedelta(days=6)).isoformat()))
        db.execute(
            "INSERT INTO announcements(user_id, title, content, event_date) VALUES(?,?,?,?)",
            (uids["admin@szkola.pl"], "Konkurs: Wrześniowe wyzwanie!",
             "Przez cały wrzesień zbieramy punkty. Zwycięzca dostanie dyplom i punkty z WF-u!",
             ""))
        for aid_row in db.execute("SELECT id FROM announcements").fetchall():
            for uid in random.sample([anna, jan, zofia, kacper, maria, piotr, ola, kuba],
                                     k=random.randint(2, 5)):
                db.execute("INSERT INTO announcement_joins(announcement_id, user_id) VALUES(?,?) ON CONFLICT DO NOTHING",
                           (aid_row["id"], uid))

        # Polubienia, komentarze, obserwacje
        acts = [r["id"] for r in db.execute("SELECT id FROM activities ORDER BY id DESC LIMIT 60").fetchall()]
        students = [anna, jan, zofia, kacper, maria, piotr, ola, kuba]
        for aid in random.sample(acts, k=min(30, len(acts))):
            for uid in random.sample(students, k=random.randint(0, 3)):
                db.execute("INSERT INTO likes(activity_id, user_id) VALUES(?,?) ON CONFLICT DO NOTHING", (aid, uid))
        comments_txt = ["Świetny wynik! 🔥", "Brawo! 👏", "Też tak chcę! 💪",
                        "Super tempo!", "Gratulacje! 🎉", "Motywujesz mnie! ⭐"]
        for aid in random.sample(acts, k=min(15, len(acts))):
            for uid in random.sample(students, k=random.randint(1, 2)):
                db.execute("INSERT INTO comments(activity_id, user_id, content) VALUES(?,?,?)",
                           (aid, uid, random.choice(comments_txt)))
        for uid in students:
            for other in random.sample([s for s in students if s != uid], k=random.randint(1, 4)):
                db.execute("INSERT INTO follows(follower_id, followed_id) VALUES(?,?) ON CONFLICT DO NOTHING",
                           (uid, other))
        db.commit()

        # Konkursy
        first = today.replace(day=1).isoformat()
        import calendar as _cal
        last = today.replace(day=_cal.monthrange(today.year, today.month)[1]).isoformat()
        db.execute("INSERT INTO contests(title, description, start_date, end_date) VALUES(?,?,?,?)",
                   ("Wrześniowe wyzwanie", "Kto zbierze najwięcej punktów w tym miesiącu? Nagrody: dyplom i punkty z WF-u!",
                    first, last))
        pm = (today.replace(day=1) - timedelta(days=1))
        pm_last = pm.replace(day=_cal.monthrange(pm.year, pm.month)[1]).isoformat()
        new_cid = insert_get_id("INSERT INTO contests(title, description, start_date, end_date) VALUES(?,?,?,?)",
                         ("Sierpniowe ściganie", "Miesięczne wyzwanie sierpniowe.", pm.replace(day=1).isoformat(), pm_last))
        db.commit()
        logic.finish_contest(new_cid)

        # Silnik: bonusy, misje, osiagniecia dla wszystkich
        for r in db.execute("SELECT email FROM users").fetchall():
            email = r["email"]
            uid = uids[email]
            logic.award_regularnosc(uid)
            logic.check_achievements(uid)
            logic.check_missions(uid)
            logic.check_achievements(uid)
        db.commit()
        print(f"Zaseedowano: misje={len(MISSIONS)}, osiagniecia={len(ACHIEVEMENTS)}, uzytkownicy={len(USERS)}")


if __name__ == "__main__":
    if "--reset" in sys.argv:
        reset_db()
        print("Wyczyszczono baze.")
    seed()

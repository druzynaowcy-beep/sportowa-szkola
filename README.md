# 🏆 Sportowa Szkoła (MVP)

Szkolna platforma sportowa dla jednej szkoły podstawowej: uczniowie łączą konta
sportowe, zbierają punkty za aktywności, realizują misje, zdobywają odznaki,
rozwijają awatary i rywalizują w rankingach.

## Uruchomienie

```bash
cd szkolny-sport
pip install -r requirements.txt
python3 seed.py --reset   # tworzy bazę + konta demo + 22 misje + 53 osiągnięcia
python3 app.py            # start serwera na http://localhost:5000
```

Zadania cykliczne (bonusy, zamykanie konkursów) – opcjonalnie (bonusy naliczają się też przy każdej aktywności, a konkursy domykają się przy podglądzie) – raz dziennie, np. cron o północy:

```bash
curl http://localhost:5000/api/cron/daily
```

## Konta demo (hasła w `seed.py`)

| Rola | E-mail | Hasło |
|---|---|---|
| Admin | admin@szkola.pl | admin123 |
| Nauczyciel | marek.tomaszewski@szkola.pl | nauczyciel123 |
| Nauczyciel | ewa.dabrowska@szkola.pl | nauczyciel123 |
| Uczniowie (8) | np. anna.kowalska@szkola.pl | uczen123 |

## Zrealizowane funkcje (wg briefu)

- **2.1** Rejestracja/logowanie e-mail + hasło, wybór klasy, role: uczeń / nauczyciel / admin.
- **2.2** Łączenie kont Strava / Garmin / Google Fit / Apple Health (**MVP: symulacja** –
  przycisk „Synchronizuj” generuje aktywności; architektura gotowa pod OAuth, patrz niżej).
- **2.3–2.4** Aktywności: bieg (1,5 pkt/km), rower (0,8 pkt/km), spacer (1 pkt/km).
- **2.5** Bonus za regularność: 5 dni → +5 pkt, 7 dni → +10 pkt (rozliczany co tydzień).
- **2.6** 22 misje (dzienne/tygodniowe/miesięczne/okazjonalne), auto-sprawdzanie, pasek postępu.
- **2.7** 53 osiągnięcia w 6 kategoriach, odznaki SVG w 2 stanach (szara/kolorowa), rangi,
  efekt „shine” dla legendarnych, klik = szczegóły.
- **2.8** Statystyki: dystanse, liczby aktywności, podział punktów, śr. tygodniowa,
  najlepszy tydzień/miesiąc, serie + wykresy (słupkowe, donut) bez zewnętrznych bibliotek.
- **2.9** Rankingi: indywidualny (paginacja + filtr klasy), moja klasa, klasy (średnia/suma),
  nauczycielski.
- **2.10** Najbardziej aktywni: tydzień / miesiąc / rok szkolny (top 3 na głównej).
- **2.11** Awatar: 9 postaci + 16 dodatków odblokowywanych punktami lub nagrodami.
- **2.12** Księga rekordów (auto-aktualizacja).
- **2.13** Tablica ogłoszeń + „Dołączę”.
- **2.14** Polubienia, komentarze, obserwowanie znajomych.
- **2.15** Konkursy okresowe + automatyczne wyłanianie zwycięzcy.
- **2.16** Panel admina: użytkownicy (CRUD, zmiana klasy/roli), klasy, misje (CRUD),
  konkursy, statystyki szkoły, eksport CSV (użytkownicy / aktywności / punkty).
- RODO: zgoda przy rejestracji, strona polityki, usuwanie użytkownika z danymi.

## Struktura

```
app.py      – aplikacja Flask, API REST, serwowanie frontendu
db.py       – schemat SQLite + połączenia
logic.py    – silnik: punkty, bonusy, misje, osiągnięcia, rankingi, rekordy
seed.py     – dane startowe (misje, osiągnięcia, demo)
static/     – frontend SPA bez frameworków: index.html, style.css,
              app.js (rdzeń), views.js (podstrony), charts.js (wykresy SVG)
sport.db    – baza SQLite (tworzona automatycznie)
```

## API (skrót)

- `POST /api/register|/login|/logout`, `GET/PUT /api/me`
- `GET /api/classes`, `GET /api/meta`
- `POST/DELETE /api/connect/<provider>`, `POST /api/sync/<provider>`
- `GET/POST /api/activities`, `DELETE /api/activities/<id>`
- `POST/DELETE /api/activities/<id>/like`, `GET/POST /api/activities/<id>/comments`
- `GET /api/stats/mine`, `GET /api/stats/user/<id>`
- `GET /api/rankings/individual|/classes`, `GET /api/top`, `GET /api/records`
- `GET /api/missions`, `GET /api/achievements`, `GET /api/avatar`
- `GET/POST/DELETE /api/announcements…`, `POST/DELETE …/join`
- `GET/POST /api/contests`, `POST /api/contests/<id>/finish`
- `POST/DELETE /api/follow/<id>`, `GET /api/users/<id>`
- `/api/admin/*` – użytkownicy, klasy, misje, przegląd, eksport CSV
- `GET /api/cron/daily`

## Prawdziwa integracja Strava ✅

Działa pełny przepływ OAuth2 + import aktywności (bieg/rower/spacer z 30 dni,
bez duplikatów, automatyczne odświeżanie tokenów):

1. Na **strava.com → Ustawienia → Moje API** (`strava.com/settings/api`) utwórz
   aplikację (darmowe).
2. W polu **Authorization Callback Domain** wpisz domenę serwera – dokładny adres
   zwrotny pokazuje panel admina (zakładka **Integracje**).
3. Przepisz **Client ID** i **Client Secret** do panelu admina (zakładka
   Integracje) albo ustaw zmienne środowiskowe `STRAVA_CLIENT_ID` /
   `STRAVA_CLIENT_SECRET`.
4. Uczniowie klikają w profilu **„Połącz przez Strava”**, logują się Stravą
   i synchronizują prawdziwe treningi. Bez kluczy działa tryb demo.

Endpointy: `GET /strava/connect`, `GET /strava/callback`,
`GET /api/strava/status`, `/api/admin/integrations/*`.
Kod: `strava_client.py` (tylko biblioteka standardowa).

**Logowanie przez Stravę:** przycisk na stronie logowania/rejestracji
(`GET /strava/login` → `GET /strava/login-callback`). Znany sportowiec jest
logowany, nowy – rejestrowany automatycznie (rola uczeń, klasa do wyboru
przy pierwszym logowaniu, jednorazowo).

## Przejście na prawdziwe integracje (po MVP)

- **Strava** – gotowe (patrz wyżej).
- **Garmin / Polar / Suunto / Coros / Apple Watch / Samsung / Amazfit / Huawei… –
  przez Stravę (oficjalna synchronizacja po stronie użytkownika).** Bezpośrednie
  API Garmina wymaga umowy partnerskiej i konta firmowego (program dla nowych
  deweloperów jest obecnie wręcz zawieszony), Google Fit zamyka swoje API
  (zapisy nowych deweloperów wstrzymane od 05.2024, koniec wsparcia: koniec 2026),
  a Apple HealthKit działa tylko wewnątrz aplikacji na iPhone'a. Wszystkie te
  urządzenia potrafią automatycznie przesyłać treningi do Stravy – uczeń włącza
  to raz w aplikacji zegarka (Ustawienia → Połączone aplikacje), a nasz import
  ze Stravy pobiera je dalej. Zero dodatkowego kodu.
- Opcja V2 (płatna): agregator typu Terra/Vital – jedno API do setek urządzeń.
- Cykliczna synchronizacja (cron co 6 h) dla połączonych kont – do dodania wg potrzeb.

## Wdrożenie produkcyjne (checklista)

- `SECRET_KEY` z zmiennej środowiskowej, `debug=False`, HTTPS (reverse proxy).
- Migracja SQLite → PostgreSQL przy większej liczbie użytkowników.
- Uzupełnij dane administratora na stronie RODO, dodaj zgodę rodzica dla <16 lat.
- Rozważ logowanie Google/Microsoft (V2) i powiadomienia e-mail/push.

## Wdrożenie za darmo

Patrz **deploy/DEPLOY.md** – instrukcja krok po kroku:
Render + Neon (najprościej: prawdziwa baza, pełna Strava, ~20 minut), PythonAnywhere (~10 minut) oraz Oracle Always Free VPS
(pełny serwer). Pakiet zawiera gotowe pliki: WSGI, systemd, Nginx, skrypt
instalacyjny i cron.

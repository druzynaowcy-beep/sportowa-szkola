# 🚀 Wdrożenie „Sportowej Szkoły” ZA DARMO

Aplikacja to Python (Flask) + baza danych (SQLite lokalnie, PostgreSQL na produkcji).
Poniżej 3 sprawdzone darmowe opcje. **Polecam C na start** (20 minut, bez karty,
pełny internet dla Stravy), A gdy wolisz klikanie bez GitHuba,
a **B jako docelową** (pełny serwer, zero limitów).

> Porównania darmowych hostingów dla Flaska (2026): PythonAnywhere jako
> najłatwiejszy dla początkujących, Oracle Cloud Free Tier jako opcja
> „maksymalna kontrola za darmo”, a Render + darmowy PostgreSQL w chmurze
> jako najprostszy start z prawdziwą bazą produkcyjną.

---

## Opcja A: PythonAnywhere – plan Beginner ($0, ~10 minut) ✅ POLECANE NA START

**Co dostajesz:** adres `twojanazwa.pythonanywhere.com` (z HTTPS), trwały dysk
(baza SQLite bezpieczna). Bez karty. (Plan darmowy nie ma wbudowanych zadań cyklicznych, ale aplikacja ich nie wymaga – patrz krok 8.)
Limity: 100 sek. CPU dziennie (dla szkoły wystarczy), brak własnej domeny,
połączenia zewnętrzne tylko do popularnych serwisów (Strava może wymagać
dopisania do listy – patrz „Uwaga o Stravie” niżej).

### Krok po kroku

1. Załóż konto na **pythonanywhere.com** (plan Beginner, darmowy).
2. Spakuj folder `szkolny-sport` do ZIP-a na swoim komputerze
   (bez pliku `sport.db` – bazę utworzymy na serwerze).
3. W PythonAnywhere otwórz zakładkę **Files** → wgraj ZIP → otwórz **Bash console** i wykonaj:
   ```bash
   cd ~
   unzip szkolny-sport.zip
   cd szkolny-sport
   mkvirtualenv --python=/usr/bin/python3.11 sport
   pip install -r requirements.txt
   ```
4. Utwórz świeżą bazę (bez danych demo) i pierwszego admina:
   ```bash
   python3 -c "from db import init_db, migrate; init_db(); migrate()"
   ```
   Pierwsza zarejestrowana osoba na stronie automatycznie zostaje **adminem**
   – zarejestruj więc najpierw siebie. (Wolisz dane demo? Zamiast tego:
   `python3 seed.py --reset`, a potem zmień hasła!)
5. Zakładka **Web** → **Add a new web app** → wybierz **Manual configuration**
   (Python 3.11) → w sekcji **Virtualenv** wpisz `/home/TWOJLOGIN/.virtualenvs/sport`.
6. W sekcji **Code** ustaw **Source code** na `/home/TWOJLOGIN/szkolny-sport`,
   a w **WSGI configuration file** wklej zawartość pliku
   `deploy/pythonanywhere_wsgi.py` z tego pakietu (podmień `TWOJLOGIN`
   i wygeneruj własny `SECRET_KEY`, np. komendą:
   `python3 -c "import secrets; print(secrets.token_hex(32))"`).
7. Kliknij **Reload** – strona działa pod `https://TWOJLOGIN.pythonanywhere.com` 🎉
8. (Opcjonalnie, możesz pominąć) Plan darmowy nie ma wbudowanych zadań cyklicznych
   (zakładka Tasks jest tylko na planach płatnych) – ale **nie są potrzebne**:
   bonusy za regularność naliczają się przy każdej aktywności, a zaległe konkursy
   zamykają się same przy otwarciu strony konkursów. Jeśli chcesz, możesz dodać
   darmowy zewnętrzny cron (np. cron-job.org), który raz dziennie otworzy adres:
   `https://TWOJLOGIN.pythonanywhere.com/api/cron/daily`
9. Zaloguj się, zmień hasło w profilu (karta „Zmiana hasła”) i wpisz klucze
   Strava w panelu admina (zakładka **Integracje**).

**Backup bazy:** co jakiś czas pobierz plik `sport.db` z zakładki Files.

### ⚠️ Uwaga o Stravie na darmowym PythonAnywhere
Darmowe konta mogą łączyć się tylko z serwisami z listy dozwolonych.
Jeśli synchronizacja ze Stravą zgłosi błąd połączenia:
- poproś o dopisanie `strava.com` / `www.strava.com` na forum PythonAnywhere, albo
- przejdź na plan Hacker (~5 $/mies., pełny internet), albo
- wybierz **Opcję B** (VPS bez żadnych ograniczeń).

---

## Opcja B: Oracle Cloud Always Free – własny serwer VPS (na zawsze darmowy)

**Co dostajesz:** prawdziwy serwer (maszyna ARM, do 24 GB RAM w puli Always Free),
własna domena, pełny internet (Strava działa bez ograniczeń), cron.
Wymaga karty do weryfikacji konta (bez opłat) i ok. 1 godziny pracy.

### Krok po kroku (skrót – szczegóły wykonuje skrypt)

1. Załóż konto **Oracle Cloud** (Always Free), utwórz instancję
   **Ubuntu 24.04** (ARM Ampere, 1–4 OCPU, 6–24 GB RAM – w limicie darmowym).
   W regułach sieci (Security List) odblokuj porty **80** i **443**.
2. Połącz się przez SSH i wgraj pliki projektu do `/tmp/deploy`
   (np. programem WinSCP / komendą `scp -r szkolny-sport/* ubuntu@SERWER:/tmp/deploy/`).
3. Uruchom dołączony skrypt (instaluje Pythona, Nginx, usługę systemową, cron):
   ```bash
   chmod +x /tmp/deploy/deploy/oracle-setup.sh
   sudo /tmp/deploy/deploy/oracle-setup.sh
   ```
4. (Opcjonalnie, własna domena + HTTPS): skieruj rekord A domeny na IP serwera
   i wykonaj:
   ```bash
   sudo apt install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d twojadomena.pl
   ```
5. Otwórz stronę, zarejestruj się jako pierwszy (zostaniesz adminem),
   zmień hasło, wpisz klucze Strava. Gotowe 🎉

**Backup bazy:** `scp ubuntu@SERWER:/opt/sportowa-szkola/sport.db backup.db`

---

## Opcja C: Render + Neon – darmowy hosting i baza PostgreSQL (~20 minut) ✅ POLECANE NA START

**Co dostajesz:** adres `twojanazwa.onrender.com` (z HTTPS), darmową bazę
PostgreSQL w chmurze (Neon, 0,5 GB – wystarczy na lata szkolnego użytku)
oraz pełny internet (Strava działa bez żadnych ograniczeń). Bez karty.
Uwaga: na Renderze NIE używamy SQLite (dysk jest ulotny – plik bazy znikałby
przy każdym restarcie), dlatego baza stoi na zewnątrz, w Neonie.
Limity: po ~15 minutach bez ruchu strona usypia i pierwsze otwarcie trwa
~30–60 s (normalne na darmowym planie); baza Neon też usypia po 5 minutach
bezczynności i budzi się w ~1 s.

### Krok po kroku

1. Załóż darmowe konto na **neon.tech** (możesz przez „Sign up with GitHub” –
   konto GitHub przyda się w kroku 3). Utwórz projekt (nazwa np. `sportowa-szkola`,
   region np. `Frankfurt`), a następnie w panelu projektu skopiuj
   **Connection string** (zakładka *Connect*, format `postgresql://...`).
   Upewnij się, że na końcu jest `?sslmode=require` (jeśli nie – dopisz).
2. Na swoim komputerze rozpakuj ZIP-a z aplikacją.
3. Załóż darmowe konto na **github.com** → **New repository**
   (nazwa np. `sportowa-szkola`, Public) → na stronie repozytorium wybierz
   **„uploading an existing file”** i przeciągnij wszystkie pliki z folderu
   (bez `sport.db`, jeśli istnieje) → **Commit changes**.
   Ważne: pliki `app.py`, `requirements.txt` i `render.yaml` muszą leżeć
   w głównym katalogu repozytorium, nie w podfolderze.
4. Załóż darmowe konto na **render.com** (najwygodniej „Sign up with GitHub”)
   → **New → Web Service** → wybierz repozytorium `sportowa-szkola`.
   Plik `render.yaml` uzupełni większość pól sam – sprawdź:
   - **Runtime:** Python, **Plan:** Free,
   - **Build Command:** `pip install -r requirements.txt`,
   - **Start Command:** `gunicorn -w 2 -b 0.0.0.0:$PORT app:app`.
5. W sekcji **Environment Variables** dodaj:
   - `DATABASE_URL` = connection string z Neona (z kroku 1),
   - `SECRET_KEY` = kliknij **Generate** (losowa wartość).
6. Kliknij **Create Web Service** i poczekaj ~3–5 minut na pierwsze wdrożenie.
7. Gdy status to **Live**, otwórz **Shell** (przycisk w panelu usługi) i wykonaj:
   ```bash
   python seed.py --reset
   ```
   To utworzy strukturę bazy i dane startowe (misje, osiągnięcia, konta demo).
   **Zmień potem hasła do kont demo!** (Wolisz pustą bazę? Zamiast seeda wykonaj:
   `python -c "from db import init_db, migrate; init_db(); migrate()"` –
   pierwsza zarejestrowana osoba zostanie wtedy adminem.)
8. Otwórz stronę `https://twojanazwa.onrender.com` – działa 🎉
9. Zaloguj się, zmień hasło w profilu (karta „Zmiana hasła”) i wpisz klucze
   Stravy w panelu admina (zakładka **Integracje**).

**Aktualizacja strony:** wgraj zmienione pliki na GitHuba (na stronie repo:
*Add file → Upload files*), a Render sam pobierze nową wersję i wdroży ją
w kilka minut.

**Backup bazy:** panel Neona → projekt → *Backups* (automatyczne kopie
w cenie planu darmowego) albo eksport CSV z panelu admina strony.

---

## Po wdrożeniu (wszystkie opcje)

1. **Strava:** w ustawieniach aplikacji Strava (`strava.com/settings/api`)
   w polu **Authorization Callback Domain** wpisz domenę wdrożenia
   (np. `twojlogin.pythonanywhere.com` – samą domenę, bez `https://`).
   Dokładny adres zwrotny pokazuje panel admina → **Integracje**.
2. **Pierwszy użytkownik = admin** (tylko przy pustej bazie).
3. **Zmień hasła startowe** (profil → „Zmiana hasła”).
4. **Nie publikuj** pliku `sport.db` ani kluczy API w internecie.

## Dlaczego nie Railway / Vercel (darmowe)?
Railway działa na zużywalnych kredytach (strona może nagle przestać działać
po ich wyczerpaniu), a Vercel/Netlify to hosting pod strony statyczne/serverless –
nasza aplikacja potrzebuje zwykłego serwera Pythona z bazą danych.
Dlatego: Render + Neon, PythonAnywhere albo Oracle VPS.

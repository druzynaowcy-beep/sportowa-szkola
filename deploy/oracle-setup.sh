#!/bin/bash
# Instalacja "Sportowej Szkoly" na VPS z Ubuntu (np. Oracle Always Free).
# Uruchomienie: sudo ./oracle-setup.sh
# Wczesniej wgraj pliki projektu do /tmp/deploy (scp lub WinSCP).
set -e
APP_DIR=/opt/sportowa-szkola
SRC=/tmp/deploy

echo "==> Pakiety systemowe..."
apt-get update
apt-get install -y python3 python3-venv nginx curl

echo "==> Katalog aplikacji..."
mkdir -p "$APP_DIR"
cp -r "$SRC"/app.py "$SRC"/db.py "$SRC"/logic.py "$SRC"/seed.py "$SRC"/strava_client.py "$SRC"/requirements.txt "$SRC"/static "$SRC"/deploy "$APP_DIR"/

echo "==> Srodowisko Python..."
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt" gunicorn

echo "==> Baza danych (pusta; pierwszy zarejestrowany = admin)..."
cd "$APP_DIR"
"$APP_DIR/venv/bin/python" -c "from db import init_db, migrate; init_db(); migrate()"

echo "==> Sekret aplikacji..."
SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
sed "s/TUTAJ-WKLEJ-DLUGI-LOSOWY-SEKRET/$SECRET/" "$APP_DIR/deploy/sportowa-szkola.service" > /etc/systemd/system/sportowa-szkola.service

echo "==> Uprawnienia, usluga, nginx..."
chown -R www-data:www-data "$APP_DIR"
systemctl daemon-reload
systemctl enable --now sportowa-szkola
cp "$APP_DIR/deploy/nginx-sportowa-szkola.conf" /etc/nginx/sites-available/sportowa-szkola
ln -sf /etc/nginx/sites-available/sportowa-szkola /etc/nginx/sites-enabled/sportowa-szkola
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "==> Cron (zadanie dzienne o polnocy)..."
(crontab -l 2>/dev/null; echo "0 0 * * * curl -s http://127.0.0.1:5000/api/cron/daily >/dev/null") | crontab -

echo "==> Firewall..."
ufw allow 80/tcp 2>/dev/null || true
ufw allow 443/tcp 2>/dev/null || true

IP=$(hostname -I | awk '{print $1}')
echo ""
echo "GOTOWE! Strona: http://$IP  ( pamietaj o regule sieci Oracle dla portow 80/443 )"
echo "Zarejestruj sie jako pierwszy - zostaniesz adminem."

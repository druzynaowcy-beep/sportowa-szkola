#!/bin/bash
# Dzienne zadanie cykliczne: bonusy tygodniowe + zamykanie konkursow.
# Uzycie: APP_URL=https://twoj-adres ./cron-daily.sh
curl -s "${APP_URL:-http://127.0.0.1:5000}/api/cron/daily"
echo

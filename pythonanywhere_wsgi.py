# Plik WSGI dla PythonAnywhere (zakladka Web -> WSGI configuration file).
# Podmien TWOJLOGIN na swoj login oraz wygeneruj wlasny SECRET_KEY:
#   python3 -c "import secrets; print(secrets.token_hex(32))"
import os
import sys

os.environ["SECRET_KEY"] = "TUTAJ-WKLEJ-DLUGI-LOSOWY-SEKRET"

PROJECT = "/home/TWOJLOGIN/szkolny-sport"
if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)
os.chdir(PROJECT)

from app import app as application  # noqa: E402

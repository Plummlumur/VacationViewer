# Security Fixes TODO

## Phase 1: Stabilität & Fonts
- [ ] `vacationviewer_setup.sh` anpassen (Wechsel von `runserver` 0.0.0.0 zu `waitress-serve --port=8000` für netzwerkweite Erreichbarkeit).
- [ ] Google Fonts aus `admin_login.html` und `admin_dashboard.html` entfernen (Verwendung von `system-ui`).
- [ ] Testen & Committen.

## Phase 2: Basis-Sicherheit (Django Settings & Auth)
- [ ] `DEBUG = False` und `SECRET_KEY` in `settings.py` absichern.
- [ ] Klartext-Passwort-Fallback in `admin_views.py` entfernen.
- [ ] Neues Management-Kommando (`set_admin_password.py`) zum Hashen des Admin-Passworts erstellen.
- [ ] Testen & Committen.

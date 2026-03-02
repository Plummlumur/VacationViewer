# codex.md

## Projektziel und Nicht-Ziele
- Ziel: Eine barrierearme TV-Info-Screen-Webapp bereitstellen, die fuer ein Museumsteam (ca. 40 Personen) freie Urlaubsslots pro aktuellem und zukuenftigen Zeitraum sichtbar macht.
- Erfolgsmetrik: Eine Aufsicht kann in unter 30 Sekunden erfassen, ob im aktuellen oder in kommenden Monaten noch freie Urlaubsslots verfuegbar sind.
- Nicht-Ziele:
  - Konkrete Beantragung oder Genehmigung von Urlaub
  - Anzeige personenbezogener Daten (keine Namen)
  - Historische Anzeige vergangener Tage/Monate

## Scope v1 (MVP)
- Enthalten:
  - Monatsansicht ab heutigem Datum (Vergangenheit ausgeblendet)
  - Anzeige aggregierter Tageswerte (z. B. "belegt", "frei", "Limit erreicht")
  - Konfigurierbares Urlaubs-Limit `n` (maximal gleichzeitig im Urlaub)
  - Automatischer Monatswechsel im Info-Screen alle `n` Sekunden (konfigurierbar)
  - Automatischer Daten-Refresh aus einer Excel-Datei alle paar Minuten
  - Barrierearme, visuell schnell erfassbare Darstellung (klare Kontraste, gut lesbare Typografie, keine reine Farbcodierung)
- Nicht enthalten:
  - Nutzerkonten und Login
  - Admin-Backend
  - Rollen-/Rechtesystem
  - Mehrsprachigkeit (nur Deutsch)

## Tech-Stack und Begruendung (kurz)
- Sprache/Runtime: Python 3.12
- Framework: Django
- Datenhaltung: Excel-Datei (XLSX) als read-only Quelle, intern aufbereitet im Speicher
- Frontend: Django Templates + leichtes CSS/JS fuer Auto-Rotation und Live-Refresh
- Begruendung:
  - Django bietet schnellen, stabilen Setup fuer serverseitige Anzeige-Anwendungen
  - Python eignet sich gut fuer robustes XLSX-Parsing und Validierung
  - Serverseitiges Rendering ist stabil fuer Smart-TV-Browser und Raspberry-Pi-Betrieb
  - Geringe Komplexitaet fuer ein Solo-Projekt mit klarem MVP

## Architektur-Skizze (Module und Verantwortlichkeiten)
- `ingest`: XLSX laden, Schema validieren, Datums-/Kontingentwerte normalisieren
- `domain`: Berechnung Tagesstatus (`frei`, `belegt`, `limit_erreicht`) und Monatsaggregation
- `app/views`: Endpunkte fuer Screen-Ansicht und Health-Check
- `ui`: TV-optimiertes Template, klare Statusindikatoren, Auto-Monatswechsel, Auto-Refresh
- `config`: Konfigurationswerte (`urlaubslimit_n`, `rotation_seconds`, `refresh_minutes`)
- Datenfluss:
  - XLSX-Datei -> `ingest` validiert/normalisiert -> `domain` berechnet Slot-Status -> `ui` rendert aktuelle und kommende Monate

## Coding-Konventionen (Format, Lint, Tests, Branching, Commits)
- Format/Lint: `ruff format` + `ruff check` als verbindliche Gates
- Tests:
  - Unit: Pflicht fuer Parser-, Datumsfilter- und Slot-Berechnungslogik
  - Integration: Mindestens 1-2 Tests fuer End-to-End-Flow (Datei laden -> Monatsansicht rendern)
- Branching: trunk-based mit kurzen Feature-Branches (`feat/*`, `fix/*`)
- Commits: Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`)

## Entwicklungsworkflow (lokal, CI, Review-Definition-of-Done)
- Lokal starten:
  - `python -m venv .venv`
  - `source .venv/bin/activate`
  - `pip install -r requirements.txt`
  - `python manage.py runserver`
- CI-Pipeline:
  - `ruff check .`
  - `ruff format --check .`
  - `pytest`
  - optional: `python manage.py check`
- Review-DoD:
  - Tests gruen
  - Lint/Format gruen
  - Barrierefreiheits-Checks fuer Kernscreen durchgefuehrt (Kontrast, Lesbarkeit, semantische Struktur)
  - Vergangene Zeitraeume werden korrekt nicht angezeigt
  - Dokumentation aktualisiert (`README` + Betriebsanleitung Datenupdate)

## Priorisierte Start-Tasks (erste 5-10 Aufgaben)
1. Django-Projektstruktur und Basis-Settings fuer Screen-App anlegen.
2. XLSX-Schema definieren (Spalten, Datumsformat, Limitbezug) und Beispiel-Datei erstellen.
3. Import-/Validierungsmodul fuer Excel inklusive Fehlerprotokoll umsetzen.
4. Domain-Logik fuer freie/belegte Slots und Limitpruefung implementieren.
5. TV-optimierte Monatsansicht mit klaren Statusindikatoren bauen.
6. Logik zum Ausblenden vergangener Tage/Monate implementieren.
7. Auto-Monatswechsel (intervallgesteuert) und Auto-Refresh integrieren.
8. Unit- und Integrationstests fuer Kernlogik und Rendering schreiben.
9. Deployment-Variante A dokumentieren (interner Server + Smart-TV-Browser).
10. Deployment-Variante B dokumentieren (Raspberry Pi + lokaler Browser im Kiosk-Modus).

## Risiken und offene Entscheidungen
- Risiko: Inkonsistente Excel-Daten (fehlende Spalten, falsche Datumsformate) -> Gegenmassnahme: Striktes Schema + Validierungsfehler sichtbar protokollieren.
- Risiko: Anzeige auf unterschiedlichen TV-/Browser-Engines wirkt uneinheitlich -> Gegenmassnahme: Zielbrowser frueh festlegen und visuelle Regressionstests auf Zielgeraeten.
- Risiko: Unzureichende Lesbarkeit auf Distanz -> Gegenmassnahme: Mindestschriftgroessen, Kontrastvorgaben und Test aus realer Betrachtungsdistanz.
- Offene Entscheidung: Primäre Betriebsform fuer v1 festlegen (Server+Smart-TV oder Raspberry Pi) bis vor erstem produktiven Rollout.
- Offene Entscheidung: Exaktes Refresh-Intervall in Minuten (z. B. 3 oder 5) final festlegen.

## Annahmen
- Nur internes Netzwerk, keine externe Oeffnung.
- Anwendung bleibt read-only und verarbeitet keine personenbezogenen Namen.
- UI-Sprache bleibt Deutsch.
- Solo-Entwicklung mit Self-Review vor Merge.
- Performanceziel: initiale Anzeige < 1 Sekunde auf Zielhardware.

## Aenderungslog
- 2026-03-02 Erstfassung erstellt.
- 2026-03-02 Inhaltlich komplettiert (TV-Info-Screen, XLSX-Quelle, Barrierefreiheit, Test-/CI-Workflow).

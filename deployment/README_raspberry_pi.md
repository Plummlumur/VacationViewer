# Deployment: Raspberry Pi Kiosk-Modus

Diese Anleitung beschreibt die Einrichtung des VacationViewer auf einem Raspberry Pi im sogenannten "Kiosk-Modus". Ziel ist es, dass der Raspberry Pi beim Starten direkt und vollflächig den VacationViewer in einem Chromium-Browser öffnet und auf Interaktionen von selbst aktualisiert.

## Voraussetzungen

- Ein **Raspberry Pi** (Modell 3 B+, 4 oder 5 wird empfohlen) mit einem modernen Raspberry Pi OS (mit Desktop), aufgesetzter Netzwerkverbindung und SSH-Zugriff.
- Ein angeschlossener TV-Screen / Monitor.

## Installation mit Setup-Script

Die automatische Installation und Einrichtung für den Autostart kann über das beiliegende Skript `vacationviewer_setup.sh` durchgeführt werden.

1. **Repository auf dem Pi klonen**:
   Stell sicher, dass der Code auf dem Raspberry Pi in das Verzeichnis `/var/www/vacationviewer` kopiert oder geclont wurde.

2. **Skript ausführen**:
   Navigiere in das Repository:
   ```bash
   cd /var/www/vacationviewer/deployment
   chmod +x vacationviewer_setup.sh
   ./vacationviewer_setup.sh
   ```

3. Das Script führt selbstständig folgende Aufgaben durch:
   - Systempakete und Werkzeuge installieren (`python3`, `git`, `unclutter`, `chromium-browser`).
   - Ein dediziertes Python Virtual Environment (VENV) für die App unter `/var/www/vacationviewer/.venv` anlegen.
   - Abhängigkeiten über `requirements.txt` installieren.
   - Die Django-App als Systemd Service (`vacationviewer.service`) einrichten, damit sie immer im Hintergrund läuft.
   - Den Autostart-Eintrag für LXDE (die Raspberry-Pi Desktop Umgebung) konfigurieren. Hierbei wird der Bildschirmschoner deaktiviert, die Maus versteckt und der Browser direkt vollbild im Kiosk-Modus geöffnet.

4. **Raspberry Pi neu starten**:
   Nach Abschluss muss das System neu gestartet werden:
   ```bash
   sudo reboot
   ```

   Der Raspberry Pi sollte nun in den Kiosk-Modus booten und den VacationViewer anzeigen.

## Manuelle Schritte (Falls das Script fehlschlägt)

Sollte das Setup-Script nicht wie gewünscht durchlaufen, kannst du die kritischen Komponenten überprüfen:

**Systemd Service überprüfen:**
Prüfe den Status der Django-App:
```bash
sudo systemctl status vacationviewer.service
```
Lese die Logs im Fehlerfall:
```bash
sudo journalctl -u vacationviewer.service -e
```

**Autostart manuell editieren:**
Falls der Kiosk-Modus nicht startet und du als Standardbenutzer `pi` eingeloggt bist, kannst du in dieser Datei prüfen, was beim Login aufgerufen wird:
```bash
nano /home/pi/.config/lxsession/LXDE-pi/autostart
```
Es sollten Einträge wie diese vorhanden sein:
```text
@xset s off
@xset -dpms
@xset s noblank
@unclutter -idle 0.5 -root &
@chromium-browser --kiosk --incognito --disable-infobars http://127.0.0.1:8000
```

## Datenpflege (Excel)

Da der Raspberry Pi als Server und Anzeigegerät zugleich dient, müssen Excel-Updates auf das Dateisystem gespielt werden. Es gibt zwei Wege:

1. **Über USB-Stick**: Ein Cronjob kann ergänzt werden, um eine Datei von einem angeschlossenen USB-Stick automatisch in den `/var/www/vacationviewer/data` Ordner zu kopieren. (Nicht Teil dieser Standard-Doku).
2. **Über Netzwerkfreigabe / SCP**: Die Mitarbeiter, die den Urlaub pflegen, laden die neue XLSX-Verson einfach per `scp` hoch:
   ```bash
   scp pfad_zur_lokalen_excel/urlaub_2026.xlsx pi@ip-des-raspberry-pi:/var/www/vacationviewer/data/
   ```
   Die App zieht sich die Daten dank des Caching/Ingest-Moduls innerhalb von maximal 5 Minuten automatisch neu an.

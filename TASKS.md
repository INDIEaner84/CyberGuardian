# CyberGuardian – priorisierter Aufgabenkatalog

Stand: 18.10.2026. Im Repository gab es zuvor keinen separaten Aufgabenkatalog; zum Zeitpunkt der Aufnahme waren keine offenen GitHub-Issues vorhanden. Dieser Katalog beschreibt **nachprüfbare Arbeiten**, nicht automatisch gestartete Security-Tools. Status: ✅ umgesetzt · ◐ teilweise · ⏳ offen · ⛔ externe Voraussetzung.

| ID | Priorität | Status | Aufgabe und Abnahmekriterium |
| --- | --- | --- | --- |
| CG-01 | P0 | ✅ | VM-Tests nur per Opt-in und festem Ziel: `core/vm_lab.py`, `lab/`; Gastmeldungen sind von simulierten Honeypot-Signalen getrennt. Integrationstest ohne echten QEMU-Boot in `tests/test_vm_lab.py`. |
| CG-02 | P0 | ✅ | VM-Test-POST erfordert Same-Origin und einen gesonderten Operator-Schlüssel (32–128 Zeichen); ohne gültigen Schlüssel kein Request an den Gast. Kein Schlüssel im Control Plane oder Tool-Run. HTTP-Test in `tests/test_server_vm_lab.py`. |
| CG-03 | P1 | ✅ | VM-Sensor im Tool Atlas mit **nur lesbarer Statusaktion**; keine Szenarien im Atlas startbar. `tests/test_tool_catalog.py`. |
| CG-04 | P1 | ✅ | Lokaler Evidenz-Finder und CSV-Export im VM-Lab; simulierte und beobachtete Ereignisse sind unterscheidbar. Kein externer OSINT-Aufruf. |
| CG-13 | P1 | ✅ | Standardbibliotheks-/HTTP-Tests und JavaScript-Syntaxprüfung laufen in `.github/workflows/tests.yml` ohne externe Security-API oder Gast-Image. |
| CG-05 | P0 | ⛔ | Echten QEMU-Boot und cloud-init auf einem Linux-Host mit geprüftem Cloud-Image validieren: Sensor erreichbar, Baseline 0 Alerts, Discovery 1, Retries 1, VM-Neustart und Offline-Zustand prüfen. In der Entwicklungsumgebung fehlen QEMU und Gast-Image; Unit-/HTTP-Tests ersetzen diesen Nachweis **nicht**. |
| CG-06 | P0 | ◐ | Alle `/api/*`-Routen (außer `/api/auth`) können mit einem Operator-Bearer-Schlüssel geschützt werden; ein optionaler, getrennter Viewer-Schlüssel erlaubt nur GET (403 vor Body-Lesen bei Schreibzugriffen). `/api/session` meldet die Rolle ohne Geheimnis. Viewer-GETs sammeln keine Gast-Alerts; UI kennzeichnet Lesezugang. Schreibzugriffe prüfen Origin, nicht-lokale Bindung ohne Operator-Schlüssel scheitert außer mit expliziter Demo-Ausnahme. **Noch offen:** vollständige Benutzer-/Datenrechte, Secret-Rotation, TLS/Reverse Proxy und produktiver Mehrbenutzerbetrieb. VM-Szenario-Operator-Schlüssel aus CG-02 bleibt separat. |
| CG-07 | P1 | ✅ | Offline-Klassifizierung vorhandener VM-Alerts und simulierter Honeypot-Logs mit vier festen Gleichheitsregeln, maximal 100 Zeilen je Quelle, getrennten Quellenlabels und Audit-Zähler. Keine frei definierbaren Muster, Pfade, Kommandos, neuen Incidents oder Live-Alerts. `tests/test_detection_replay.py`, `tests/test_api_auth.py`. **Kein Sigma-Parser.** |
| CG-08 | P1 | ✅ | Alert-Workflow für Gast-Signale: Quittierung, begrenzte Notizen, Run-ID im lokalen CSV-Export und Audit ohne Notizinhalt. Sensordaten bleiben unverändert, keine automatische Blockierung. `tests/test_api_auth.py`. |
| CG-09 | P2 | ✅ | Optionaler Offline-Import von Suricata-EVE-Alerts und Zeek-JSON-Notices: maximal 48 KiB/100 Zeilen/50 Alerts pro Datei, nur ausgewählte Metadaten, 200 lokal gespeicherte Einträge, Dubletten-Abgleich und **unverifiziert/nicht live** als Quellenlabel. Keine Sensor-Installation, kein Dateipfad an den Server, keine Rohlog-Persistenz. Fixtures/Tests in `tests/fixtures/`, `tests/test_offline_import.py`, `tests/test_api_auth.py`. Kein TSV oder produktiver Collector. |
| CG-10 | P2 | ⏳ | Offline-Artefaktprüfung (YARA/osquery/ClamAV) nur mit expliziter lokaler Pfad-Allowlist, begrenzter Laufzeit und dokumentierter Berechtigung. |
| CG-11 | P2 | ⏳ | Optionaler PCAP-Import und Metrik-Export, jeweils mit Datenschutz-/Retention-Konzept; keine Payloads in den Browser-Audit-Trail. |
| CG-12 | P2 | ⏳ | Maltego/Graph-Workflow erst nach Auswahl von Lizenz, Datenquellen und Datenschutzumfang; derzeit nur lokaler CSV-Export, **keine** installierte Maltego-Integration. |

## Nächste Reihenfolge

1. **CG-05** auf einem geeigneten Host manuell abnehmen; beobachtete Ergebnisse und Gast-Image-Version dokumentieren.
2. **CG-06** für Remote-/Mehrbenutzerbetrieb fertigstellen (vollständige Rollen-/Datenrechte, TLS, Rotation); der Viewer-Zugang ist kein vollständiges Mehrbenutzer-Rollenmodell.
3. Danach **CG-10/11** nur mit explizitem lokalen Pfad-/Datenumfang und Datenschutzkonzept planen; externe Sensoren und Scanner nicht automatisch installieren.

Testbefehl: `python3 -m unittest discover -s tests -v`. Die VM-Provisionierung selbst benötigt lokal bereitgestellte Systemwerkzeuge; Details in der [README](README.md#optionales-qemu-vm-lab-echte-gast-beobachtung).

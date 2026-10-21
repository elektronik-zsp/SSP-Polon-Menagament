# SSP Polon 2.4.4 — widoczny menedżer przy uruchomieniu

## Poprawka
- Okno menedżera pojawia się przy normalnym uruchomieniu `SSP_Polon_Manager.vbs`.
- Skrypty `.vbs` uruchamiają `pythonw.exe` z żądaniem widocznego okna. Jeżeli w przenośnym środowisku dostępny jest tylko `python.exe`, jego konsola pozostaje ukryta.
- Win32 `ShowWindow` jest wywoływane ponownie, co omija ograniczenie `STARTUPINFO` z uruchomienia ukrytego przez Windows Script Host.
- Minimalizacja i przycisk X nadal ukrywają menedżer do tray. Proces serwera działa bez zmian.
- Ponowne uruchomienie skrótu przywraca istniejące okno menedżera.

## Instalacja z wersji 2.4.3
Zamknij stary menedżer przez ikonę tray -> Zamknij menedżer (serwer bez zmian). Podmień tylko:
`tools/manager.py`, `SSP_Polon_Manager.vbs` i `Uruchom_w_tle.vbs`.
Następnie uruchom `SSP_Polon_Manager.vbs`.
Nie zmieniaj `server.py`, `config.json`, `runtime`, lokalizacji bazy ani pliku JSON. Nie ma potrzeby zatrzymywania serwera SSP Polon.

## Sprawdzenie
Zweryfikowane są testy logiki i kolejność wywołań Win32 przy uruchomieniu. Natywne okno Windows i zachowanie powłoki firmowego komputera należy ostatecznie potwierdzić na docelowej stacji.

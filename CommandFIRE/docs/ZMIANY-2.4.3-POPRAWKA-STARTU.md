# SSP Polon 2.4.3 — naprawa uruchamiania menedżera

W wersji 2.4.2 podczas importu `tools/manager.py` użyto `ctypes.wintypes.HCURSOR`, którego nie zawierają standardowe kompilacje CPython. Ponieważ `SSP_Polon_Manager.vbs` uruchamiał proces niewidocznie, menedżer mógł zakończyć działanie bez komunikatu.

## Poprawki
- zastąpiono nieistniejący typ WinAPI poprawnym typem uchwytu;
- skrypt VBS uruchamia `tools/manager_boot.py`, który loguje błędy i wyświetla komunikaty;
- dodano `Diagnoza_Menedzera.bat`, który uruchamia proces z widoczną konsolą;
- zachowano działanie przycisków, ikony tray i izolowanego serwera na localhost.

## Aktualizacja z 2.4.2
Zamknij stary menedżer, podmień tylko: `tools/manager.py`, `tools/manager_boot.py` (nowy), `SSP_Polon_Manager.vbs`, `Uruchom_w_tle.vbs`, `Uruchom.bat`, `Diagnoza_Menedzera.bat` (nowy).
Nie zmieniaj `server.py`, `launcher.py`, `config.json`, `runtime`, pliku bazy ani `backups`.

Jeśli okno nadal nie pojawia się, użyj `Diagnoza_Menedzera.bat` i zapisz dokładny komunikat.

## Ograniczenia
Brak natywnego testu środowiska Windows podczas budowania aktualizacji; działanie tray i polityki firmowe Windows muszą zostać sprawdzone na docelowym komputerze.

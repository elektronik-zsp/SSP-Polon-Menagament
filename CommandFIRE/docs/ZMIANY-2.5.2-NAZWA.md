# CommandFIRE SSP Serwis 2.5.2 — zmiana nazwy aplikacji

Nowa nazwa programu: **CommandFIRE SSP Serwis**. Poprzednie oznaczenie interfejsu "SSP Polon Serwis" zostało zastąpione w:
- tytule i nagłówku strony oraz ekranie logowania,
- komunikatach statusu i nazwie eksportu bazy,
- oknie, ikonie tray i komunikatach menedżera Windows,
- stronie licencji i tekście licencji, z zachowaniem danych autora i udzielonego ZSP Synthos upoważnienia,
- dokumentacji głównej oraz nowym skrócie `CommandFIRE_SSP_Serwis.vbs`.

## Aktualizacja z 2.5.1
1. Zakończ wszystkie sesje pracy i wykonaj kopię wspólnej bazy.
2. Zatrzymaj lokalny serwer, zamknij menedżera z tray, a potem podmień pliki z ZIP na każdym stanowisku.
3. Nie nadpisuj `config.json`, pliku `db_polon_ssp.json`, folderu `runtime` ani folderu `backups`.
4. Otwórz `CommandFIRE_SSP_Serwis.vbs` lub istniejący `SSP_Polon_Manager.vbs`; odśwież przeglądarkę `Ctrl+F5`.

Ważne: nazwy techniczne (`SSP-Polon`, `%LOCALAPPDATA%\SSP-Polon`, `SSP_Polon_Manager.vbs`, `db_polon_ssp.json`, identyfikator okna oraz port `8765`) zachowano świadomie dla zgodności. **Nie zmieniaj ręcznie nazwy folderu aplikacji**, gdy serwer jest uruchomiony. Dane, uprawnienia, funkcje i schemat wspólnej bazy nie zostały zmienione.

Ikona graficzna (tarcza i płomień) pozostaje bez zmian, ponieważ nie zawiera starej nazwy. Informacje o prawach autorskich i licencji to oznaczenia autora i warunki korzystania, nie zastępują odrębnego ustalenia, komu przysługują prawa majątkowe w świetle umów i prawa.

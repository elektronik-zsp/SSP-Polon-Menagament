# SSP Polon 2.4.2 — jedno okno menedżera i zasobnik systemowy Windows

## Uruchomienie

1. Zakończ pracę i **zatrzymaj serwer 2.4.1**, używając `Zatrzymaj_SSP_Polon.vbs`, przed podmianą `tools/launcher.py`.
2. Wykonaj kopię folderu aplikacji. Nie ruszaj `runtime`, `config.json`, lokalnej ani wspólnej bazy danych i kopii zapasowych.
3. Podmień pliki aplikacji z aktualizacji 2.4.2 na każdym stanowisku.
4. Otwórz **`SSP_Polon_Manager.vbs`** (albo `Uruchom_w_tle.vbs`, który teraz uruchamia ten sam menedżer).
5. W jednym oknie sprawdź stan i kliknij **Uruchom**; przeglądarka otworzy panel. Gdy serwer działa, przycisk **Otwórz panel** otworzy stronę ponownie.
6. Kliknięcie **Minimalizuj do tray**, standardowego `-` albo `X` ukrywa okno menedżera w obszarze powiadomień Windows (może znajdować się pod strzałką `^`). Nie zatrzymuje serwera. Kliknij ikonę, by przywrócić okno, albo użyj jej menu kontekstowego.
7. **Zatrzymaj** kończy serwer i zwalnia lokalne blokady edycji. Zamknięcie tylko okna menedżera (`Zamknij menedżer`) **nie zatrzymuje** serwera.

`Uruchom.bat` również otwiera menedżer. Jeśli wbudowany w przenośny runtime `pythonw.exe` nie istnieje, `SSP_Polon_Manager.vbs` ukrywa konsolę `python.exe`. Jeśli korporacyjna polityka blokuje VBS i w runtime nie ma `pythonw.exe`, nie będzie możliwe w pełni bezkonsolowe uruchomienie tą metodą bez zgody IT; alternatywnie można uruchomić `runtime\python.exe -I -B tools\manager.py` z widoczną konsolą. Nie trzeba niczego instalować.

## Co się nie zmienia

- Na każdym komputerze nadal działa tylko lokalny HTTP serwer na `127.0.0.1`.
- Wspólna baza JSON nadal jest na udziale Windows, blokady poszczególnych rekordów i 30 minut bezczynności są bez zmian.
- Panel i tray nie podtrzymują sztucznie aktywności podczas edycji. Po zamknięciu przeglądarki serwer nadal może pracować w tle.
- Menedżer otwiera tylko własną instancję programu. Jeśli port jest zajęty przez obcy proces, nie próbuje go zatrzymywać.

## Zagrożenia i ograniczenia

1. **Tray to nie usługa**: po wylogowaniu lub restarcie Windows serwer może zostać zakończony i nie uruchamia się sam. Program uruchamia użytkownik Windows.
2. **Ukryte błędy**: menedżer prezentuje status bazy i zapisuje błędy do `%LOCALAPPDATA%\SSP-Polon\<id>\manager.log`, a serwer do `server.log`; proces bez widocznej konsoli może ulec awarii. Status odświeża się co ok. 15 s.
3. **Sieć SMB**: utrata udziału nie może spowodować przełączenia na lokalną bazę; zapis kończy się błędem. Najważniejsze pozostają kopie zapasowe i uprawnienia do udziału. Menedżer nie zabezpiecza pliku przed awarią sieci/dysku.
4. **Niezapisane formularze**: zatrzymanie serwera w trakcie edycji może spowodować utratę treści przeglądarki. Menedżer korzysta z istniejącego ostrzeżenia przed zatrzymaniem, jeśli są aktywne formularze.
5. **Jedna instancja menedżera** na użytkownika i lokalną instalację. Ponowny klik pokazuje istniejące okno, nie tworzy kolejnego tray.
6. **Blokady IT**: polityka organizacji może wyłączyć WSH (VBS), dostęp do Win32 tray albo wykonywanie lokalnych skryptów. To wdrożenie wymaga testu na docelowych Windows 10/11; automatyczny test natywnego GUI nie został wykonany w środowisku Linux.
7. **Uwierzytelnianie**: endpoint zatrzymywania serwera pozostaje zabezpieczony losowym tokenem przechowywanym w lokalnym profilu Windows. Nie udostępniaj całego profilu użytkownika ani tokenów. Menedżer nie zmienia uprawnień bazy sieciowej.

## Testy

73 testy logiki aplikacji (w tym 6 nowych testów kontrolera menedżera) uruchomione pomyślnie. Uruchomienie natywnego okna i ikony tray na rzeczywistym Windows należy zweryfikować pilotażowo, zanim wszystkie stanowiska przejdą na tę wersję.

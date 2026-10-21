# SSP Polon Serwis 2.4.0 — aktualizacja

## Zakres

- Numeracja zgłoszeń: `fault.number`, generowana automatycznie przy tworzeniu nowego zgłoszenia.
- Numeracja przeglądów: `history.inspectionNo` na dokumentach typu `Przegląd`, dopiero po zatwierdzeniu.
- Numeracja protokołów: `history.protocolNo` na wszystkich zatwierdzonych dokumentach. Przegląd ma osobny numer przeglądu i numer protokołu.
- Konfiguracja w `serviceConfig.numbering`: trzy serie `fault`, `inspection`, `protocol`, każda z `prefix`, `start`, `digits`, `annual`.
- Numeracja roczna `PREFIKS/RRRR/0001` lub ciągła `PREFIKS/0001`; cyfry z wiodącymi zerami. Każda seria ma osobny prefiks.
- Starsza konfiguracja `protocolPrefix` nadal jest odczytywana. Zmiana numeracji w formularzu aktualizuje ją dla zgodności ze starszym formatem.
- Stare wpisy bez nowych pól czytane są automatycznie, otrzymują puste wartości, ale nie są przenumerowywane.
- Dotychczasowe numery są niezmienne. Dla nowych wpisów serwer, a nie klient, wyznacza kolejne numery.
- Kolejność nowych rekordów w jednym zapisie jest deterministyczna. Wiele lokalnych klientów używa nadal wyłącznego blokowania pliku `.mutex` przed wyliczeniem numeru i zapisem.
- Dashboard pokazuje liczbę central wymagających uwagi, zaległe i zbliżające się terminy, wykres statusów zgłoszeń i terminów oraz miesięczną aktywność (sześć miesięcy).
- Nie potrzeba dodatkowych instalacji ani internetu. Wykresy napisano w HTML i CSS.

## Aktualizacja stanowisk

1. Wykonaj kopię folderu SSP Polon na każdym komputerze i **oddzielną kopię wspólnej bazy** w bezpiecznym miejscu.
2. Zamknij program na wszystkich stanowiskach, także serwery `server.py`.
3. W każdym lokalnym folderze SSP-Polon zastąp pliki aplikacji zawartością ZIP 2.4.0. Nie nadpisuj folderu `runtime`, `config.json`, `db_polon_ssp.json` ani `backups`.
4. Uruchom program przez `Uruchom.bat` i sprawdź wyświetlaną wersję `2.4.0`.
5. Na jednym stanowisku otwórz **Konfiguracja → Edytuj konfigurację i numerację**, ustaw trzy serie. Zapis jest wspólny dla wszystkich użytkowników.
6. Przeprowadź test dwóch komputerów: niezależne zgłoszenia otrzymują odrębne numery; próba edycji tej samej centrali jest blokowana; zatwierdzenie przeglądu zapisuje oba numery.

**Ważne:** wszystkie komputery zapisujące tę samą bazę muszą mieć tę samą wersję 2.4.0; program 2.3.x nie nada nowych numerów zgłoszeń/przeglądów. Nie umieszczaj programu na udziale do wspólnego uruchamiania — współdzielony jest wyłącznie plik JSON.

## Testy

- Testy serwera: `python -m unittest discover -s tests -p 'test_*.py'`
- Kontrola składni JS: `node --check app.js`
- Test demonstracyjny UI wykonany w Chromium z przykładowymi danymi (bez HTTP/SMB); pełny test na stanowiskach Windows pozostaje wymagany.
- Automatyczny test HTTP Playwright może być niedostępny w środowisku z blokadą dostępu Chromium do `127.0.0.1`.

## Ograniczenia

- Numeracja oparta o historię wpisów, nie jest zaawansowaną księgową numeracją transakcyjną. Import całej bazy może cofnąć stan licznika, a zmiana prefiksu/trybu może utworzyć nową serię.
- Zgłoszenia już zarejestrowane w starych wersjach bez numeru w nowym formacie pozostają identyfikowane starym ID, np. `A-…`; to celowe, aby zachować odnośniki.
- Wykres i lista uwag odzwierciedlają dane zapisane przez serwisantów; **nie zastępują odczytu stanu fizycznej centrali** ani diagnostyki Polon.

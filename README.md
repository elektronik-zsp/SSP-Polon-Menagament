# SSP Polon — aplikacja offline

**[Pobierz gotową paczkę Windows x64 — bez instalacji](https://github.com/elektronik-zsp/SSP-Polon-Menagament/raw/refs/heads/main/downloads/SSP-Polon-Portable-Windows-x64.zip)**

Rozpakuj cały ZIP i uruchom `Uruchom.bat`. Paczka zawiera środowisko Python; nie trzeba go instalować.

Interfejs i funkcje pochodzą z przekazanego `mini_crm_ssp_polon_v11.html`: pulpit, rejestr central, karta techniczna, awarie, historia, przeglądy, wydruki oraz import/eksport JSON. Zapis ActiveX/LocalStorage zastąpiono lokalnym serwerem plikowym. Nie są pobierane biblioteki ani zasoby z Internetu.

## Windows

1. Rozpakuj całą paczkę do folderu, w którym masz prawo zapisu, np. Dokumenty\SSP-Polon. Nie uruchamiaj jej wewnątrz ZIP.
2. Kliknij `Uruchom.bat`. Otworzy się domyślna przeglądarka. Pozostaw okno serwera otwarte podczas pracy.
3. Przy pierwszym uruchomieniu wybierz dane demonstracyjne albo pustą bazę. Dane demonstracyjne nie opisują rzeczywistego stanu urządzeń.
4. Zakończ pracę, zamykając przeglądarkę i okno serwera (lub Ctrl+C).

Plik HTML otwierany bezpośrednio nie ma dostępu do plików. Uruchamiaj program przez plik BAT. Paczka zawiera przenośny Python 3.13.16 dla Windows x64 w folderze `runtime`. Nie wymaga instalacji, pip, zmian PATH, rejestru ani uprawnień administratora. Aplikacja działa bez Internetu; serwer nasłuchuje wyłącznie na tym komputerze.

## Baza i konfiguracja

- `db_polon_ssp.json` — baza tworzona przy pierwszym uruchomieniu; każda zatwierdzona zmiana jest od razu zapisywana.
- `db_polon_ssp.json.bak` — poprzednia wersja bazy, aktualizowana przed kolejnym zapisem. Regularnie kopiuj bazę również na inny nośnik.
- `config.json` — konfiguracja czytana podczas uruchomienia. `port` domyślnie 8765, `database` to nazwa pliku JSON w tym samym folderze, `open_browser` określa automatyczne otwieranie przeglądarki. Po zmianie konfiguracji uruchom serwer ponownie. Zmiana nazwy bazy wybiera inny plik, nie przenosi danych automatycznie.

Zapis odbywa się przez plik tymczasowy i podmianę pliku docelowego. Konflikt wersji (np. drugie okno lub ręczna edycja pliku) blokuje zapis i wymaga odświeżenia. Uszkodzona baza nie jest zastępowana danymi demonstracyjnymi. Aby odtworzyć kopię, zatrzymaj serwer, zachowaj uszkodzony plik osobno, skopiuj `.json.bak` jako `.json` i uruchom program.

## Przeniesienie danych

W starym programie użyj eksportu JSON, a w nowym importu JSON. LocalStorage starej strony nie jest automatycznie dostępny dla nowego programu. Jeśli masz już plik `db_polon_ssp.json` z wersji HTA, skopiuj go obok `server.py` przed pierwszym uruchomieniem; serwer odczytuje UTF-8 i UTF-16. Import zastępuje bieżącą bazę; poprzedni zapis pozostaje w `.bak`.

## Rozwój i testy

Python nie potrzebuje dodatkowych pakietów do uruchomienia:

```
python server.py --no-browser
python -m unittest discover -s tests -v
```

Test przeglądarkowy: `python tests/browser_smoke.py` (wymaga deweloperskiego pakietu Playwright i Chromium; nie są wymagane użytkownikowi aplikacji).

Zweryfikowano na Linuksie: zapis i ponowny odczyt, restart serwera, kopię, konflikt wersji, uszkodzoną bazę, format UTF-16 oraz edycję w Chromium. Launcher Windows wymaga sprawdzenia na docelowym komputerze. Baza pozostaje w zgodnym ze starym programem formacie JSON; nie jest to SQLite. Nie uruchamiaj kilku serwerów dla tego samego pliku bazy.

## Paczka przenośna

Uruchom.bat korzysta wyłącznie z dołączonego runtime, niezależnie od Pythona zainstalowanego na komputerze. Przenoś cały folder razem z bazą i konfiguracją. Aktualizując istniejącą aplikację, zachowaj własne pliki bazy i konfiguracji. Wymagany Windows 10/11 x64. Jeśli polityka domeny blokuje uruchamianie plików EXE z folderów użytkownika (np. AppLocker), również aplikacja przenośna wymaga dopuszczenia przez IT; brak instalacji nie omija tej polityki.

Runtime pochodzi z pakietu Python Software Foundation w NuGet: https://api.nuget.org/v3-flatcontainer/python/3.13.16/python.3.13.16.nupkg . Zweryfikowano SHA-512 z metadanych pobrania HTTPS i integralność ZIP. Licencja: runtime/LICENSE.txt. Testy aplikacji wykonano na Linuksie; plików wykonywalnych Windows nie uruchomiono w tym środowisku.

# CommandFIRE SSP Serwis — aktualizacja 2.12.10-TEST

Przegląd i poprawki przygotowane na podstawie paczki CommandFIRE 2.12.9.

- [Aktualizacja istniejącej instalacji](downloads/CommandFIRE-2.12.10-TEST-Aktualizacja.zip)
- [Pełna paczka Portable dla Windows x64](downloads/CommandFIRE-2.12.10-TEST-Portable-Windows-x64.zip)
- [Instrukcja aktualizacji i lista zmian](CommandFIRE/INFORMACJE-2.12.10-TEST.txt)
- [Analiza kodu i wyniki testów](CommandFIRE/docs/PRZEGLAD-2.12.10.md)
- [Kod aktualnej wersji](CommandFIRE/)

Zachowaj własną bazę, config.json i cfdb-key.dpapi. Paczka aktualizacyjna nie
zawiera plików użytkownika ani runtime. Wykonaj kopię folderu przed podmianą.
Testy automatyczne wykonano na Linux; test natywnego DPAPI i udziału SMB
pozostaje do wykonania na docelowym Windows.

Poniżej zachowano dokumentację wcześniejszej wersji SSP Polon 2.0.

---

# SSP Polon Serwis 2.0

Lokalna aplikacja do ewidencji central, zgłoszeń, przeglądów, napraw i protokołów. Windows 10/11 x64, bez instalacji i bez uprawnień administratora. Runtime Python jest w pełnej paczce. Wszystkie zasoby interfejsu działają offline.

**[Aktualizacja z wersji 1 do 2.0](https://github.com/elektronik-zsp/SSP-Polon-Menagament/raw/refs/heads/main/downloads/SSP-Polon-Aktualizacja-2.0.zip)** · **[Pełna paczka Windows x64](https://github.com/elektronik-zsp/SSP-Polon-Menagament/raw/refs/heads/main/downloads/SSP-Polon-Portable-Windows-x64.zip)**

## Aktualizacja istniejącego programu

1. Zakończ pracę w przeglądarce i zamknij okno serwera (`Ctrl+C`).
2. Skopiuj cały dotychczasowy folder aplikacji w inne miejsce jako kopię bezpieczeństwa.
3. Rozpakuj paczkę aktualizacyjną. Skopiuj **zawartość folderu `SSP-Polon`** do istniejącego folderu aplikacji i zgódź się na zastąpienie plików programu. Nie twórz podfolderu `SSP-Polon` wewnątrz starego folderu.
4. Pozostaw dotychczasowy `runtime`, `db_polon_ssp.json` (lub własny plik bazy) i `config.json`. Aktualizacja ich nie zawiera i nie nadpisuje.
5. Uruchom `Uruchom.bat`. Przy pierwszym zapisie program zrobi kopię starej bazy i zapisze nową strukturę. Samo otwarcie bazy nie zmienia pliku.
6. Otwórz **Konfiguracja**, wpisz dane firmy, obiektu, techników i dostosuj szablon kontroli.

Nowa wersja zachowuje stare centrale, zgłoszenia i historię, w tym dodatkowe pola. Stare wpisy są oznaczone „Wpis historyczny”; nie są automatycznie uznawane za zatwierdzone protokoły. Powrót do wersji 1 wymaga przywrócenia całego zachowanego folderu — nie używaj starego programu do zapisu nowej bazy.

## Pierwsze uruchomienie

Rozpakuj pełną paczkę do zapisywalnego folderu, np. Dokumenty\SSP-Polon, i uruchom `Uruchom.bat`. `config.json` powstanie automatycznie, jeśli go nie ma. Zacznij od konfiguracji i dodania centrali albo importu starej bazy. Nowa baza jest pusta; nie dodajemy automatycznie urządzeń demonstracyjnych. Pozostaw okno serwera otwarte podczas pracy.

## Proces serwisowy

1. **Centrale i harmonogram:** dodaj centralę, model, lokalizację, numer seryjny, stan i interwał. Karta centrali łączy zgłoszenia z historią. Archiwizacja zachowuje dane i wymaga zamknięcia zgłoszeń oraz zakończenia lub usunięcia szkiców.
2. **Zgłoszenia serwisowe:** określ objawy, zgłaszającego, priorytet, odpowiedzialnego i termin. Statusy: Nowe, W trakcie, Oczekujące, Zamknięte. Zamknięte zgłoszenie można ponownie otworzyć.
3. **Obsłuż / Nowy protokół:** uzupełnij zakres, wykonawcę, datę, rzeczywiste wyniki kontroli, pomiary, opis, części, czas pracy i zalecenia. Możesz zapisać szkic i wrócić później.
4. **Zatwierdź:** aplikacja sprawdzi dane, nada numer `PREFIKS/ROK/0001` i utrwali dane firmy oraz centrali. Zatwierdzonego dokumentu nie można zmienić ani usunąć w normalnym trybie. Korektę opisz w nowym protokole uzupełniającym; pierwotny dokument pozostaje w historii.
5. **Drukuj / PDF:** otwórz dokument i wybierz drukowanie. W przeglądarce wybierz „Zapisz jako PDF” lub drukarkę; dla czystego wydruku wyłącz nagłówki i stopki przeglądarki. Na wydruku są miejsca na podpis wykonawcy i przedstawiciela obiektu.

Pozytywny przegląd aktualizuje datę ostatniego przeglądu (starszy wpis nie cofa daty). Negatywny lub warunkowy wynik nie przesuwa terminu i oznacza centralę „Wymaga serwisu”. Po naprawie zweryfikuj stan urządzenia i zaktualizuj go świadomie w ewidencji — aplikacja nie zakłada automatycznie, że wszystkie usterki usunięto. Powiązane zgłoszenie jest zamykane tylko po pozytywnym zatwierdzeniu i zaznaczeniu odpowiedniej opcji.

Termin wyliczamy w miesiącach kalendarzowych: 31 stycznia + 1 miesiąc to ostatni dzień lutego. Daty formularzy korzystają z lokalnego czasu komputera. Filtr historii „Do” obejmuje cały wskazany dzień.

## Pliki, konfiguracja i kopie

- `db_polon_ssp.json` — baza; odczyt UTF-8 lub UTF-16 ze starej wersji HTA, zapis UTF-8.
- `config.json` — ustawienia startu (`port`, `database`, `open_browser`) oraz `service` (firma, obiekt, szablony). Firma i szablony są edytowane w interfejsie. Zmiana portu/nazwy bazy wymaga restartu; zmiana nazwy wybiera inny plik, nie przenosi danych.
- `backups/` — maksymalnie 30 ostatnich kopii każdej bazy. Powstają przed zapisem/importem i na żądanie.
- `*.json.bak` — poprzednia wersja bazy lub konfiguracji.
- `runtime/` — przenośne środowisko Windows, bez instalacji.

Kopie można pobrać z zakładki „Kopie i import”, a następnie zaimportować po potwierdzeniu zastąpienia bazy. **Import jest świadomym zastąpieniem całej bazy, także protokołów zatwierdzonych.** Najpierw zachowywana jest kopia bieżących danych. Uszkodzona baza nie jest zastępowana automatycznie; zatrzymaj program, zachowaj uszkodzony plik i ręcznie przywróć wybraną kopię. Przechowuj również kopię folderu na osobnym nośniku.

Zapis sprawdza wersję pliku: drugie okno nie nadpisze zmian niezauważenie. Błąd pozostawia formularz otwarty. Przed odświeżeniem przy konflikcie skopiuj niezapisane treści w bezpieczne miejsce. Dziennik zawiera ostatnie 1000 zapisów bazy i zmienione identyfikatory; nie jest rejestrem uwierzytelnionych użytkowników.

## Zakres i dalszy rozwój

[Plan rozwoju](docs/PLAN-ROZWOJU.md) · [Zmiany wersji 2.0](docs/ZMIANY-2.0.md)

Program jest przeznaczony dla jednego lokalnego stanowiska, bez współdzielenia pliku przez sieć. Nazwiska na protokole są wpisami użytkownika, a podpisy składa się na wydruku. Szablon kontroli należy dostosować do dokumentacji urządzeń i procedur obiektu; aplikacja nie potwierdza zgodności przeglądu z normami. Wersja nie obejmuje załączników binarnych, magazynu części, rozliczeń ani integracji z centralami. Jeśli polityka domeny blokuje przenośne EXE, potrzebne jest dopuszczenie przez IT.

## Rozwój i weryfikacja

Kod korzysta wyłącznie ze standardowej biblioteki Pythona 3.10+ i lokalnego JavaScript/CSS. Dla dewelopera:

```
python server.py --no-browser
python -m unittest discover -s tests -v
python tests/browser_smoke.py
python tools/build_release.py
```

Test przeglądarkowy wymaga Playwright i Chromium (tylko środowisko deweloperskie). Testy korzystają z osobnych katalogów tymczasowych. Sprawdzamy migrację, konflikty, numerację, niezmienność protokołów, kopie, konfigurację, pozytywne/negatywne przeglądy i scenariusze użytkownika z wydrukiem PDF. Testy wykonano na Linuksie/Chromium; nową wersję trzeba sprawdzić także na docelowym Windows. Przenośny runtime/launcher jest tym samym rozwiązaniem, którego uruchomienie potwierdzono dla wersji 1.

Runtime: Python Software Foundation, Python 3.13.16 x64 z https://api.nuget.org/v3-flatcontainer/python/3.13.16/python.3.13.16.nupkg . Przy pobraniu zweryfikowano SHA-512 z metadanych HTTPS i integralność ZIP. Licencja znajduje się w `runtime/LICENSE.txt`. Budowanie pełnej paczki wymaga istniejącego, zweryfikowanego katalogu runtime; skrypt niczego nie pobiera.

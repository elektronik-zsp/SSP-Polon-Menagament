# CommandFIRE SSP Serwis 2.11.1

Program portable Windows x64, bez instalowania osobnego serwera i bez dostępu do internetu.
Lokalny proces programu obsługuje interfejs przeglądarki na 127.0.0.1, tak jak w 2.5.6.

Nowa instalacja: wypakuj paczkę, wejdź do SSP-Polon i uruchom Uruchom.bat.
Aktualizacja: zatrzymaj wszystkie stanowiska, zamknij menedżer i uruchom Aktualizuj.bat
z głównego folderu rozpakowanej paczki. Wskaż dotychczasowy folder SSP-Polon.
Powstanie zweryfikowana kopia programu, konfiguracji i bazy w update-backups.
Dotychczasowe dane, konta i konfiguracja pozostają na miejscu.
Zaktualizuj wszystkie stanowiska korzystające ze wspólnej bazy.

Poprawka wyglądu: jednolite pola, etykiety, odstępy i przyciski w formularzach modalnych.
Zmiany opisano w docs/ZMIANY-2.11.1.md.
Paczka jest czysta: bez danych, kont, haseł, konfiguracji i kopii użytkownika.

﻿> Czyste wydanie portable 2.5.6: rozpocznij od START-TUTAJ.txt. Instrukcje aktualizacji poniżej dotyczą istniejących instalacji.

## 2.5.3 — automatyczna synchronizacja wspólnej bazy

Co 5 sekund lokalne stanowisko kontroluje rewizję wspólnej bazy. Zmienione dane odświeżają się automatycznie, pojawiają się powiadomienia. Edycja formularzy jest chroniona. Szczegóły: `docs/SYNCHRONIZACJA-2.5.3.md`.

# CommandFIRE SSP Serwis 2.5.2

Przenośny program do obsługi przeglądów, central SSP i zgłoszeń serwisowych. Działa lokalnie na Windows 10/11 x64 z przenośnym Pythonem (folder `runtime` jest dołączony do tej paczki). Nie wymaga nowych instalacji ani serwera centralnego.

**NOWOŚĆ 2.5.1 — administracja bazą i licencja:** przyciski eksportu i tworzenia kopii zostały usunięte z nagłówka. Wszystkie operacje na bazie znajdziesz w zakładce **Baza danych** dostępnej wyłącznie dla ADMIN; serwer sprawdza rolę przy API kopii i importu. Dodano stopkę autorską i publiczną stronę `/licencja` z warunkami wewnętrznego używania dla ZSP Synthos. Pełny tekst: [`LICENCJA-COMMANDFIRE-SSP-SERWIS.txt`](LICENCJA-COMMANDFIRE-SSP-SERWIS.txt). Szczegóły i bezpieczeństwo: [`docs/ZMIANY-2.5.1-BAZA-LICENCJA.md`](docs/ZMIANY-2.5.1-BAZA-LICENCJA.md).

**NOWOŚĆ 2.5.2 — nowa nazwa:** **CommandFIRE SSP Serwis** jest widoczna w programie, logowaniu, menedżerze tray i licencji. Dane i konta pozostają bez zmian. Wystarczy podmienić pliki aplikacji na wszystkich stanowiskach. Szczegóły: [`docs/ZMIANY-2.5.2-NAZWA.md`](docs/ZMIANY-2.5.2-NAZWA.md).

**Prawa autorskie:** © 2026 Arkadiusz Bartula. Wszelkie prawa zastrzeżone. ELEKTRONIK – Arkadiusz Bartula, NIP: 549-226-34-51. Kontakt: akradiusz.bartula@gmail.com, +48 531 531 622. Zastrzeżenie dotyczy oryginalnych elementów programu z poszanowaniem praw osób trzecich oraz ewentualnych postanowień umownych o prawach autorskich.

**NOWOŚĆ 2.5.0 — logowanie i uprawnienia:** administrator tworzy użytkowników, przypisuje role `ADMIN`, `SERWISANT`, `DYSPOZYTOR`, `ODCZYT`, nadaje szczegółowe uprawnienia, resetuje hasła i blokuje konta. Hasła są haszowane, pierwsza zmiana hasła jest wymuszana; historia zgłoszeń i dziennik zapisów identyfikują zalogowane konto.

**Przy pierwotnym wdrożeniu kont (2.5.0):** zatrzymaj wszystkie stanowiska, wykonaj kopię wspólnej bazy i wgraj 2.5.0 na każdy komputer. Na jednym stanowisku uruchom `Utworz_pierwszego_admina.bat`. Nie ma domyślnego hasła. Po tej operacji starsze wersje 2.4.x nie mogą już otwierać wspólnej bazy (schemaVersion 4). Szczegółowa instrukcja, zasady uprawnień i **istotne ograniczenia bezpieczeństwa wspólnego JSON**: [`docs/ZMIANY-2.5.0-UZYTKOWNICY.md`](docs/ZMIANY-2.5.0-UZYTKOWNICY.md).

**POPRAWKA 2.4.3:** rozwiązano błąd uruchomienia menedżera wynikający z nieistniejącego typu `wintypes.HCURSOR`. Zamiast milczącego zakończenia skrypt wyświetla błąd i zapisuje go w `%LOCALAPPDATA%\SSP-Polon\<id>\manager.log`. Gdy problem się powtarza, uruchom `Diagnoza_Menedzera.bat` i prześlij treść błędu. Zmiany dotyczą tylko menedżera.

**NOWOŚĆ 2.4.2 — jedno okno menedżera i tray:** dwukrotnie kliknij `SSP_Polon_Manager.vbs`. W oknie masz przyciski **Uruchom**, **Zatrzymaj**, **Otwórz panel** i **Minimalizuj do tray** oraz stan serwera i wspólnej bazy. `X` i minimalizacja ukrywają jedynie okno sterowania, a serwer nadal pracuje; kliknięcie ikony tray przywraca okno. Menedżer nie wymaga instalacji ani PowerShella, wykorzystuje natywne funkcje Windows i istniejący przenośny Python. `Uruchom_w_tle.vbs` i `Uruchom.bat` również otwierają menedżer. Instrukcja i analiza ryzyk: `docs/ZMIANY-2.4.2-MENEDZER-TRAY.md`.

**NOWOŚĆ 2.4.1 — uruchamianie w tle, bez instalacji:** aplikacja działa jako lokalny proces Pythona bez stałego okna konsoli. Po dwukrotnym kliknięciu `Uruchom_w_tle.vbs` otwiera się przeglądarka; nie trzeba pozostawiać żadnego okna BAT. `Zatrzymaj_SSP_Polon.vbs` kończy tylko tę instancję, a `Sprawdz_status.vbs` pokazuje stan działania i dostępność wspólnej bazy. Gdy firmowe zasady blokują pliki VBS, używaj odpowiednich plików `.bat` — konsola pojawi się wyłącznie podczas polecenia, sam serwer nadal pozostanie ukryty. Szczegółowa instrukcja i analiza ryzyk: `docs/ZMIANY-2.4.1-I-BEZPIECZENSTWO.md`.

**Wersja 2.5.2 zmienia wyłącznie oznaczenia aplikacji (rebranding).** Zostaw nazwę istniejącego folderu i skryptów uruchamiających; nowy skrót `CommandFIRE_SSP_Serwis.vbs` działa obok dotychczasowego `SSP_Polon_Manager.vbs`. Nowa wersja nadal korzysta z istniejących ścieżek `%LOCALAPPDATA%\SSP-Polon`, portu i `db_polon_ssp.json`. Nie zmieniaj `config.json`, istniejącej wspólnej bazy `db_polon_ssp.json` ani folderu `runtime`. **Nie kopiuj plików sterujących i logów z `%LOCALAPPDATA%` na dysk sieciowy.**

**NOWOŚĆ 2.4.0:** konfigurowalne, niezależne serie numerów dla zgłoszeń, przeglądów i protokołów oraz nowy pulpit z centralami i obiektami wymagającymi interwencji, wykresami i podsumowaniem otwartych prac. Numeracja jest nadawana automatycznie we wspólnej bazie pod blokadą pliku, aby nie powstawały duplikaty przy jednoczesnym zapisie. Szczegóły: `docs/ZMIANY-2.4.0.md`.

Od wersji 2.3.1 program instaluje się osobno (lokalnie) na każdym komputerze, a **baza `db_polon_ssp.json` może znajdować się we wspólnym folderze sieciowym**. W bazie zapisywane są blokady edycji konkretnego zgłoszenia lub centrali. Blokady wygasają po 30 minutach bezczynności. Inni pracownicy mogą w tym czasie czytać dane i edytować **inne** rekordy.

## Pierwsze użycie — Windows

1. Zamknij wszystkie kopie starego CommandFIRE SSP Serwis i zrób kopię istniejącej bazy.
2. Z archiwum aktualizacji skopiuj folder `SSP-Polon` do istniejącej lokalnej instalacji, zachowując `runtime`, stary `config.json` i lokalną bazę.
3. **Główny komputer** — otwórz `Konfiguruj_wspolna_baze.bat`, wpisz ścieżkę udziału UNC, np. `\\KOMPUTER-ZSP\Serwis\db_polon_ssp.json`. Konfigurator zaproponuje skopiowanie aktualnej lokalnej bazy, jeśli docelowy plik jeszcze nie istnieje.
4. Sprawdź w aplikacji, że dane zostały odczytane ze wspólnego pliku. Jeśli importowana baza nie miała wspólnej konfiguracji, otwórz Konfigurację i zapisz ją raz na głównym komputerze.
5. **Pozostałe komputery** — uruchom ten sam konfigurator i podaj identyczną ścieżkę do istniejącej wspólnej bazy. Nie kopiuj ich starych baz na dysk sieciowy.
6. Uruchom `SSP_Polon_Manager.vbs` na każdym komputerze. W oknie kliknij **Uruchom**, aby otworzyć lokalny adres przeglądarki `http://127.0.0.1:8765`, a na zakończenie pracy **Zatrzymaj**. Działają także `Uruchom_w_tle.vbs` i `Uruchom.bat`, które otwierają menedżer.

Ważne: wszyscy muszą mieć prawo modyfikacji plików na udziale, włącznie z tworzeniem pliku `.mutex`, tworzeniem kopii, zmianą nazwy i kasowaniem plików. **Wszystkie stanowiska muszą używać kompatybilnej wersji 2.5.x po wdrożeniu kont**.

## Jak działa blokada

Otwierasz formularz edycji centrali `CSP-01`: aplikacja rezerwuje `panels/CSP-01`. Inna osoba może przeczytać informacje o tej centrali, lecz po kliknięciu „Edytuj” zobaczy komunikat o zajęciu, z nazwą zalogowanego użytkownika CommandFIRE SSP Serwis i komputera. Może w tym czasie edytować `CSP-02`, a także inne zgłoszenie. Podobnie działa dopisywanie historii konkretnego zgłoszenia i edycja protokołów.

Po zamknięciu formularza blokada jest zwalniana. W razie zamknięcia programu, awarii lub 30 minut bezczynności druga osoba może przejąć edycję. Kliknięcia lub samo podglądanie treści nie przedłuża sesji — liczą się czynności w formularzu. **Sam plik JSON ma pole `activeSessions`**, zaś plik `.mutex` obok niego chroni krytyczny zapis przed równoczesną zmianą.

Wszyscy widzą bieżącą bazę po naciśnięciu **Odśwież**. Jeśli ktoś edytuje inną centralę lub zgłoszenie, oba zapisy są scalane. Zmiany tego samego rekordu z przestarzałego formularza są odrzucane. Nie wolno modyfikować wspólnej bazy przy użyciu starszej wersji programu.

## Obsługa zgłoszeń

Statusy: **Nowe, W realizacji, Zakończone, Anulowane**. Każde zgłoszenie ma nieedytowalną historię z datą, nazwiskiem, opisem prac i zmianą statusu. Przykład: pierwszy serwisant diagnozuje uszkodzoną czujkę i zapisuje potrzebną część; kolejny serwisant dopisuje wymianę i kończy zgłoszenie.

Są też ewidencja i harmonogram central, przeglądy, protokoły, kopie, eksport/import oraz rejestr zmian.

**Instrukcja techniczna:** [docs/ZMIANY-2.4.0.md](docs/ZMIANY-2.4.0.md). Wersja ta jest rozwiązaniem przejściowym dla małego zespołu, nie zastępuje serwera i bazy transakcyjnej. Regularnie kopiuj wspólną bazę poza udział. Wykonaj testy na Waszym Windows SMB przed normalną pracą.

## Testy deweloperskie

W środowisku z Pythonem 3 uruchom `python -m unittest discover -s tests -p 'test_*.py'`. Wydanie 2.5.2 zawiera aktualne testy uwierzytelniania, uruchamiania w tle, ikon i menedżera; historyczne testy 2.4 wymagające dostępu bez logowania nie są częścią nowego ZIP. Testy serwera nie wymagają zewnętrznych bibliotek. Test automatyczny przeglądarki jest opcjonalny (Playwright/Chromium w środowisku deweloperskim). Do normalnej pracy nie potrzeba Playwright.

## Konfiguracja numeracji — 2.4.0

W **Konfiguracja → Edytuj konfigurację i numerację** ustaw osobno prefiks, numer początkowy, liczbę cyfr (1–9) i tryb: roczny (np. `ZG/2026/0001`) lub ciągły (np. `ZG/0001`). Domyślne serie: `ZG`, `PRZ` i `SSP`. Każda seria musi mieć własny prefiks.

Numer zgłoszenia powstaje w chwili jego rejestracji. Numer przeglądu i numer protokołu są nadawane dopiero przy zatwierdzaniu dokumentu; zatwierdzony przegląd otrzymuje oba numery. Wcześniejsze dokumenty i zgłoszenia **zachowują swoje stare numery**. Zmiana prefiksu lub numeru początkowego nie zmienia przeszłych zapisów, a kolejny numer jest obliczany z już zajętych numerów danej serii.

Na pulpicie widoczne są: centrale wymagające uwagi (wraz z nazwą obiektu, miejscem, stanem, terminem i liczbą otwartych zgłoszeń), wskaźniki operacyjne, wykresy statusów, terminów i liczby zgłoszeń/protokołów z ostatnich sześciu miesięcy oraz lista zgłoszeń do obsługi. Przyciskiem **Odśwież** można ponownie odczytać wspólną bazę.

**Bezpieczeństwo:** wykonaj kopię danych przed aktualizacją; na wszystkich stanowiskach wymień pliki aplikacji, ale **nie nadpisuj `config.json`, `runtime` ani pliku bazy**. Nie mieszaj wersji 2.3.1 i 2.4.0 pracujących równocześnie. Kopie przechowywane na tym samym współdzielonym dysku nie chronią przed jego awarią. Testy SMB na dwóch stanowiskach nadal należy wykonać w środowisku docelowym.



### Ikona programu (2.4.5)

- Okno menedżera i ikona tray używają pliku `favicon.ico` w katalogu `SSP-Polon`.
- W przeglądarce ikona karty oraz znak w nagłówku korzystają z `favicon.png`; endpointy `/favicon.ico` i `/favicon.png` są obsługiwane przez lokalny serwer.
- Po wymianie plików zatrzymaj i ponownie uruchom serwer oraz menedżera, potem wykonaj Ctrl+F5 w przeglądarce.
- Nie zmieniaj `config.json`, `runtime` ani wspólnej bazy JSON.

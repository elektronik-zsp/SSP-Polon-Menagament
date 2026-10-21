# SSP Polon 2.5.0 — konta, role i uprawnienia

## Założenia

Aplikacja pozostaje lokalna na każdym komputerze, wspólna baza JSON jest na dotychczasowym udziale Windows/SMB. Nie instaluje się SQL, usług, frameworków ani dodatkowych bibliotek. Nadal działa SSP Polon Manager/tray.

## Pierwsze uruchomienie (ważna kolejność!)

1. Zapewnij, że **nikt nie pracuje** w SSP Polon, zatrzymaj wszystkie działające serwery i menedżery, zrób pełną kopię bazy poza udziałem sieciowym.
2. Wgraj wersję **2.5.0 na wszystkie stanowiska**. Nie włączaj jeszcze programu z żadnego komputera. Zachowaj `config.json`, wspólny `db_polon_ssp.json`, `runtime` i istniejące kopie.
3. Na jednym upoważnionym stanowisku uruchom `Utworz_pierwszego_admina.bat` i podaj własny login, nazwę oraz hasło minimum 12 znaków. Kreator wykorzystuje ścieżkę bazy z miejscowego `config.json` (np. `\\KOMPUTER-ZSP\Serwis\db_polon_ssp.json`). Hasło jest wpisywane w konsoli bez echa.
4. Kreator wykona kopię `db_polon_ssp.json.przed-kontami.bak` obok bazy, jeśli kopia z tej operacji jeszcze nie istnieje; następnie bezpiecznie, pod blokadą mutex, zapisze konto i podniesie format bazy do wersji 4.
5. Uruchom lokalny menedżer, kliknij **Uruchom**, otwórz przeglądarkę, zaloguj się kontem administratora i przejdź do **Użytkownicy**.
6. Dodaj pracowników, nadaj role i osobne uprawnienia. Wydaj im indywidualne hasła początkowe; po pierwszym logowaniu program wymusi zmianę hasła.
7. Na drugim komputerze sprawdź logowanie, odmowę edycji bez uprawnień i blokadę jednego zgłoszenia.

**Nie ustawiono hasła domyślnego.** Inicjalizacja konta administratora możliwa jest wyłącznie z lokalnego skryptu i tylko wtedy, gdy wspólna baza nie zawiera żadnych użytkowników. Administracyjne założenie kolejnych kont odbywa się przez interfejs.

## Role i uprawnienia

| Rola | Standardowy zakres |
| --- | --- |
| ADMIN | wszystkie uprawnienia; zarządzanie kontami i hasłami, import i konfiguracja |
| SERWISANT | podgląd central, zgłoszenia, dopisywanie czynności, protokoły i przeglądy łącznie z zatwierdzaniem |
| DYSPOZYTOR | podgląd central/protokołów, tworzenie i obsługa zgłoszeń, bez zatwierdzania protokołów |
| ODCZYT | wyłącznie podgląd pulpitu, central, zgłoszeń, protokołów i ustawień |

Administrator może dostosować poszczególne uprawnienia kont nieadministracyjnych: podgląd i edycja central, podgląd i edycja zgłoszeń, podgląd/tworzenie/zatwierdzanie protokołów, konfiguracja, wykresy i pulpit, lista kopii, import, dziennik. **Zarządzanie kontami przysługuje tylko roli ADMIN**, niezależnie od ręcznie zaznaczonej listy.

Uprawnienia są egzekwowane w backendzie podczas żądań HTTP, **nie wyłącznie przez ukrycie przycisku**. Serwer nie udostępnia zwykłym widokom skrótów haseł ani wewnętrznych identyfikatorów blokad. Konto nieaktywne nie może się zalogować, zmiana roli/hasła lub blokada natychmiast unieważniają dotychczasową lokalną sesję. Dostęp do listy użytkowników oraz surowych plików kopii bazy jest administracyjny.

Hasła są przechowywane jako skróty PBKDF2-HMAC-SHA256 z losową indywidualną solą i 350 tysiącami iteracji. Hasła nie są przechowywane w postaci jawnej. Sesja przeglądarki istnieje tylko w bieżącym lokalnym procesie serwera; wygasa po 8 godzinach bez żądań, przy wylogowaniu, wyłączeniu procesu lub zmianie konta. Blokady edycji nadal mają odrębny limit 30 minut bezczynności.

Zgłoszenie i historia: każdy nowy wpis otrzymuje nazwę i identyfikator **zalogowanego konta**, a gdy rzeczywisty wykonawca jest inny, jest dodatkowo zapisany jako `performedBy`.

## Szczególnie istotne ograniczenie obecnej architektury

**Konta i uprawnienia to kontrola dostępu do aplikacji, a nie pełna ochrona przed osobą mogącą ręcznie edytować plik na udziale SMB.** Każde konto Windows mające prawo zapisu do wspólnego JSON może ominąć program i zmienić w tym pliku role, dane albo skróty haseł, np. przez zwykły edytor tekstu. Także pliki w `backups`, `.bak` i kopia inicjalizacyjna zawierają rekordy użytkowników. Ochronę plików i kopii na poziomie systemu Windows należy ustanowić odpowiednimi uprawnieniami udziału/NTFS, lecz jeśli wszyscy muszą zapisywać bezpośrednio do JSON, nie można uzyskać silnego rozdzielenia uprawnień administracyjnych. **Wrażliwych haseł nie wolno używać ponownie w innych systemach.** Pełną kontrolę uprawnień i logowania zapewni późniejsza wersja na dedykowanym serwerze z bazą danych i scentralizowanym uwierzytelnianiem.

## Zabezpieczenie przed starszymi wersjami

Przy pierwszym utworzeniu administratora baza przechodzi na `schemaVersion: 4`. SSP Polon 2.4.x akceptuje wyłącznie wersje 1–3, dlatego odmówi odczytu i zapisu nowej bazy. Zapobiega to skasowaniu nowych rekordów kont przez stary backend. Nie mieszaj wersji i **nie zmieniaj ręcznie schemaVersion**.

## Zgodność i kopie zapasowe

Dane central, zgłoszeń, protokołów, numeracje, historia i konfiguracja pozostają na miejscu. Import starego pliku bazy przez administratora **zachowuje obecne konta użytkowników** zamiast je zastępować zawartością importu. Nie podmieniaj bezpośrednio pliku bazy ręcznym kopiowaniem podczas pracy.

W paczce aktualizacyjnej nie ma `runtime`, `config.json` ani `db_polon_ssp.json`. Nowe pliki: `auth_users.py`, `Utworz_pierwszego_admina.bat`, `tools/utworz_admina.py`. Zmienione: `server.py`, `app.js`, `index.html`, `style.css`, `tools/launcher.py`, `tools/manager.py`.

Testy wykonane w środowisku przygotowania: backend auth/permissions, unieważnienie sesji, lokalne dwa serwery współdzielące JSON, import, wersja schematu, menedżer/launcher. Test rzeczywistego środowiska Windows + udział SMB jest konieczny przed wdrożeniem. Test automatycznej przeglądarki Chromium nie powiódł się z powodu polityki dostępu do localhost w środowisku testowym, nie ze względu na potwierdzony błąd UI.

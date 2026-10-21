# SSP Polon 2.3 — lokalne komputery, wspólna baza plikowa

## Co zmieniono

- Każdy komputer uruchamia własne `SSP-Polon` z lokalnego folderu, bez instalowania programów ani uruchamiania centralnego serwera WWW.
- W `config.json` każdego komputera pole `database` wskazuje ten sam plik JSON w **udostępnionym folderze Windows** (UNC, ewentualnie identyczny dostępny dysk mapowany).
- Wewnątrz bazy powstaje pole `activeSessions`, gdzie dla edytowanego zgłoszenia, centrali, szkicu protokołu lub ustawień zapisano kto je edytuje i czas ostatniej czynności.
- Inny użytkownik może je **oglądać**, ale próba **edycji tego samego rekordu** wyświetla, kto go edytuje, bez otwierania formularza. Może równocześnie zmieniać inne zgłoszenia/centrale.
- Zapis historii zgłoszeń nadal zachowuje nazwisko serwisanta, automatyczną datę, opis czynności i zmianę statusu (Nowe, W realizacji, Zakończone, Anulowane).
- Blokada znika przy normalnym wyjściu z formularza. Po 30 minutach bez pisania/zmiany pól wygasa bez dodatkowych czynności, nawet gdy komputer został wyłączony. Kontrolę terminu egzekwuje serwer lokalny przy następnym żądaniu.
- We wspólnym folderze utworzony zostanie dodatkowo **`db_polon_ssp.json.mutex`** (lub analogiczna nazwa). To techniczna blokada plikowa obsługiwana przez Windows/SMB, potrzebna do bezpiecznego zapisywania jednego JSON z kilku komputerów. **Nie usuwać tego pliku podczas pracy.**
- Zapisy do odmiennych rekordów są scalane z najświeższą zawartością pliku. Próby modyfikacji tego samego rekordu przy nieaktualnej wersji są odrzucane, zamiast nadpisywać inną pracę.
- Zatwierdzanie protokołu, które zmienia dane centrali albo dopisuje zdarzenie do zgłoszenia, nie jest dozwolone, jeśli te rekordy właśnie edytuje ktoś inny.
- Wspólna konfiguracja serwisu znajduje się teraz w bazie w polu `serviceConfig`. Lokalny `config.json` służy przede wszystkim do wskazania lokalnego portu i wspólnego pliku.
- Kopie zapasowe są wykonywane **przy pliku wspólnej bazy**, w podfolderze `backups`; `.json.bak` zachowuje poprzednią wersję przed zapisem danych.
- Import całej bazy wymaga zwolnienia wszystkich edytowanych rekordów.

## Instalacja i pierwsze uruchomienie

1. **Zamknij aplikacje** na wszystkich komputerach i wykonaj kopię całego folderu dotychczasowego programu, w szczególności `db_polon_ssp.json` i `config.json`.
2. Wgraj pliki wersji 2.3 do lokalnego folderu SSP Polon **na każdym komputerze**, nadpisując pliki programu. Zachowaj `runtime`, własny plik bazy i `config.json`.
3. Na komputerze z prawidłową, najbardziej aktualną bazą uruchom `Konfiguruj_wspolna_baze.bat`. Podaj docelową ścieżkę, np. `\\KOMPUTER-ZSP\Serwis\db_polon_ssp.json`. Jeśli plik nie istnieje, konfigurator zaproponuje przeniesienie lokalnej bazy do udziału. **Tylko raz** wykonaj tę operację z głównego komputera.
4. Uruchom program i sprawdź centrale/zgłoszenia. Jeśli plik pochodzi ze starszej wersji, zaloguj się na **głównym komputerze** i zapisz ustawienia w module Konfiguracja, aby zainicjalizować wspólne ustawienia firmy.
5. Na każdym pozostałym komputerze uruchom ten sam konfigurator i podaj **tę samą pełną ścieżkę**. Jeśli baza już istnieje, konfigurator nie nadpisze jej lokalnymi danymi.
6. Uruchamiaj aplikację tylko przez `Uruchom.bat` z folderu **lokalnego**, nigdy bezpośrednio z udziału sieciowego. Na każdym komputerze `http://127.0.0.1:8765` jest adresem wyłącznie tamtego komputera.
7. Otwórz tę samą centralę w dwóch programach, spróbuj edytować ją jednocześnie i zweryfikuj komunikat o zajęciu. Następnie przetestuj dwie różne centrale i osobne zgłoszenia.

Wszystkie osoby muszą mieć prawo odczytu, tworzenia, modyfikowania, **zmiany nazwy i usuwania** plików we wspólnym folderze, łącznie z możliwością tworzenia `backups/`. Plik musi znajdować się na zwykłym udziale SMB obsługującym blokady systemowe. Nie używaj synchronizacji OneDrive/Dropbox jako zamiennika udziału SMB.

## Co trzeba wiedzieć

- Nie ma jeszcze kont użytkowników ani serwera 24/7. Identyfikator edytora jest pobierany z konta Windows i nazwy komputera. Mechanizm zapobiega **przypadkowym** konfliktom, nie uniemożliwia administratorowi udziału ręcznego zmieniania JSON.
- Wymagane są sprawny udział sieciowy, połączenie i w miarę zgodne zegary komputerów. Jeśli udział jest odłączony, zapis może zakończyć się błędem; nie zmieniaj wówczas ponownie danych bez sprawdzenia, czy zapis się powiódł.
- Starsze SSP Polon 2.1.x nie mają mechanizmu blokad — nie wolno używać ich do zapisywania tej samej wspólnej bazy.
- Każdy zapis odbywa się pod krótkotrwałą techniczną blokadą SMB. Jest to rozwiązanie przejściowe; przy większej liczbie użytkowników docelowo warto przejść na serwer z transakcyjną bazą danych.
- Kopie pozostające na tym samym udostępnionym dysku nie chronią przed awarią ani skasowaniem udziału. Rób także kopie na **innym nośniku**.
- Sam mechanizm został przetestowany w symulacji dwóch lokalnych procesów. Przed udostępnieniem użytkownikom należy potwierdzić blokady i podmianę plików na Waszym **konkretnym udziale Windows**.

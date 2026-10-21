# CommandFIRE SSP Serwis 2.12.1 TEST

Wersja testowa, bez gwarancji działania na Windows. Interfejs HTML/CSS/JS zachowany z 2.12.0.

## Migracja JSON -> CFDB

1. Zamknij CommandFIRE na wszystkich stanowiskach, wykonaj niezależną kopię całego katalogu bazy.
2. Uruchom `Migracja_CFDB.bat` na testowym Windows i wybierz `1`.
3. Podaj pełną ścieżkę istniejącej bazy JSON. Program sprawdzi strukturę i zapisze kopię `.bak`, a następnie zaszyfruje bazę jako `.cfdb`.
4. Zapisz wyświetlony 64-znakowy klucz odzyskiwania poza udziałem sieciowym i potwierdź `ZAPISANE`.
5. Narzędzie ustawi lokalny `config.json` na `.cfdb`, a klucz zapisze lokalnie jako DPAPI. Oryginalny JSON nie jest usuwany.
6. Na pozostałych stanowiskach wybierz opcję `2`, podaj ścieżkę CFDB i klucz. Uruchamiaj tylko nową wersję programu.

**Ważne:** migracja nie uruchamia się bez potwierdzenia użytkownika, aby nie zmienić samoczynnie produkcyjnej bazy. Nie udostępniaj pliku klucza DPAPI ani klucza odzyskiwania. Stary JSON i jego kopie nadal zawierają jawne dane i trzeba je osobno zabezpieczyć.

**Ograniczenia:** wymagana biblioteka Python `cryptography` w środowisku uruchomieniowym Windows; dostarczony runtime nie został tutaj zweryfikowany pod kątem tej zależności. Nie zweryfikowano pracy na Windows/SMB, importów/odtworzenia backupu ani kompatybilności konfiguratora wspólnej bazy z CFDB. Nie wdrażać na produkcji bez testów.

# SSP Polon Serwis 2.1.1 — poprawka odczytu zgłoszeń

- Naprawiono `KeyError: 'toStatus'` w `validate_database()` przy odczycie bazy zawierającej dwa lub więcej zgłoszeń, z których wcześniejsze mają wpisy historii.
- Przyczyną było nadpisanie zmiennej `key`, która identyfikuje listę `faults`, podczas sprawdzania pól `author`/`text` oraz `fromStatus`/`toStatus` każdego wpisu historii. Pętle używają teraz odrębnych nazw zmiennych.
- Dodano testy regresyjne: dwie i więcej spraw z wpisami historii, odczyt przez API i zapis bez utraty danych.
- Format bazy bez zmian (schemaVersion 3). Nie wymaga importu ani migracji danych.

## Instalacja

Zamknij `Uruchom.bat`/okno serwera (Ctrl+C), zrób kopię folderu aplikacji, a następnie skopiuj pliki poprawki do istniejącego `SSP-Polon`, nadpisując pliki aplikacji. **Nie nadpisuj bazy `db_polon_ssp.json` ani katalogu `runtime/`.** Dla instalacji 2.1 wystarczy podmienić pojedynczy `server.py`. Uruchom aplikację ponownie.

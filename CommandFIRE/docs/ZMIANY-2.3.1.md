# SSP Polon 2.3.1 — poprawki bezpieczeństwa wspólnej bazy

- Poprawiono ekskluzywną blokadę przy imporcie: żaden drugi użytkownik nie może zapisywać nawet nowo dodanych zgłoszeń/central ani konfiguracji, dopóki trwa import.
- Sesje edycji pozostają w `activeSessions` wspólnej bazy JSON, a `*.mutex` zabezpiecza techniczny zapis z kilku komputerów.
- Instalacja jak dla wersji 2.3: lokalne foldery z programem, tylko baza na udziale SMB, bez instalowania dodatkowego oprogramowania.
- Aktualizacja 2.3 -> 2.3.1 wymaga zastąpienia plików programu na **każdym** komputerze i zamknięcia starych aplikacji przed podmianą. Nie zastępuj `runtime`, `config.json` ani `db_polon_ssp.json`.
- Testy lokalne nie dowodzą działania blokad na konkretnym serwerze Windows SMB. Wykonaj test na dwóch stanowiskach z kopią bazy przed produkcją.

# SSP Polon 2.4.5 — ikony aplikacji

- Dodano oryginalną ikonę SSP Polon z motywem ochrony przeciwpożarowej w `favicon.ico` (rozmiary 16–256 px) i `favicon.png`.
- Manager Win32 ładuje ikonę z lokalnego pliku (nie z runtime ani z dysku wspólnego) dla okna oraz tray; przy braku pliku zachowuje awaryjną ikonę Windows.
- Favicon jest dostarczany przez lokalny serwer jako `image/x-icon` i `image/png`, z wersjonowanym adresem w HTML, aby przeglądarka pobrała go ponownie.
- Ikona została również dodana do nagłówka aplikacji.
- Nie zmieniono bazy, `config.json`, blokad, protokołów ani mechanizmu uruchamiania.

## Szybka aktualizacja z 2.4.4

Podmień `tools/manager.py`, `server.py`, `index.html`, `style.css`; dodaj `favicon.ico`, `favicon.png`.
Zamknij menedżera i zatrzymaj dotychczasowy serwer przed podmianą plików (naciśnij Zatrzymaj). Włącz ponownie `SSP_Polon_Manager.vbs`.
Nie zmieniaj folderu `runtime`, `config.json` i pliku JSON na udziale sieciowym.

Uwaga: pracujące instancje serwera muszą być restartowane, aby wczytać nową trasę faviconu. Dla przeglądarki: Ctrl+F5.

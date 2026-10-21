# CommandFIRE SSP Serwis 2.11.1 — stylistyka formularzy

Ujednolicono formularze we wszystkich modalach:
- inputy, selecty i pola daty mają wysokość 40 px, wspólną czcionkę, obramowanie i zaokrąglenie;
- etykiety i odstępy mają spójny układ, także przy dłuższych nazwach;
- pola wielowierszowe mają domyślnie 112 px, a uwagi checklisty 64 px;
- checkboxy, listy uprawnień i wybór plików pasują do pozostałych pól;
- nagłówek i przyciski pozostają dostępne przy przewijaniu długiego formularza;
- przyciski zapisu i anulowania mają wspólną wysokość;
- węższe okna przełączają formularz na jedną kolumnę.

Zmiany są ograniczone do modali. Zachowano kompaktowe filtry nad tabelami.
Schemat bazy pozostaje 8. Dane, konta i logika formularzy nie ulegają zmianie.
Aktualizacja: zatrzymaj program, wypakuj paczkę osobno, uruchom Aktualizuj.bat.

Kontrola: sprawdzono składnię i dotychczasowe generowanie widoków JS oraz
integralność i pełne rozpakowanie ZIP po zapisaniu pliku do pobrania.
Nie wykonano wizualnej weryfikacji w rzeczywistej przeglądarce ani uruchomienia Windows.

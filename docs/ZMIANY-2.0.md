# Wersja 2.0.0 — zmiany

## Analiza wersji 1

- Brak dodawania central do pustej bazy i brak archiwizacji.
- Identyfikatory liczone na podstawie liczby rekordów mogły się powtarzać po imporcie.
- Każdy przegląd, również negatywny, zmieniał datę kolejnego przeglądu.
- Daty formularzy powstawały w UTC; dodawanie miesięcy mogło przeskakiwać do kolejnego miesiąca.
- Filtr końcowej daty pomijał część wpisów z wybranego dnia.
- Dane użytkownika były składane bezpośrednio do HTML, co umożliwiało wykonanie kodu z importowanej bazy.
- Brak dokumentu protokołu, konfiguracji firmy i trwałej migawki danych archiwalnych.
- Synchroniczne zapisy blokowały interfejs; brak rozbudowanej obsługi konfliktów i rotacji kopii.

## Wdrożenie

Nowy lokalny interfejs zachowuje zakres obsługi central, przeglądów, awarii i historii, porządkując go w moduły serwisowe. Dodano ewidencję, priorytety i terminy zgłoszeń, protokoły robocze/finalne, szablon kontroli, pomiary i uwagi, części, czas pracy, dane odbiorcy, wydruk A4/PDF oraz protokoły uzupełniające.

Numery protokołów są nadawane na serwerze przy zatwierdzeniu z uwzględnieniem istniejących numerów. Techniczne identyfikatory zgłoszeń i protokołów są UUID. Zatwierdzony protokół zachowuje migawki firmy i centrali, a normalny zapis nie pozwala go zmienić lub usunąć. Historia z wersji 1 pozostaje oznaczona jako historyczna; program nie fabrykuje dla niej podpisów, list kontrolnych ani pierwotnych danych firmy.

Konfiguracja jest dostępna w UI, zapisuje się w config.json i zachowuje ustawienia startu. Protokoły robocze zachowują szablon z chwili utworzenia. Dodano bezpieczne renderowanie tekstu, politykę CSP, walidację po stronie serwera, asynchroniczny zapis, blokadę powtórnego wysłania i potwierdzenie odrzucenia niezapisanych zmian.

Dane pozostają w pliku JSON. Pierwszy odczyt starej bazy nie zmienia pliku; pierwszy zapis wykonuje kopię. Rotacja zachowuje 30 kopii i poprzedni plik .bak. Rejestr ostatnich 1000 zapisów bazy ułatwia znalezienie zmienionych rekordów; nie jest mechanizmem tożsamości ani niezmiennym audytem prawnym.

## Dostarczenie

- Pełna paczka: program + przenośny runtime Windows.
- Aktualizacja: tylko program i dokumentacja; bez runtime, config.json i danych użytkownika.
- Żadna paczka 2.0 nie zawiera pliku bazy ani config.json. Brakująca konfiguracja powstaje podczas pierwszego uruchomienia.

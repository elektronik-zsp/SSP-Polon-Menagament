# CommandFIRE SSP Serwis 2.5.3 — synchronizacja bez centralnego serwera

## Jak działa

- Program i lokalny serwer pozostają na **każdym komputerze**. Wspólna baza JSON pozostaje na folderze sieciowym Windows / SMB.
- Co 5 sekund przeglądarka żąda `/api/sync` ze swojego serwera na `127.0.0.1`, który pod blokadą pliku sprawdza rewizję wspólnej bazy i statusy blokad. Odpowiedź jest niewielka, nie zawiera pełnej bazy ani danych haseł.
- Tylko po zmianie rewizji serwer udostępnia aktualne dane ze sprawdzeniem uprawnień. Dashboard, listy i szczegóły odświeżają się bez przeładowania strony.
- Nowe zgłoszenia, zmiany statusów, wpisy w historii, zmiany stanów central i zatwierdzone protokoły powodują powiadomienia. Powiadomienia są lokalne dla bieżącej sesji przeglądarki — bez dźwięków i powiadomień systemowych.
- Blokady są obserwowane, ale automatyczne odświeżanie **nie wykonuje** akcji `touch` ani nie przedłuża 30-minutowej blokady edycji. Nie przedłuża także czasu bezczynności sesji logowania.
- Jeśli formularz jest otwarty, stan ekranu nie jest nadpisywany. Zmiany oczekują na zamknięcie formularza. Serwer nadal wykrywa konflikt tego samego rekordu przy próbie zapisu.
- Utrata dostępu do SMB pokazuje „Brak synchronizacji”; program nie przełącza się na lokalny plik i nie ukrywa błędu zapisu.
- Po odzyskaniu połączenia synchronizacja wznawia działanie.

## Instalacja

1. Zatrzymaj aplikacje na wszystkich komputerach i zrób kopię wspólnej bazy.
2. Skopiuj `server.py`, `app.js`, `index.html`, `style.css` z nowej paczki na wszystkie komputery.
3. Nie nadpisuj `config.json`, `runtime`, wspólnego pliku bazy ani folderu `backups`.
4. Uruchom program i odśwież kartę przeglądarki klawiszami `Ctrl+F5` (nowe pliki mają wersję ?v=253).
5. Przetestuj na dwóch stanowiskach, tworząc dwa różne zgłoszenia i sprawdzając automatyczne powiadomienia.

## Ograniczenia

To jest **polling (co 5 sekund)**, nie WebSocket. Zdarzenia mogą pojawić się z kilkusekundowym opóźnieniem. Wzmożona aktywność wielu klientów podnosi liczbę odczytów pliku SMB; dla bardzo dużych baz lub większej liczby stanowisk wymagany będzie serwer z bazą SQL i WebSocket.
Testy automatyczne wykonywane są poza docelowym Windows i SMB — przed wdrożeniem trzeba sprawdzić oba stanowiska na rzeczywistym udziale.

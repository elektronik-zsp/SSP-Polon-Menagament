# SSP Polon Serwis 2.1 — historia zgłoszeń

## Najważniejsze zmiany

- Cztery statusy zgłoszeń: **Nowe / W realizacji / Zakończone / Anulowane**.
- Kliknięcie zgłoszenia otwiera osobną kartę: opis, stan, centralę, termin, serwisanta, protokoły i chronologiczną oś historii.
- **Dodaj wpis / zmień status** — autor, opis diagnozy/czynności/potrzebnych części i opcjonalnie nowy status. Jeden wpis może zawierać zmianę statusu; następny serwisant dopisuje kolejny wpis.
- Można zakończyć zgłoszenie bez protokołu, ale zawsze z nazwiskiem wykonawcy i opisem wykonanych prac; protokół dodatni ze świadomie zaznaczoną opcją zamyka je automatycznie.
- Zatwierdzone powiązane protokoły trafiają do historii zgłoszenia także bez jego zamykania.
- Poprzednie wpisy są niemodyfikowalne przy zwykłym zapisie, a ich znaczniki czasu nadaje lokalny serwer. Nie jest to system logowania ani podpis cyfrowy.
- Edycja podstawowych danych zgłoszenia dopisuje techniczny ślad zmiany.
- Wersja bazy 3, migracja z wersji 1 i 2 zachowuje istniejące dane i pola niestandardowe.
- Zmiana nazwy dawnych statusów przy odczycie: W trakcie/Oczekujące → W realizacji; Zamknięte → Zakończone.
- Nie odtwarza się historii starych czynności. Przy pierwszym zapisie starszego zgłoszenia pojawia się znacznik migracji.
- Zmiana statusu bez nowego wpisu jest odrzucana, wyjątek stanowi zamknięcie zatwierdzonym protokołem.
- Statusy końcowe (Zakończone, Anulowane) nie blokują archiwizacji centrali.

## Przykład

1. Dyspozytor tworzy zgłoszenie „Uszkodzenie czujki”. Status: Nowe.
2. Jan dodaje wpis „Czujka uszkodzona, wymagana wymiana, brak części” i ustawia „W realizacji”.
3. Anna dodaje kolejny wpis „Wymieniono czujkę, próba alarmu prawidłowa” i ustawia „Zakończone”.
4. Cały przebieg i nazwiska są dostępne na karcie tego samego zgłoszenia.

## Aktualizacja

Zamknij program. Zrób kopię starego folderu. Wypakuj archiwum aktualizacji i **skopiuj zawartość `SSP-Polon`** nad istniejące pliki. Zachowaj `runtime/`, `config.json` i `db_polon_ssp.json`. Uruchom `Uruchom.bat`. Pierwszy zapis tworzy kopię starej bazy przed aktualizacją schematu.

Nie uruchamiaj starszego wydania 2.0 na bazie zapisanej przez 2.1 — użyj kopii i zachowaj kompletny folder z poprzednią wersją, jeśli konieczny jest powrót.

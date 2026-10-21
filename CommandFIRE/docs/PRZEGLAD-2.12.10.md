# Przegląd CommandFIRE 2.12.9 i poprawki 2.12.10-TEST

Przegląd dotyczy kodu z przesłanej paczki Portable, przede wszystkim zapisu
bazy, CFDB, kont, uprawnień, zgłoszeń i formularzy. Nie korzysta z bazy produkcyjnej.

## Ocena architektury

Lokalny serwer i przenośny Python pozwalają obsłużyć pliki bez ograniczeń
przeglądarki i instalacji systemowej. Aplikacja ma już istotne mechanizmy:
walidację danych po stronie serwera, blokady rekordów, kontrolę zmian,
kopie zapasowe, role, niezmienne protokoły i dopisywaną historię zgłoszenia.
CFDB szyfruje plik; DPAPI chroni lokalną kopię klucza dla konta Windows.

## Naprawione problemy

| Problem | Zmiana i weryfikacja |
| --- | --- |
| Narzędzie pierwszego administratora czytało i zapisywało tylko JSON | Wspólny kodek z serwerem; test zapisu konta do CFDB i zachowania zaszyfrowanej kopii |
| Konfigurator tworzył CFDB przed zabezpieczeniem klucza i sprawdzeniem config.json | Preflight konfiguracji, zabezpieczenie i zapis klucza przed bazą; testy awarii DPAPI, konfiguracji i dysku |
| Funkcja LocalFree nie miała jawnych typów wskaźników | Jawna sygnatura ctypes dla Windows 64-bit; wymaga testu natywnego Windows |
| Ograniczony widok użytkownika odrzucał zgłoszenie z niewidocznym protokołem źródłowym | Częściowy widok toleruje nieobecny protokół; pełna baza nadal wymaga poprawnego powiązania |
| Zapis kont nie blokował podwójnego wysłania; formularz pozostawał aktywny podczas odczytu załączników | Blokada od początku zapisu; odtworzenie poprzedniego stanu pól po błędzie |
| Wszystkie pola były ponownie aktywowane po błędzie, także pola uprawnień administratora | Zapamiętanie i odtworzenie indywidualnych blokad |
| Długie formularze utrudniały dotarcie do przycisków | Osobno przewijana treść, stały nagłówek i stopka, sekcje i wymagane pola |
| Warunki zakończenia zgłoszenia były sprawdzane dopiero przez serwer | Dynamicznie wymagane pola przyczyny, naprawy i weryfikacji; sprawdzenie w Chromium |
| Budowanie paczki pomijało skrypty .ps1 | Dołączenie PowerShell, wykluczenie .git, aktualizacja numeru wydania |

Formularz zgłoszenia już prawidłowo odświeżał powiązania po zmianie centrali;
nie wymagał zmiany tej logiki. Nie zmieniono schematu bazy (wersja 8),
algorytmu szyfrowania, formatu historii ani istniejących uprawnień.

## Weryfikacja

- 39 testów Python: walidacja, workflow, API, uprawnienia, koszty, planowanie,
  słownik elementów, szyfrowanie i nowe regresje.
- Dotychczasowy test JavaScript uruchamiany w Node: pozytywny.
- Chromium z rzeczywistym serwerem: logowanie, nowe zgłoszenie, pierwszy
  wykonawca oczekujący na część, drugi wykonawca kończący naprawę, wymagalność
  pól i zapis obu wpisów na dysku; brak błędów JavaScript.
- Układ formularza przy szerokości 1366 i 390 pikseli, oględziny zrzutów.

Polecenia dla środowiska deweloperskiego:

```text
python -m unittest discover -s tests -p 'test_*.py'
node tests/test_ui_260.cjs
python tests/browser_review_21210.py
```

Test przeglądarki wymaga Playwright i Chromium; użytkownik aplikacji nie musi
ich instalować. Testy przeprowadzono na Linux. DPAPI jest w testach jednostkowych
symulowane. Nie potwierdzono uruchomienia runtime na Windows domenowym,
polityk PowerShell ani pracy na konkretnym udziale SMB.

## Kolejne kroki wymagające środowiska docelowego

1. Sprawdzić aktualizację na kopii folderu działającej instalacji Windows,
   pod tym samym kontem: odczyt CFDB, dopisanie wpisu, restart i ponowny odczyt.
2. Na dwóch stanowiskach sprawdzić jednoczesną edycję tego samego zgłoszenia
   i zwalnianie blokady po zamknięciu formularza.
3. Sprawdzić odtworzenie kopii CFDB z kluczem odzyskiwania na stanowisku testowym.
4. Osobno zaplanować przywracanie niezapisanych formularzy po wygaśnięciu sesji
   oraz dalszy podział formularzy protokołów i konfiguracji na sekcje.

Te punkty nie są deklarowane jako wykonane. Do analizy konkretnego błędu
produkcyjnego wystarczy najpierw jego opis i komunikat; hasła logowania nie
należy przesyłać. Ewentualna baza testowa powinna mieć zanonimizowane dane.

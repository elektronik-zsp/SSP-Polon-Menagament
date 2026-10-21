# Rozwój SSP Polon — wersja 2.1

## Wdrożenie 2.0

- [x] Migracja dotychczasowych plików JSON bez utraty dodatkowych pól; brak obowiązkowego Internetu i instalacji.
- [x] Ewidencja: nowe centrale, edycja, archiwizacja bez usuwania historii, karta centrali.
- [x] Serwis: priorytet, osoba odpowiedzialna, termin, powiązanie zgłoszenia z protokołem.
- [x] Protokoły: szkic, lista kontroli, pomiary i uwagi, części, roboczogodziny, zalecenia, odbiorca.
- [x] Zatwierdzanie: unikalny numer, niezmienny dokument, migawka danych firmy i urządzenia, wydruk A4/PDF przez przeglądarkę.
- [x] Harmonogram: kalendarzowe dodawanie miesięcy i daty lokalne; tylko pozytywny przegląd aktualizuje termin; negatywny wynik wymaga dalszego serwisu.
- [x] Konfiguracja: firma, obiekt, kontakt, technicy, prefiks protokołów, domyślny interwał, wyprzedzenie przypomnień, lista kontrolna.
- [x] Ochrona danych: wersjonowanie zapisów, rotowane kopie, kopia przed importem, walidacja, rejestr zmian i obsługa błędów bez utraty formularza.
- [x] Testy API i scenariusze przeglądarkowe; paczki pełna oraz aktualizacyjna bez bazy i config.json.

## Rozszerzenie 2.1

- [x] Historia kolejnych wizyt/diagnoz/napraw w zgłoszeniu (kto, kiedy i co zrobił).
- [x] Nowe statusy, zamykanie i anulowanie z uzasadnieniem, wznowienie oraz powiązanie z protokołami.
- [x] Kontrola dopisywania wpisów, zachowanie starszych baz i testy procesu wieloetapowego.

## Granice wersji

Aplikacja lokalna, dla jednego stanowiska. Odpowiedzialny i podpisy to dane dokumentu, nie uwierzytelniona tożsamość ani podpis elektroniczny. Lista kontrolna jest szablonem roboczym do dostosowania do urządzeń i procedur obiektu; nie stanowi certyfikacji zgodności. Załączniki binarne, rozliczenia finansowe, współdzielenie sieciowe i integracja sprzętowa nie są częścią tego wydania.

## Dalsze etapy

1. Ewidencja czujek, pętli i stref oraz wyniki kontroli poszczególnych elementów.
2. Załączniki zdjęć i dokumentacji z kontrolą wielkości i kopiowaniem całego katalogu danych.
3. Magazyn części i zestawienia kosztów, po ustaleniu zasad rozliczeń.
4. Wersja wielostanowiskowa z kontami, uprawnieniami i centralną bazą — odrębna architektura wymagająca uzgodnienia z IT.

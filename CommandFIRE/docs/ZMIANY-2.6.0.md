# CommandFIRE SSP Serwis 2.6.0

## Zakres

Rozbudowa lokalnej wersji portable. Bez modułu przekazania służby.
Zachowano dotychczasowy nagłówek, sortowanie i prezentację zgłaszającego.

## Kopie i aktualizacja

- Kopie przed zmianami danych i importem są odczytywane kontrolnie po zapisie.
- Lista kopii pokazuje datę, wynik walidacji i liczbę central, spraw oraz dokumentów.
- Uszkodzona kopia jest oznaczona i zablokowana do pobrania jako poprawna kopia.
- Przed potwierdzeniem importu aplikacja weryfikuje strukturę pliku i pokazuje podsumowanie.
- Import zastępuje dane robocze; zachowuje bieżące konta i konfigurację serwisu.
- Pełne kopie JSON zawierają konta, konfigurację zapisaną w bazie i dokumenty central.
  Plik config.json ze ścieżką bazy i portem jest lokalny; zachowuje go aktualizator.
- Aktualizuj.bat wykonuje sprawdzony ZIP starych plików i bazy przed podmianą programu.
  W razie błędu kopiowania przywraca już podmienione pliki. Nie zmienia runtime ani danych.
- Kopie na tym samym dysku nadal wymagają dodatkowego przechowywania na innym nośniku.

## Zgłoszenia

- Data wystąpienia i adres elementu / pętli / strefy.
- Powiązanie z innym zgłoszeniem tej samej centrali: nawrót, duplikat, powiązane.
- Osobny etap prac: diagnoza, naprawa, oczekiwanie na części, oczekiwanie na serwis, weryfikacja.
  Etap prac, status sprawy i stan techniczny centrali są odrębnymi informacjami.
- Przy zamykaniu wpisem wymagane są przyczyna, sposób usunięcia i wynik sprawdzenia.
  Zamknięcie pozytywnym protokołem pobiera opis i wynik z protokołu.
- Ponowne otwarcie przez wpis ze statusem W realizacji zachowuje historię.
- Historia zmian danych wskazuje poprzednią i nową wartość oraz osobę zapisującą.
- Wydruk zgłoszenia z historią, także do PDF przez przeglądarkę.

## Karta centrali

- Obsługiwany obszar i kontakt do serwisu.
- Dokumenty PDF, PNG, JPG, TXT zapisane wewnątrz bazy: do 2 MB na plik,
  do 20 dokumentów centrali; cała baza do 20 MB.
- Dokumenty dodaje się i usuwa przez edycję centrali; pobiera z jej karty.
- Nie kopiujemy dokumentów binarnych do każdego zatwierdzanego protokołu.
- Wydruk karty z aktualnymi danymi, zgłoszeniami i historią.

## Przeglądy i raporty

- Z pozycji Usterka na liście kontrolnej można otworzyć formularz zgłoszenia.
  Zgłoszenie zachowuje odnośnik do protokołu źródłowego.
- Ponowne wybranie tej samej pozycji otwiera istniejącą sprawę, jeżeli jej opis pozostał niezmieniony.
- Dotychczasowy harmonogram i checklisty pozostają dostępne.
- Raport prac w zakładce Protokoły i historia korzysta z zakresu dat, wyszukania i filtra stanu.
  Dla raportu miesięcznego ustaw pierwszy i ostatni dzień miesiąca.
- Eksport CSV zgodny z polskim Excelem oraz wydruk / zapis do PDF przez przeglądarkę.

## Zgodność i weryfikacja

- Bazy ze schematami 1–4 są uzupełniane do schematu 5 bez zmiany nadanych numerów.
- Po zapisie nowej bazy starsza wersja programu jej nie obsłuży.
  Wszystkie stanowiska muszą używać 2.6.0; wycofanie wymaga kopii sprzed aktualizacji.
- Testy Python: migracja, niezmienność historii, szczegóły zmian, zamknięcie/wznowienie,
  powiązania, dokumenty, uszkodzona kopia, podgląd importu i zamknięcie protokołem.
- Testy JavaScript: generowanie widoków i formularzy, powiązania, dokumentacja,
  wyszukiwanie nazw plików, akcja zgłoszenia z checklisty i raporty.
- Test aktualizatora: kopia danych i plików programu, zachowanie konfiguracji i runtime.
- Nie wykonano pełnego testu w rzeczywistej przeglądarce ani uruchomienia Windows.
  Środowisko testowe nie udostępniło działającej przeglądarki.

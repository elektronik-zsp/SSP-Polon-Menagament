# CommandFIRE SSP Serwis 2.7.0 — plan przeglądów

## Planowanie

W menu dodano Plan przeglądów. Dla aktywnej centrali można zapisać jedną najbliższą
wizytę: datę, wykonawcę i ustalenia organizacyjne. Plan można zmienić albo odwołać.
Planowanie wymaga uprawnienia do edycji central. Odczyt planu jest dostępny wraz z podglądem central.

Termin z interwału i uzgodniona wizyta są oddzielne. Ustalenie wizyty nie przesuwa
terminu przeglądu i nie oznacza potwierdzenia sprawności urządzenia.
Widok wskazuje wizyty po terminie i wizyty ustalone po terminie z interwału.

Filtry: miesiąc, tekst wyszukania, zaplanowane, bez planu, wizyta po terminie,
przegląd po terminie. Miesiąc odnosi się do daty wizyty, a przy jej braku do terminu
z interwału. Centrale bez obu dat widać przy wyłączonym filtrze miesiąca.
Liczniki nad tabelą obejmują wszystkie aktywne centrale, niezależnie od filtrów.
Przycisk Drukuj plan / PDF drukuje aktualnie wybrane pozycje.

## Wykonanie wizyty

Wybierz Wykonaj przegląd z planu lub Nowy przegląd z karty centrali.
Formularz zapamięta identyfikator aktualnego planu i podpowie wykonawcę.
Data wykonania to rzeczywista data czynności; data wizyty nie wypełnia jej automatycznie.

Po zatwierdzeniu protokołu przeglądu odpowiadająca mu wizyta zostaje rozliczona.
Jej dane są zachowane przy zatwierdzonym protokole i w rejestrze zmian.
Po wyniku negatywnym lub warunkowym data ostatniego pozytywnego przeglądu nie zmienia się.
Wynik negatywny nadal oznacza konieczność obsługi technicznej.

Przełożenie wizyty nadaje jej nowy identyfikator. Zatwierdzenie starszego szkicu
nie usuwa nowego planu. Protokół utworzony bez powiązania z wizytą nie rozlicza jej
samoczynnie. Przed archiwizacją centrali należy odwołać jej zaplanowaną wizytę.

## Zgłoszenia

Dodano filtry: otwarte, otwarte po terminie, otwarte bez odpowiedzialnego,
etap prac, odpowiedzialny i zakres dat zgłoszenia. Filtry łączą się z wyszukaniem
oraz statusem sprawy. Liczba wyników jest widoczna przy filtrach.

## Uprawnienia

Serwisant z prawem przygotowania protokołów może teraz uzyskać blokadę centrali
potrzebną do utworzenia przeglądu. Nie otrzymuje przez to prawa do ręcznej zmiany
danych centrali. Bezpośrednie zmiany nadal wymagają uprawnienia panels.edit.

## Aktualizacja i zgodność

Zatrzymaj program i zamknij menedżer na wszystkich stanowiskach. Wypakuj paczkę
do osobnego folderu i uruchom Aktualizuj.bat. Wskaż dotychczasowy folder SSP-Polon.
Aktualizator sprawdzi kopię programu, konfiguracji i bazy przed podmianą plików.
Nie nadpisuje bazy, kont ani konfiguracji czystymi plikami.

Bazy ze schematami 1–5 są uzupełniane do schematu 6. Numery zgłoszeń i historia
pozostają zachowane. Wszystkie stanowiska muszą korzystać z wersji 2.7.0.
Powrót do poprzedniej wersji wymaga odtworzenia kopii sprzed aktualizacji.
Nie dodano przekazania służby ani połączeń z usługami internetowymi.

## Weryfikacja

15 testów Python: migracja i dane 2.6, kopie, import, dokumentacja,
zamknięcie/wznowienie zgłoszeń, planowanie, przełożenie, odwołanie,
rozliczenie wizyty, wynik negatywny, blokady i uprawnienia API.
Testy JavaScript: generowanie widoków i formularzy, filtry miesiąca i zgłoszeń,
podpowiadanie wykonawcy, raporty i regresja funkcji 2.6.
Archiwum ZIP i nienaruszony runtime sprawdzono automatycznie.
Nie wykonano pełnego uruchomienia na Windows ani wizualnego testu w przeglądarce.

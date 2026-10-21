# CommandFIRE SSP Serwis 2.11.0 — zapamiętywanie widoków

## Filtry i sortowanie

Program zapamiętuje filtry oraz sortowanie tabel w zakładkach:
Centrale i harmonogram, Plan przeglądów, Zgłoszenia serwisowe,
Protokoły i historia oraz Raporty i koszty.

Ustawienia są przypisane do konta i lokalnej ścieżki bazy w danej przeglądarce.
Nie zmieniają wspólnej bazy i nie są przenoszone na inne komputery.
Po ponownym otwarciu zakładki przywracane są poprzednie filtry i sortowanie.
Dotyczy to także frazy w filtrze tabeli. Fraza wspólnej wyszukiwarki Ctrl+K
nie jest utrwalana przez tę funkcję. Nie zapamiętujemy otwartego formularza.

Miesiąc raportu, jeżeli użytkownik go wybrał, pozostaje taki sam do zmiany
lub resetu. Przy pierwszym otwarciu raportu domyślny jest bieżący miesiąc.

## Resetuj widok

W pasku filtrów dodano kompaktowy przycisk Resetuj widok.
Czyści filtry i przywraca domyślne sortowanie tabel bieżącej zakładki.
Dla raportów reset przywraca bieżący miesiąc. Nie zmienia pozostałych zakładek,
danych użytkownika ani ustawień innych kont.

Gdy przeglądarka blokuje localStorage lub brakuje w nim miejsca, program
korzysta z pamięci bieżącej sesji. Funkcje tabel nadal działają.
Uszkodzone lub nieobsługiwane ustawienia są pomijane. Pamięć sortowania
jest ograniczona do 100 ostatnich tabel. Podpowiedź na przycisku resetu
informuje o sposobie przechowywania ustawień.

## Aktualizacja

Zatrzymaj program, wypakuj paczkę osobno i uruchom Aktualizuj.bat.
Wskaż dotychczasowy folder SSP-Polon. Aktualizator wykona kopię przed zmianą
plików i zachowa dane, konta oraz konfigurację. Schemat bazy pozostaje 8.
Wygląd kompaktowych filtrów, słownik elementów i podpowiedzi zgłoszeń zachowano.
Nie dodano modułu przekazania służby ani usług internetowych.

Archiwum przygotowano jako standardowy ZIP bez kompresji. Jest większe,
ale otwiera się zwykłym narzędziem rozpakowywania Windows.
Sprawdzono integralność i pełne rozpakowanie także po zapisaniu pliku do pobrania.

## Weryfikacja

Testy JavaScript: przywracanie filtrów i sortowania, izolacja kont i baz,
reset bieżącego widoku, błędne dane, zablokowany zapis i regresja poprzednich funkcji.
Nie wykonano pełnego uruchomienia Windows ani wizualnego testu przeglądarki.

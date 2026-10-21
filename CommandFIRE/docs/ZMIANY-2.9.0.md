# CommandFIRE SSP Serwis 2.9.0 — wyszukiwanie i nawigacja

## Szukaj w systemie

Nowa pozycja w menu zbiera wyniki z central, zgłoszeń, protokołów oraz rejestru kosztów.
Dostępna jest także skrótem Ctrl+K (na macOS Cmd+K), gdy użytkownik jest zalogowany,
ma uprawnienia do podglądu danych i nie edytuje otwartego formularza.

Wyszukiwarka obejmuje:
- centrale: kod, model, lokalizację, numer seryjny, uwagi, plan wizyty i nazwy załączników;
- zgłoszenia: numer, opis, zgłaszającego, odpowiedzialnego, adres elementu, etap prac,
  opis naprawy i historię czynności;
- protokoły: numer protokołu i przeglądu, wykonawcę, opis, zalecenia, części i checklistę;
- koszty: opis, numer dokumentu, protokół, kategorię, kwotę i autora wpisu.

Wpisz minimum dwa znaki. Wszystkie słowa muszą wystąpić w rekordzie, choć mogą być
w różnych polach. Wielkość liter i polskie znaki nie mają znaczenia.
Dokładne dopasowanie numeru lub nazwy otrzymuje pierwszeństwo, potem wyniki są
porządkowane według dopasowania i daty. Można ograniczyć wyniki do jednego rodzaju.
Pokazujemy 100 najlepiej dopasowanych wyników z licznikiem pełnej liczby trafień.
Przy większej liczbie należy zawęzić frazę albo wybrać rodzaj rekordu.

Treść załączników nie jest przeszukiwana. Nie indeksujemy danych binarnych plików,
kont, haseł ani technicznych pól sesji. Wyszukiwanie odbywa się lokalnie.

## Otwieranie wyników

Kliknięcie wyniku otwiera kartę centrali, zgłoszenie lub protokół.
Wynik kosztu prowadzi do powiązanego protokołu z rejestrem kosztów.
Przycisk Wróć do wyników wyszukiwania przywraca frazę oraz wybrany rodzaj wyników.
Zwykła nawigacja do innej zakładki kończy powrót do poprzedniego wyszukiwania.
Wylogowanie i ekran ponownego logowania czyszczą stan powrotu.

Wyniki i odnośniki respektują uprawnienia do podglądu central, zgłoszeń i protokołów.
Dostęp do kosztów jest zgodny z dotychczasowym dostępem do protokołów.

## Wygląd i zgodność

Zachowano kompaktowe filtry o wysokości 34 px z wersji 2.8.1.
Nie zmieniono schematu bazy (pozostaje 7), numeracji ani danych użytkownika.
Nie dodano przekazania służby ani usług internetowych.

Aktualizacja: zatrzymaj program, wypakuj paczkę osobno, uruchom Aktualizuj.bat
i wskaż dotychczasowy folder SSP-Polon. Powstanie kopia przed zmianą plików.
Dane, konta i konfiguracja pozostają zachowane.

## Weryfikacja

Testy JavaScript obejmują numery dokumentów, znaki diakrytyczne, historię czynności,
nazwy załączników, pomijanie danych binarnych, warunek wszystkich słów,
filtrowanie rodzaju, uprawnienia, kodowanie HTML i powrót do wyników.
Dotychczasowe testy raportów, kosztów, planów i widoków także przechodzą.
Archiwum ZIP i nienaruszony runtime sprawdzono automatycznie.
Nie wykonano pełnego uruchomienia Windows ani wizualnego testu w przeglądarce.

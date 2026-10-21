# CommandFIRE SSP Serwis 2.8.0 — raporty i koszty

## Raport miesięczny

Nowa zakładka Raporty i koszty. Domyślnie otwiera bieżący miesiąc.
Można wybrać miesiąc i centralę albo wyczyścić miesiąc, aby objąć całą historię.
Zestawienie według central zawiera zatwierdzone prace, przeglądy, wyniki negatywne,
nowe zgłoszenia, czas pracy oraz koszty części, robocizny, dojazdu i inne.

Prace liczymy według daty wykonania protokołu, zgłoszenia według daty zgłoszenia,
a koszty według daty kosztu lub korekty. Szkice nie są liczone jako wykonane prace.
Stare wpisy historyczne nie są traktowane jak zatwierdzone protokoły nowego typu;
można powiązać z nimi koszt i taki koszt pojawi się w wybranym okresie.
Wskaźnik protokołów bez wpisu kosztowego odnosi się do prac z wybranego okresu
oraz wpisów kosztowych z całej historii. Brak wpisu nie oznacza potwierdzonego 0 PLN.
Po skorygowaniu kosztu do zera historia wpisów nadal pozostaje zapisana.

## Nawroty usterek

Potwierdzone nawroty to zgłoszenia oznaczone Nawrót i połączone z poprzednią sprawą.
Raport obejmuje nowe, nieanulowane zgłoszenia tego typu z wybranego okresu.

Druga tabela wskazuje powtarzające się adresy elementów w tej samej centrali.
Porównanie pomija wielkość liter i nadmiarowe spacje, anulowane sprawy oraz duplikaty.
Grupa musi zawierać co najmniej dwa zgłoszenia w całej historii oraz co najmniej
jedno z wybranego okresu. Jest to wskazówka do sprawdzenia, nie diagnoza wspólnej przyczyny.
Kliknięcie numeru otwiera zgłoszenie. Analiza wymaga podglądu zgłoszeń.

## Rejestr kosztów

Koszt można dodać przy zatwierdzonym protokole lub wpisie historycznym,
a także przyciskiem Dodaj koszt w raportach. Szkic nie może być podstawą kosztu.
Dane: data kosztu, kategoria, kwota brutto PLN, opis i opcjonalny numer dokumentu.

Kwoty są przechowywane jako całkowita liczba groszy. Limit pojedynczego kosztu:
0,01–100 000 000 PLN. Formularz przyjmuje przecinek lub kropkę i najwyżej dwa miejsca
dziesiętne. Koszt rzeczywisty nie może mieć przyszłej daty.
Nie wyliczamy podatków ani nie prowadzimy księgowości — rejestr służy ewidencji serwisu.

Zapis kosztu nie zmienia zatwierdzonego protokołu technicznego. Historia kosztów jest
widoczna przy protokole i na karcie centrali. Wpisu nie można nadpisać ani usunąć.
Korekta odwraca całą pierwotną kwotę z podaniem powodu. Jeden koszt można odwrócić
jeden raz. Aby poprawić kwotę, wykonaj korektę, a następnie dodaj poprawny koszt.
Korekta nie może mieć daty wcześniejszej niż oryginał i jest ujmowana w swoim miesiącu.
Suma wybranego miesiąca może być ujemna, gdy korekty przewyższą nowe koszty.
Wpisy zachowują autora i czas zapisu ustalone przez aplikację.

Podgląd kosztów korzysta z uprawnienia protocols.view; dodawanie i korekty z protocols.edit.
Użytkownik bez dostępu do protokołów nie otrzymuje rejestru kosztów z API.
Operacje na rejestrze są zapisywane w rejestrze zmian.

## Wydruki i eksport

Raport miesięczny z analizą usterek i kosztami można wydrukować lub zapisać do PDF
przez przeglądarkę. CSV zestawienia obejmuje sumy według central, a CSV kosztów
wszystkie wpisy z wybranego miesiąca i centrali. W widoku historii pokazujemy
maksymalnie 200 ostatnich pozycji; wydruk i CSV obejmują cały wybrany zakres.
CSV używa średnika, przecinka dziesiętnego i UTF-8 BOM dla polskiego Excela.
Pola tekstowe przypominające formuły są zabezpieczane; kwoty ujemne pozostają liczbami.

## Kopie i aktualizacja

Koszty są częścią bazy JSON, eksportu i kopii zapasowych. Podgląd importu wskazuje
liczbę wpisów kosztowych w pliku i bieżącej bazie. Import starszej bazy bez kosztów
zastępuje rejestr pustą listą — dotychczasowa baza pozostaje w kopii przed importem.

Zatrzymaj program i zamknij menedżer na wszystkich stanowiskach. Wypakuj paczkę
do osobnego folderu, uruchom Aktualizuj.bat i wskaż dotychczasowy SSP-Polon.
Aktualizator wykona sprawdzoną kopię przed podmianą plików. Zachowuje konta i dane.
Bazy ze schematami 1–6 są uzupełniane do schematu 7 bez zmiany numerów i historii.
Zaktualizuj wszystkie stanowiska. Powrót wymaga kopii sprzed aktualizacji.

## Weryfikacja

22 testy Python: regresja 2.6/2.7, walidacja kwot i powiązań, niezmienność rejestru,
korekty, równoległe dopisywanie, ochrona przed podwójną korektą, uprawnienia i API.
Testy JavaScript: sumy miesięczne, kwoty w groszach, rozliczenie korekt w miesiącach,
analiza nawrotów, formularze, generowanie widoków i eksport CSV.
ZIP i zgodność runtime z dotychczasową paczką zweryfikowano automatycznie.
Nie wykonano pełnego uruchomienia Windows ani wizualnego testu przeglądarki.
Nie dodano modułu przekazania służby ani usług internetowych.

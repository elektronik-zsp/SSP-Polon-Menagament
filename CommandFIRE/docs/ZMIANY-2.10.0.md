# CommandFIRE SSP Serwis 2.10.0 — elementy i podobne zgłoszenia

## Słownik elementów centrali

Na karcie centrali dodano tabelę Elementy centrali. Można dodawać i edytować adres,
typ, lokalizację i uwagi. Słownik uzupełnia się stopniowo; nie trzeba wcześniej
wprowadzać całej instalacji. Pole typu ma podpowiedzi, ale dopuszcza własną nazwę.
Adres powinien uwzględniać pętlę i numer, aby jednoznacznie wskazywał element.

Adresy są unikalne w obrębie centrali, z pominięciem wielkości liter i nadmiarowych
spacji. Unikalność obejmuje także archiwum. Zamiast ponownie używać tego samego
adresu, przywróć lub popraw istniejący wpis. Nie usuwamy elementów — archiwizacja
zachowuje ich powiązania. Limit wynosi 5000 elementów centrali, z zachowaniem
limitu całej bazy 20 MB. Zmiany słownika są widoczne w rejestrze zmian.

Słownik korzysta z uprawnień do central: odczyt panels.view, zmiany panels.edit.
Zmiana słownika blokuje edycję całej centrali na czas formularza, korzystając
z dotychczasowych blokad. Archiwalna centrala nie dopuszcza zmiany słownika.

## Element w zgłoszeniu

Formularz zgłoszenia ma wybór elementu ze słownika wskazanej centrali.
Wybranie elementu uzupełnia adres i zapisuje typ oraz lokalizację.
Adres wybranego elementu jest tylko do odczytu. Nadal można wybrać wpis ręczny,
więc słownik nie jest warunkiem rejestracji usterki.

Serwer potwierdza, że wybrany element należy do centrali i jest aktywny.
Zgłoszenie zapisuje historyczne wartości adresu, typu i lokalizacji. Późniejsza
zmiana słownika ich nie nadpisuje. Dotychczasowe adresy wpisane ręcznie nie są
automatycznie przypisywane do elementów. Użytkownik może powiązać je podczas edycji.
Archiwalny element pozostaje widoczny w już powiązanej sprawie, ale nie jest
podpowiadany do nowych zgłoszeń. Zmiana centrali czyści wybór elementu i powiązanie
z inną sprawą, aby uniknąć przypadkowego przeniesienia danych.

Użytkownik bez podglądu central może nadal obsługiwać dostępne zgłoszenie,
zachowując jego zapisane powiązanie. Nie otrzymuje przez to podglądu słownika.
Dane elementów są też objęte wspólną wyszukiwarką i kopiami zapasowymi.

## Podobne zgłoszenia

Podczas wpisywania adresu lub opisu formularz pokazuje maksymalnie 5 najbardziej
zbliżonych spraw tej samej centrali. Dopasowanie bierze pod uwagę identyczny element
słownika, identyczny adres lub podobieństwo słów w opisie. Otwarte sprawy mają
pierwszeństwo. Pomijamy aktualnie edytowane zgłoszenie, anulowane sprawy i duplikaty.

Podpowiedzi nie blokują zapisu i nie oznaczają potwierdzenia wspólnej przyczyny.
Po sprawdzeniu opisu można ustawić powiązanie jako duplikat dla otwartej sprawy lub
nawrót dla zakończonej. Powiązanie zostaje zapisane dopiero przy zapisaniu formularza.
Podgląd szczegółów nie zamyka formularza. Otwieranie istniejącej sprawy wymaga
potwierdzenia odrzucenia niezapisanych zmian. Podpowiedzi wymagają faults.view.

## Aktualizacja i dane

Zatrzymaj program na wszystkich stanowiskach. Wypakuj paczkę osobno i uruchom
Aktualizuj.bat. Wskaż dotychczasowy folder SSP-Polon. Powstanie sprawdzona kopia
przed zmianą plików; konta i dotychczasowe dane pozostaną zachowane.

Bazy ze schematami 1–7 są uzupełniane do schematu 8. Historia, numery, koszty i
ręczne adresy pozostają zachowane. Zaktualizuj wszystkie stanowiska.
Powrót do wersji 2.9 lub starszej wymaga odtworzenia kopii sprzed aktualizacji.
Wygląd kompaktowych filtrów z 2.8.1 pozostaje zachowany.
Nie dodano przekazania służby ani usług internetowych.

## Weryfikacja

30 testów Python obejmuje regresję poprzednich wersji, walidację słownika,
unikalność adresów, archiwizację, niezmienność danych historycznych elementu,
powiązania między centralami oraz obsługę zgłoszenia bez uprawnień do słownika.
Testy JavaScript obejmują podobieństwo opisów, kolejność podpowiedzi, zakres centrali,
wykluczenia, uprawnienia, opcje słownika i dotychczasowe widoki, raporty oraz wyszukiwanie.
Sprawdzono ZIP i zgodność dołączonego runtime z poprzednią paczką.
Nie wykonano pełnego uruchomienia na Windows ani wizualnego testu w przeglądarce.

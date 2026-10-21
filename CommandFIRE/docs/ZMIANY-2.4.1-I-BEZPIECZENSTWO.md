# SSP Polon 2.4.1 — uruchamianie w tle i ryzyka

## Zmiany

- `Uruchom_w_tle.vbs`: uruchamia w tle lokalny serwer i otwiera przeglądarkę, bez pozostawiania okna konsoli. Plik VBS działa w standardowym Windows Script Host (jeśli nie został wyłączony przez politykę firmy).
- `Uruchom.bat`: uruchamia identyczny mechanizm, bez potrzeby obsługi VBS. Okno BAT widoczne jest tylko w czasie uruchamiania.
- `Zatrzymaj_SSP_Polon.vbs` / `.bat`: łagodnie zamyka serwer należący do bieżącej lokalnej instalacji. Jeżeli są aktywne formularze, pyta o potwierdzenie; niewysłane formularze utracą dane. Program próbuje zwolnić z bazy wspólnej swoje blokady.
- `Sprawdz_status.vbs` / `.bat`: pokazuje, czy serwer działa oraz czy może odczytać wspólną bazę.
- Drugie uruchomienie otwiera działający już serwer, bez zakładania kolejnej kopii.
- Serwer pozostaje ograniczony do `127.0.0.1` i nie jest udostępniany w sieci. Polecenie zatrzymania wymaga losowego tokenu przechowywanego w profilu danego użytkownika Windows.
- Lokalne logi i plik identyfikujący proces znajdują się w `%LOCALAPPDATA%\SSP-Polon\<identyfikator folderu>\`. Log `server.log` jest obracany po przekroczeniu 2 MB, poprzedni zapis jest w `server.previous.log`.

## Jak przejść z 2.4.0 na 2.4.1

1. Zapisz zmiany, zamknij formularze i zatrzymaj **stary** serwer otwarty w czarnym oknie `Uruchom.bat` (Ctrl+C / zamknij okno). Zrób kopię aktualnej wspólnej bazy poza jej folder.
2. Lokalnie na każdym stanowisku podmień `server.py` i `Uruchom.bat`; dodaj `tools/launcher.py`, `Uruchom_w_tle.vbs`, `Zatrzymaj_SSP_Polon.vbs`, `Sprawdz_status.vbs` i pomocnicze `.bat`. Nie ruszaj `config.json`, `runtime` i bazy.
3. Dwukrotnie kliknij `Uruchom_w_tle.vbs`. Jeśli Windows blokuje pliki VBS, użyj `Uruchom.bat`. Gdy Windows zablokuje aplikację polityką organizacji, **nie obchodź zabezpieczeń** — skonsultuj z IT.
4. Otwórz `Sprawdz_status.vbs`, sprawdź status i odczyt bazy. Otwórz zgłoszenie, wykonaj testowy wpis i zapisz. Po zapisie zamknij formularz.
5. Użyj `Zatrzymaj_SSP_Polon.vbs`, a potem ponownie uruchom i sprawdź zapisy. Przetestuj dwa stanowiska podłączone do tej samej bazy.

## Ryzyka i środki ostrożności

| Ryzyko | Co robi wersja 2.4.1 i co należy wiedzieć |
|---|---|
| Błąd w ukrytym oknie | Wyjątki trafiają do lokalnego `server.log`. Status pozwala sprawdzić dostępność; nie ma automatycznej gwarancji przywrócenia procesu po jego awarii. |
| Pozostawiony proces po zamknięciu przeglądarki | To zamierzone: sam serwer nadal działa. Należy użyć pliku Zatrzymaj albo wylogować się z Windows. |
| Utrata niezapisanej edycji | Zatrzymanie przy otwartym formularzu może utracić niewysłane dane. Program ostrzega, jeśli lokalny serwer ma otwarte blokady. Najpierw zapisz i zamknij formularz. |
| Blokada po awarii | Przy prawidłowym zamknięciu serwer usuwa własne blokady; po awarii maszyna/internet pozostaje mechanizm 30 minut bezczynności. |
| Odłączenie udziału SMB | Serwer pozostaje w tle, ale odczyt/zapis będzie zgłaszać błędy. Nie pracuj na lokalnej kopii bazy ani nie usuwaj `.mutex`; po przywróceniu połączenia odśwież. Nie ma kolejki offline. |
| Uszkodzenie/utrata bazy | Nadal używany jest pojedynczy plik JSON na zwykłym udziale SMB. Atomowe zapisy i blokady zmniejszają ryzyko, ale nie zastępują prawdziwej bazy transakcyjnej, UPS ani kopii offline. |
| Inny program zajmuje port 8765 | Aplikacja nie zabija obcych procesów i pokazuje błąd. Można zmienić port w lokalnym `config.json` (nie współdzielić go). |
| Wielu serwisantów | Lokalne procesy są niezależne, ale wspólna baza ma blokadę plikową. Wymagane są poprawne uprawnienia SMB; rzeczywiste zachowanie udziału należy przetestować. |
| Dostęp do danych | Brak kont i haseł w aplikacji. Każdy z uprawnieniami zapisu do folderu może obejść aplikację i bezpośrednio edytować JSON. Uprawnienia Windows/SMB to zasadnicza ochrona; nie otwieraj portu na LAN. |
| Token sterowania | Jedynie lokalny menedżer posiada losowy token zatrzymania procesu. Złośliwy program działający pod tym samym użytkownikiem może potencjalnie uzyskać do niego dostęp; to nie jest izolacja od zainfekowanego Windows. |
| Windows Script Host zablokowany przez IT | Wybierz pliki BAT. Nie instaluj skryptów jako usług, nie dodawaj autostartu i nie obchodź zasad korporacyjnych. |
| Logi w profilu Windows | Zapisują błędy techniczne oraz żądania HTTP i ścieżki, ale nie powinny zawierać treści zgłoszeń. Są lokalne i ograniczane wielkością; chroń profil użytkownika. |

**Ograniczenia:** brak autostartu po zalogowaniu, ikony w zasobniku, kont użytkowników, kolejkowania zmian offline i pełnej synchronizacji w czasie rzeczywistym. Zamknięcie przeglądarki nie zwalnia automatycznie procesu. Mechanizm Windows uruchamiania bez konsoli nie został sprawdzony na firmowym systemie z rzeczywistą polityką IT — wykonaj próbę na 2 stanowiskach przed wdrożeniem.

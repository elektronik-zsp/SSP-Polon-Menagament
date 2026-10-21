# SSP Polon Serwis 2.5.1 — Baza danych, prawa autorskie i licencja

## Zakres aktualizacji

1. Nagłówek pozostaje lekki: **Odśwież, identyfikacja zalogowanego konta i Wyloguj**. Przycisków eksportu i tworzenia kopii nie ma już w nagłówku.
2. Zakładka **Baza danych** zawiera: eksport bieżących danych JSON, tworzenie kopii bezpieczeństwa, import/przywracanie, listę i pobieranie kopii.
3. Zakładka **Baza danych** jest dostępna **wyłącznie dla roli ADMIN**. Po stronie serwera dotyczy to też listowania i pobierania kopii, tworzenia kopii, blokady importu oraz właściwego importu. Posiadanie starszego przypisanego uprawnienia `backups.view` lub `backups.manage` nie wystarcza dla konta niebędącego ADMIN.
4. Stopka programu i ekran logowania pokazują **© 2026 Arkadiusz Bartula**, dane firmy **ELEKTRONIK – Arkadiusz Bartula**, NIP, e-mail, telefon i link do warunków licencji.
5. **`/licencja`** to publiczna (bez logowania), statyczna strona, zawierająca ograniczoną zgodę na wewnętrzne używanie przez ZSP Synthos. Pełna treść licencji jest także w `LICENCJA-SSP-POLON.txt`.

## Co ważne w kwestii kopii

- **Eksport JSON przez stronę** to eksport danych roboczych. Nie zawiera kont użytkowników ani skrótów ich haseł. Nie powinien być uznawany za pełną kopię awaryjną z kontami.
- **Kopie wykonywane przez serwer** obejmują cały plik JSON, włącznie z kontami i zapisami haseł. Należy chronić te pliki uprawnieniami Windows i przechowywać ich kopie poza udziałem sieciowym.
- **Import danych** zastępuje ewidencję central, zgłoszeń i protokołów, ale zachowuje istniejące konta administratora i użytkowników. Występuje globalna blokada importu, ważna także przy wielu stanowiskach.
- **Uprawnienia aplikacji nie zastąpią ACL udziału SMB:** użytkownik z bezpośrednim dostępem do całego pliku JSON może ominąć logowanie aplikacji.

## Aktualizacja ze stanu 2.5.0

1. Na wszystkich stanowiskach zapisz pracę, zatrzymaj program i menedżera; zrób kopię pliku bazy na odrębny nośnik/lokalizację.
2. Skopiuj do lokalnego folderu `SSP-Polon` pliki: `server.py`, `auth_users.py`, `app.js`, `index.html`, `style.css`, `licencja.html`, `LICENCJA-SSP-POLON.txt`, `README.md` i ten dokument.
3. **Nie nadpisuj** `runtime`, `config.json` ani `db_polon_ssp.json`. Wersja 2.5.1 nie wymaga zmiany schematu bazy.
4. Uruchom program normalnie przez `SSP_Polon_Manager.vbs` i odśwież stronę `Ctrl+F5`.
5. Sprawdź na koncie ADMIN: zakładka Baza danych zawiera eksport/kopie/import, działa strona `/licencja`, a w nagłówku nie ma operacji na bazie.
6. Sprawdź na koncie SERWISANT: brak zakładki Baza danych; operacje przez API muszą zwracać 403.

## Właściciel i warunki licencji

**Autor / podmiot wskazany przez wydawcę:** Arkadiusz Bartula, ELEKTRONIK – Arkadiusz Bartula, NIP 549-226-34-51, akradiusz.bartula@gmail.com, +48 531 531 622.

Licencja ma charakter niewyłącznego, nieodpłatnego upoważnienia dla wewnętrznej pracy ZSP Synthos. Nie przenosi autorskich praw majątkowych. Zastrzeżenie praw dotyczy autorskich elementów programu, z zastrzeżeniem praw osób trzecich i praw mogących wynikać ze stosunku pracy lub umów. Treść należy zweryfikować prawnie, szczególnie jeśli program jest tworzony w ramach obowiązków pracowniczych.

**Uwaga dotycząca kontaktu:** adres `akradiusz.bartula@gmail.com` zapisano dokładnie według danych podanych przez autora; nie korygowano jego pisowni.

## Testy

Kontrole automatyczne w Pythonie: uwierzytelnianie, funkcje menedżera, ikony oraz uprawnienia ADMIN do bazy i statyczna strona licencji. Automatyczny test przeglądarki Playwright/Chromium może być blokowany przez politykę lokalnego środowiska; wówczas przetestuj UI na Windows.

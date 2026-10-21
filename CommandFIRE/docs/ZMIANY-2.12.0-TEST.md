# CommandFIRE 2.12.0 TEST — wersja deweloperska

**NIE INSTALOWAĆ NA PRODUKCJI.** Kod zawiera prototyp szyfrowania AES-256-GCM i DPAPI; nie jest to sprawdzona paczka Windows portable. Wymaga biblioteki `cryptography` w środowisku Python 3.13 x64. Nie jest dołączona (brak dostępu do pobrania zgodnego koła Windows).

1. Zamknij program na wszystkich komputerach i wykonaj kopię JSON poza udziałem.
2. Na testowym Windows z Pythonem 3.13 i `cryptography` uruchom `tools/cfdb_setup.py` (opcja 1). Zapisz klucz odzyskiwania poza komputerem i udziałem SMB.
3. Zmień lokalne `config.json` na ścieżkę `.cfdb`. Nie uruchamiaj starej wersji przeciw CFDB.
4. Na kolejnych stanowiskach uruchom opcję 2 i wprowadź klucz odzyskiwania; DPAPI jest związane z użytkownikiem Windows.
5. Sprawdź logowanie, edycję, backup, import, konflikt i przerwanie sieci. Nie testowano Windows/SMB w tym środowisku.

UWAGA: nie wszystkie zewnętrzne narzędzia i scenariusze importu zostały dostosowane do CFDB. Nie używaj konfiguratora wspólnej bazy z 2.11.1 do plików CFDB. Dostęp do klucza przez proces użytkownika nie daje ochrony przed administratorem komputera. Stare jawne kopie JSON należy zabezpieczyć oddzielnie. Przy utracie klucza odzyskiwania i DPAPI odszyfrowanie będzie niemożliwe.

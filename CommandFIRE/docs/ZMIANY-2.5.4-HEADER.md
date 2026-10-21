# CommandFIRE SSP Serwis 2.5.4 — nowy nagłówek

- Nowoczesny ciemny nagłówek z własnym logo i wyraźnym tytułem aplikacji.
- Kontrolka stanu połączenia ze wspólną bazą: Sprawdzanie…, Połączenie OK, Brak połączenia oraz Zmiany oczekują.
- Automatyczna synchronizacja nadal działa co 5 sekund, ale częstotliwość nie jest wyświetlana w nagłówku.
- Karta zalogowanego użytkownika pokazuje nazwę, rolę i inicjały; administrator jest wizualnie wyróżniony.
- Lepszy kontrast powiadomień i przycisku wylogowania; responsywny układ na węższych ekranach.
- Przeniesiono okienko powiadomień pod przycisk, aby nie zasłaniało niepowiązanych elementów.

Zmieniono `app.js`, `index.html`, `style.css` oraz numer wersji w `server.py` (bez zmiany jego działania). Nie zmieniono formatu bazy ani API.

## Instalacja

1. Zamknij stronę programu na stanowisku. Zatrzymaj lokalny serwer w menedżerze.
2. Podmień cztery pliki `app.js`, `index.html`, `style.css`, `server.py` w folderze `SSP-Polon`.
3. Uruchom serwer i odśwież stronę skrótem `Ctrl+F5`.

Konfiguracja, runtime, wspólna baza JSON, hasła i historia zgłoszeń pozostają bez zmian.

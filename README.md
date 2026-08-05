# Wizje Lełona

**Wizje Lełona** to narzędzie do testowania i zarządzania playlistami IPTV, które automatycznie weryfikuje dostępność kanałów, klasyfikuje ich statusy i generuje gotowe playlisty do użytku z aplikacjami takimi jak Yuki IPTV.

## Opis

Projekt pobiera listę kanałów z pliku źródłowego (M3U), testuje każdy kanał asynchronicznie (sprawdzając odpowiedź HTTP, poprawność playlisty M3U8, dostępność segmentów, czas odpowiedzi), a następnie klasyfikuje je na trzy statusy:

- **OK** – kanał działa poprawnie (HTTP 200, poprawne M3U8, dostępne segmenty, czas odpowiedzi < 1s)
- **UNKNOWN** – nie udało się jednoznacznie potwierdzić działania (timeout, blokada serwera, brak User-Agent, niejednoznaczna odpowiedź)
- **FAILED** – jednoznacznie nie działający kanał (HTTP 404, 410, uszkodzona playlista, brak segmentów)

Na podstawie testów generowane są **4 playlisty** oraz **3 raporty**.

## Struktura projektu

```
Wizje_Lełona/
├── config/
│   └── testing.yaml          # Konfiguracja testów (timeout, workers, retry, user-agent, SSL)
├── logs/
│   └── test.log              # Logi z każdego testu kanału
├── playlists/                # Wygenerowane playlisty M3U
│   ├── wizje-lelona-full.m3u         # Wszystkie kanały (341)
│   ├── wizje-lelona-stable.m3u       # Tylko status OK (69)
│   ├── wizje-lelona-testing.m3u      # OK + UNKNOWN (341)
│   └── wizje-lelona-verification.m3u # Tylko UNKNOWN (272)
├── reports/
│   ├── stable_report.md      # Raport Markdown ze statystykami
│   ├── status.json           # Pełne dane w formacie JSON
│   └── channel_report.csv    # Szczegółowy raport CSV
├── src/
│   └── iptv_manager/
│       ├── __init__.py
│       ├── channel.py        # Model kanału
│       ├── config.py         # Menedżer konfiguracji
│       ├── logger.py         # Logger testów
│       ├── playlist.py       # Odczyt/zapis M3U
│       └── tester.py         # Tester kanałów (asynchroniczny)
├── run_iptv_manager.py       # Główny skrypt uruchomieniowy
└── README.md                 # Ten plik
```

## Sposób używania

### Wymagania
- Python 3.11+
- Zależności: `aiohttp`, `pyyaml`

### Instalacja zależności
```bash
pip install aiohttp pyyaml
```

### Uruchomienie
```bash
cd /home/mx/Dokumenty/Projekty/Wizje_Lełona
python3 run_iptv_manager.py
```

Skrypt:
1. Wczyta plik źródłowy `/home/mx/polska-iptv-rozszerzona.m3u`
2. Przetestuje wszystkie kanały równolegle (domyślnie 10 workerów)
3. Wygeneruje 4 playlisty w katalogu `playlists/`
4. Wygeneruje 3 raporty w katalogu `reports/`
5. Zapisz logi testów w `logs/test.log`

### Konfiguracja (`config/testing.yaml`)
```yaml
timeout: 10                 # Timeout połączenia w sekundach
parallel_workers: 10        # Liczba równoległych testów
retry_count: 3              # Liczba ponownych prób
user_agent: "..."           # User-Agent do requestów
verify_segments: true       # Weryfikuj segmenty w M3U8
verify_ssl: true            # Weryfikuj certyfikaty SSL
```

## Integracja z Yuki IPTV

### Import playlisty do Yuki IPTV

1. **Otwórz Yuki IPTV** na swoim urządzeniu (Android TV, telefon, tablet)
2. Przejdź do **Ustawienia** → **Playlisty** → **Dodaj playlistę**
3. Wklej **link RAW** do wybranej playlisty (patrz sekcja "Linki RAW" poniżej)
4. Zapisz i zaktualizuj listę kanałów

### Którą playlistę wybrać?

| Playlista | Cel | Liczba kanałów |
|-----------|-----|----------------|
| **wizje-lelona-stable.m3u** | Codzienne oglądanie – tylko pewnie działające kanały | 69 |
| **wizje-lelona-testing.m3u** | Testowanie – działające + te do weryfikacji | 341 |
| **wizje-lelona-verification.m3u** | Ręczna weryfikacja – tylko te, których status nie potwierdzono | 272 |
| **wizje-lelona-full.m3u** | Pełna lista wszystkich kanałów źródłowych | 341 |

> **Zalecenie:** Do codziennego użytku użyj `wizje-lelona-stable.m3u` – zawiera wyłącznie kanały ze statusem **OK** (100 punktów).

### Automatyczna aktualizacja (opcjonalnie)

Możesz skonfigurować `cron` lub `systemd-timer` do regularnego uruchamiania skryptu i generowania świeżych playlist, a następnie hostować pliki `.m3u` na swoim serwerze/NAS (np. przez Nginx, Caddy, GitHub Pages) i podawać Yuki IPTV linki RAW do plików na serwerze.

## Linki RAW (GitHub)

Po wypchnięciu zmian na GitHub (repozytorium: `mx-wsh/wizje-lelona`), linki RAW do playlist będą dostępne pod adresami:

```
https://raw.githubusercontent.com/mx-wsh/wizje-lelona/main/playlists/wizje-lelona-full.m3u
https://raw.githubusercontent.com/mx-wsh/wizje-lelona/main/playlists/wizje-lelona-stable.m3u
https://raw.githubusercontent.com/mx-wsh/wizje-lelona/main/playlists/wizje-lelona-testing.m3u
https://raw.githubusercontent.com/mx-wsh/wizje-lelona/main/playlists/wizje-lelona-verification.m3u
```

> **Uwaga:** Linki RAW zadziałają dopiero po utworzeniu repozytorium na GitHub i wypchnięciu kodu (patrz sekcja "Wysyłka na GitHub" poniżej).

## System punktowania (0–100 pkt)

Każdy kanał otrzymuje ocenę na podstawie 5 kryteriów (po 20 pkt):

| Kryterium | Punkty |
|-----------|--------|
| HTTP OK (kod 200) | 20 |
| Poprawna playlista M3U8 | 20 |
| Wykryte segmenty | 20 |
| Czas odpowiedzi < 1s | 20 (10 pkt dla < 3s) |
| Stabilność (zakładana) | 20 |

**Status na podstawie wyniku:**
- **100 pkt (wszystkie kryteria spełnione)** → `OK`
- **HTTP 404 / 410** → `FAILED`
- **Pozostałe przypadki** → `UNKNOWN`

## Raporty

### `reports/stable_report.md`
- Łączna liczba kanałów
- Liczba kanałów OK / UNKNOWN / FAILED
- Średni czas odpowiedzi
- TOP 10 kanałów (najwyższy wynik)
- BOTTOM 10 kanałów (najniższy wynik)
- Lista kanałów FAILED z powodem

### `reports/status.json`
Pełne dane w formacie JSON (wszystkie atrybuty każdego kanału).

### `reports/channel_report.csv`
Szczegółowy raport CSV do analizy w Excelu/LibreOffice Calc.

## Logi

Wszystkie testy zapisywane są do `logs/test.log` w formacie:
```
2026-08-05 19:21:35 - IPTVTester - INFO - CHANNEL: TVP Info | URL: http://... | STATUS: OK | RESPONSE_TIME: 0.45s | REASON: HTTP OK, M3U8 valid, Segments found, Fast (<1s), Stable (assumed)
```

## Bezpieczeństwo i zasady

- ❌ **Nie usuwa** pliku źródłowego (`/home/mx/polska-iptv-rozszerzona.m3u`)
- ❌ **Nie nadpisuje** oryginalnej playlisty
- ❌ **Nie usuwa** kanałów z bazy – FAILED oznacza tylko w raporcie
- ✅ Kanały `UNKNOWN` są zachowywane do ręcznej weryfikacji
- ✅ Zachowywane są loga, EPG ID, group-title

## Licencja

Projekt prywatny – do użytku własnego.

---

## Wysyłka na GitHub (instrukcja)

Repozytorium GitHub: **`mx-wsh/wizje-lelona`**

Jeśli repozytorium nie istnieje, wykonaj kroki poniżej:

```bash
cd /home/mx/Dokumenty/Projekty/Wizje_Lełona

# 1. Inicjalizacja git
git init
git branch -M main

# 2. Dodaj wszystkie pliki
git add .

# 3. Commit wersji 1.0
git commit -m "Wizje Lełona v1.0

- Zmieniono nazwę projektu z CB IPTV Manager na Wizje Lełona
- Zaktualizowano nazwy playlist (wizje-lelona-*.m3u)
- Dodano pełny README z opisem, strukturą, instrukcją Yuki IPTV, linkami RAW
- System statusów: OK / UNKNOWN / FAILED
- System punktowania 0-100 pkt
- Generowanie 4 playlist i 3 raportów
- Logowanie testów do logs/test.log
- Konfiguracja w config/testing.yaml
- Kod modułowy, PEP 8, type hints, logging, gotowy do rozbudowy"

# 4. Dodaj remote i wyślij na GitHub (wymaga zalogowania: gh auth login)
git remote add origin https://github.com/mx-wsh/wizje-lelona.git
git push -u origin main
```

Po wykonaniu `git push`:
- Repozytorium będzie publiczne: `https://github.com/mx-wsh/wizje-lelona`
- Linki RAW (z sekcji wyżej) staną się aktywne
- Yuki IPTV będzie mógł pobierać playlisty bezpośrednio z GitHub

---

**Wersja:** 1.0  
**Data wydania:** 2026-08-05  
**Autor:** Wizje Lełona Team
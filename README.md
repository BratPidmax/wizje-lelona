# 📺 Wizje Lełona

**Wizje Lełona** to narzędzie do automatycznego testowania, weryfikacji i zarządzania playlistami IPTV. Pobiera listę kanałów z pliku źródłowego (M3U), testuje każdy kanał asynchronicznie, klasyfikuje ich statusy i generuje gotowe playlisty do użytku z popularnymi aplikacjami takimi jak **Yuki IPTV**, **TiviMate** czy **VLC**.

---

## 🎯 Najważniejsze funkcje

- ✅ **Asynchroniczne testowanie** – równoległe sprawdzanie setek kanałów (domyślnie 10 workerów)
- ✅ **System statusów 3-poziomowy** – OK / UNKNOWN / FAILED
- ✅ **System punktacji 0–100 pkt** – obiektywna ocena jakości kanału
- ✅ **Generowanie 4 playlist** – full, stable, testing, verification
- ✅ **Szczegółowe raporty** – Markdown, JSON, CSV
- ✅ **Logowanie testów** – pełna historia w `logs/test.log`
- ✅ **Konfiguracja YAML** – timeout, retry, user-agent, SSL, segmenty
- ✅ **Zachowanie metadanych** – logo (tvg-logo), EPG ID (tvg-id), grupy (group-title)
- ✅ **Bezpieczeństwo** – nie usuwa pliku źródłowego, nie nadpisuje oryginałów, FAILED tylko w raporcie
- ✅ **Kod modułowy** – PEP 8, type hints, logging, gotowy do rozbudowy

---

## 📁 Struktura katalogów

```
wizje-lelona/
├── config/
│   └── testing.yaml          # Konfiguracja testów
├── logs/
│   └── test.log              # Logi z każdego testu
├── playlists/                # Wygenerowane playlisty M3U
│   ├── wizje-lelona-full.m3u         # Wszystkie kanały (341)
│   ├── wizje-lelona-stable.m3u       # Tylko status OK
│   ├── wizje-lelona-testing.m3u      # OK + UNKNOWN
│   └── wizje-lelona-verification.m3u # Tylko UNKNOWN
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
├── README.md                 # Ten plik
└── .gitignore                # Pliki ignorowane przez Git
```

---

## 📋 Opis playlist

| Playlista | Zawartość | Przeznaczenie |
|-----------|-----------|---------------|
| **wizje-lelona-full.m3u** | Wszystkie 341 kanałów źródłowych | Archiwum, kopia zapasowa |
| **wizje-lelona-stable.m3u** | Tylko kanały ze statusem **OK** (100 pkt) | **Codzienne oglądanie** ✅ |
| **wizje-lelona-testing.m3u** | Kanały **OK + UNKNOWN** | Testowanie, eksperymenty |
| **wizje-lelona-verification.m3u** | Tylko kanały **UNKNOWN** | Ręczna weryfikacja problematycznych |

> **Zalecenie:** Do codziennego użytku używaj `wizje-lelona-stable.m3u` – zawiera wyłącznie kanały z potwierdzoną działającą strumieniem (HTTP 200, poprawne M3U8, segmenty, czas < 1s).

---

## 🛠️ Sposób używania

### Wymagania
- Python 3.11+
- Zależności: `aiohttp`, `pyyaml`

### Instalacja
```bash
pip install aiohttp pyyaml
```

### Uruchomienie
```bash
cd /home/mx/Dokumenty/Projekty/wizje-lelona
python3 run_iptv_manager.py
```

Skrypt:
1. Wczyta plik źródłowy `/home/mx/polska-iptv-rozszerzona.m3u`
2. Przetestuje wszystkie kanały równolegle
3. Wygeneruje 4 playlisty w `playlists/`
4. Wygeneruje 3 raporty w `reports/`
5. Zapisz logi w `logs/test.log`

### Konfiguracja (`config/testing.yaml`)
```yaml
timeout: 10                 # Timeout połączenia (sekundy)
parallel_workers: 10        # Liczba równoległych testów
retry_count: 3              # Liczba ponownych prób
user_agent: "Mozilla/5.0..." # User-Agent do requestów
verify_segments: true       # Weryfikuj segmenty w M3U8
verify_ssl: true            # Weryfikuj certyfikaty SSL
```

---

## 📱 Integracja z aplikacjami IPTV

### Yuki IPTV (Android TV / Telefon / Tablet)

1. Otwórz **Yuki IPTV** → **Ustawienia** → **Playlisty** → **Dodaj playlistę**
2. Wklej **link RAW** do wybranej playlisty (patrz sekcja "Linki RAW")
3. Zapisz i zaktualizuj listę kanałów

**Którą playlistę wybrać?**
- 🟢 **Stable** (`wizje-lelona-stable.m3u`) – do codziennego oglądania
- 🟡 **Testing** (`wizje-lelona-testing.m3u`) – do testów
- 🔴 **Verification** (`wizje-lelona-verification.m3u`) – do ręcznej weryfikacji

### TiviMate (Android TV / Fire TV)

1. Otwórz **TiviMate** → **Ustawienia** → **Playlisty** → **Dodaj playlistę**
2. Wybierz **Z sieci (URL)** i wklej link RAW
3. Nazwij playlistę (np. "Wizje Lełona Stable") i zapisz
4. W **Ustawieniach EPG** dodaj źródło EPG (jeśli masz plik XMLTV)

### VLC Media Player (Windows / Linux / macOS / Android)

1. Otwórz **VLC** → **Media** → **Otwórz strumień sieciowy** (Ctrl+N)
2. Wklej link RAW do playlisty i kliknij **Odtwórz**
3. Aby zapisać na stałe: **Media** → **Zapisz playlistę w pliku...** → wybierz format M3U

> **Wskazówka:** W VLC możesz też otworzyć plik `.m3u` bezpośrednio z dysku lub URL.

---

## 🔄 Instrukcja aktualizacji playlist

### Opcja 1: Ręczna (lokalnie)
```bash
cd /home/mx/Dokumenty/Projekty/wizje-lelona
python3 run_iptv_manager.py
# Nowe playlisty w playlists/
# Jeśli hostujesz na serwerze – skopiuj pliki na serwer
```

### Opcja 2: Automatyczna (cron / systemd-timer)
```bash
# Codziennie o 04:00
0 4 * * * cd /home/mx/Dokumenty/Projekty/wizje-lelona && python3 run_iptv_manager.py >> logs/cron.log 2>&1
```

### Opcja 3: GitHub Actions (CI/CD)
Możesz dodać workflow, który uruchamia skrypt codziennie i commituje zaktualizowane playlisty do repozytorium – wtedy linki RAW zawsze wskazują na najnowszą wersję.

---

## 📊 System statusów

| Status | Opis | Kryteria |
|--------|------|----------|
| **OK** ✅ | Kanał działa poprawnie | HTTP 200 + poprawne M3U8 + segmenty + czas < 1s |
| **UNKNOWN** ⚠️ | Nie udało się potwierdzić działania | Timeout, blokada serwera, brak User-Agent, niejednoznaczna odpowiedź |
| **FAILED** ❌ | Jedenazncznie nie działający | HTTP 404, 410, uszkodzona playlista, brak segmentów |

> **Ważne:** Kanały **UNKNOWN** NIE są usuwane – trafiają do `verification.m3u` do ręcznej weryfikacji. Kanały **FAILED** oznaczane są tylko w raportach.

---

## 🏆 System punktacji (0–100 pkt)

Każdy kanał otrzymuje ocenę na podstawie 5 kryteriów (po 20 pkt):

| Kryterium | Punkty | Uwagi |
|-----------|--------|-------|
| HTTP OK (kod 200) | 20 | Podstawa działania |
| Poprawna playlista M3U8 | 20 | Wykryto `application/vnd.apple.mpegurl` lub `.m3u8` |
| Wykryte segmenty | 20 | Segmenty TS w playliście lub dane w strumieniu |
| Czas odpowiedzi | 20 / 10 | < 1s = 20 pkt, < 3s = 10 pkt, ≥ 3s = 0 pkt |
| Stabilność | 20 | Zakładana (single test) – w przyszłości wielokrotne testy |

**Próg statusu:**
- **100 pkt (wszystkie kryteria)** → `OK`
- **HTTP 404 / 410** → `FAILED`
- **Pozostałe** → `UNKNOWN`

---

## 🗺️ Roadmap projektu

### v1.1 – Udoskonalenie jakości
- [ ] Wielokrotne testy kanału (np. 3x w ciągu godziny) dla lepszej oceny stabilności
- [ ] Konfigurowalne wagi punktacji
- [ ] Filtrowanie po kategoriach (sport, news, filmy, dzieci)

### v1.2 – Automatyzacja i CI/CD
- [ ] GitHub Actions: codzienne generowanie playlist i commit
- [ ] GitHub Pages: hosting playlist bez własnego serwera
- [ ] Webhook / powiadomienia o zmianach statusów

### v1.3 – Rozszerzone funkcje
- [ ] Import/eksport listy kanałów z pliku CSV/JSON
- [ ] Interfejs CLI z podkomendami (`test`, `generate`, `report`)
- [ ] Obsługa EPG (XMLTV) – pobieranie i łączenie z kanałami
- [ ] Dashboard webowy (FastAPI + HTMX) do przeglądania statusów

### v2.0 – Architektura rozproszona
- [ ] Rozdzielenie testera i generatora (mikroserwisy)
- [ ] Baza danych (SQLite/PostgreSQL) z historią testów
- [ ] API REST do integracji z zewnętrznymi systemami
- [ ] Wsparcie dla IPv6, HLS AES-128, DRM

---

## 📄 Raporty

### `reports/stable_report.md`
- Łączna liczba kanałów
- Liczba OK / UNKNOWN / FAILED
- Średni czas odpowiedzi
- TOP 10 / BOTTOM 10 kanałów
- Lista FAILED z powodem

### `reports/status.json`
Pełne dane w JSON (wszystkie atrybuty każdego kanału) – do integracji.

### `reports/channel_report.csv`
Szczegółowy CSV do analizy w Excel / LibreOffice Calc.

### `logs/test.log`
Logi w formacie:
```
2026-08-05 19:21:35 - IPTVTester - INFO - CHANNEL: TVP Info | URL: http://... | STATUS: OK | RESPONSE_TIME: 0.45s | REASON: HTTP OK, M3U8 valid, Segments found, Fast (<1s), Stable (assumed)
```

---

## 🔗 Linki RAW (GitHub)

Po opublikowaniu repozytorium `BratPidmax/wizje-lelona`, playlisty będą dostępne pod adresami:

```
https://raw.githubusercontent.com/BratPidmax/wizje-lelona/main/playlists/wizje-lelona-full.m3u
https://raw.githubusercontent.com/BratPidmax/wizje-lelona/main/playlists/wizje-lelona-stable.m3u
https://raw.githubusercontent.com/BratPidmax/wizje-lelona/main/playlists/wizje-lelona-testing.m3u
https://raw.githubusercontent.com/BratPidmax/wizje-lelona/main/playlists/wizje-lelona-verification.m3u
```

> Skopiuj wybrany link i wklej go w Yuki IPTV / TiviMate / VLC.

---

## 👤 Autor projektu

**Wizje Lełona** – projekt prywatny do użytku własnego i społeczności IPTV.

- GitHub: [@BratPidmax](https://github.com/BratPidmax)
- Repozytorium: [BratPidmax/wizje-lelona](https://github.com/BratPidmax/wizje-lelona)

---

## 📜 Licencja

Projekt prywatny – do użytku własnego. Kod źródłowy udostępniony bez gwarancji.

---

**Wersja:** 1.0 Stable  
**Data wydania:** 2026-08-05  
**Katalog projektu:** `wizje-lelona`  
**Repozytorium:** `BratPidmax/wizje-lelona`
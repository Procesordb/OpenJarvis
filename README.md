<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/AGI-PROCESOR_Horizontal_Logo_dark.png">
    <img alt="AGI PROCESOR — Inteligencja AGI" src="assets/AGI-PROCESOR_Horizontal_Logo.png" width="440">
  </picture>

  <p><i>Inteligencja AGI na Twoim komputerze: agenci, pamięć i modele, które działają lokalnie.</i></p>
</div>

---

**AGI PROCESOR — Inteligencja AGI** to lokalny silnik inteligencji AGI PROCESOR. Uruchamia modele językowe na Twoim sprzęcie, prowadzi agentów z narzędziami i pamięcią, liczy koszt i zużycie energii, a do chmury sięga tylko wtedy, gdy naprawdę trzeba. Powstał na bazie otwartego frameworku OpenJarvis ze Stanfordu (licencja Apache 2.0) — szczegóły w sekcji [Pochodzenie i licencja](#pochodzenie-i-licencja).

## Zasady

- **Analizuje i proponuje, nie działa za Ciebie w systemie.** Inteligencja AGI nie zmienia ustawień antywirusa ani zabezpieczeń, nie usuwa plików i nie uruchamia poleceń administratora. Preset `inteligencja-agi` włącza tylko narzędzia do szukania i myślenia.
- **Nic nie wychodzi bez decyzji właściciela.** Analityka nie ma domyślnego adresu, więc aplikacja nie wysyła statystyk i nie pyta o zgodę na coś, czego nie ma. Ranking oszczędności i automatyczne aktualizacje działają dopiero po skonfigurowaniu własnych usług.
- **Zero zmyślonych danych.** Gdy czegoś brakuje, AGI mówi o tym wprost.
- **Ochrona Windows jest osobno.** Własny silnik antywirusowy OCHRONA AGI to oddzielny projekt z wyższymi uprawnieniami; Inteligencja AGI może go najwyżej analizować i doradzać.

## Stan funkcji

| Funkcja | Stan |
| --- | --- |
| Czat z modelem lokalnym (Ollama, vLLM, SGLang, MLX i inne) | DZIAŁA |
| Agenci z narzędziami, pamięć, umiejętności (skills), harmonogram | DZIAŁA |
| Interfejs w przeglądarce (`agi gui`) | DZIAŁA |
| Preset `inteligencja-agi` — tylko analiza i propozycje | DZIAŁA |
| Aplikacja desktopowa (Tauri) | PROTOTYP — kod gotowy, instalatory AGI PROCESOR nie są jeszcze zbudowane |
| Automatyczne aktualizacje aplikacji desktopowej | WYŁĄCZONE — wymagają własnego klucza podpisu |
| Analityka i ranking oszczędności | WYŁĄCZONE — brak usług AGI PROCESOR |
| Połączenie z OCHRONA AGI (wyjaśnianie alertów, propozycje kroków) | PLANOWANE |

## Instalacja z kodu źródłowego

Wymagania: Python 3.11–3.13, [uv](https://docs.astral.sh/uv/) i [Ollama](https://ollama.com/) z jednym modelem (np. `ollama pull qwen3.5:4b`). Interfejs w przeglądarce potrzebuje jeszcze Node.js 22.22+ z npm 11.19+.

```bash
git clone https://github.com/Procesordb/OpenJarvis.git agi-procesor
cd agi-procesor
uv sync
uv run agi            # rozmowa w terminalu
uv run agi gui        # interfejs w przeglądarce
uv run agi doctor     # stan instalacji
```

Instalator jednym poleceniem (`install.sh` i `install.ps1`) pobiera kod z tego repozytorium; zadziała pod adresem `https://procesordb.github.io/OpenJarvis/install.sh`, gdy dokumentacja zostanie opublikowana na GitHub Pages.

## Szybki start

```bash
uv run agi init --preset inteligencja-agi --force   # analiza i propozycje, bez zmian w systemie
uv run agi ask "Wyjaśnij to ostrzeżenie Windows Defender: <wklej treść>"
```

Model domyślny presetu to `qwen3.5:9b` (`ollama pull qwen3.5:9b`); inny ustawisz w `~/.agi-procesor/config.toml`, w sekcji `[intelligence]`.

Pozostałe presety `--preset` pochodzą z OpenJarvis: `chat-simple`, `deep-research`, `morning-digest-mac`, `morning-digest-linux`, `morning-digest-minimal`, `scheduled-monitor` i `code-assistant`. `code-assistant` daje agentowi dostęp do powłoki i plików, a przykładowa konfiguracja `configs/agi_procesor/examples/full-system-access.toml` — pełny dostęp do systemu. Nie używaj ich obok OCHRONA AGI.

Dokumentacja techniczna (po angielsku) jest w folderze [`docs/`](docs/).

## Co zmieniło się względem OpenJarvis

| Było | Jest |
| --- | --- |
| OpenJarvis, Jarvis | AGI PROCESOR |
| polecenie `jarvis` | `agi` |
| pakiet Pythona `openjarvis` | `agi_procesor` (dystrybucja `agi-procesor`) |
| folder danych `~/.openjarvis` | `~/.agi-procesor` |
| zmienne `OPENJARVIS_*` i `JARVIS_*` | `AGI_PROCESOR_*` i `AGI_*` |
| klasy `Jarvis`, `JarvisConfig`, `OpenJarvisError` | `AgiProcesor`, `AgiConfig`, `AgiProcesorError` |
| crate'y Rust `openjarvis-*` | `agi-procesor-*` |
| aplikacja `com.openjarvis.desktop` | `com.agiprocesor.desktop` |

Poza nazwami:

- analityka (PostHog) nie ma domyślnego adresu, także w instalatorze `install.sh` — w OpenJarvis dane po zgodzie trafiały do serwera zespołu OpenJarvis; własną usługę ustawisz w `[analytics]` w `config.toml` albo zmiennymi `AGI_PROCESOR_ANALYTICS_HOST` i `AGI_PROCESOR_ANALYTICS_KEY`;
- ranking oszczędności nie ma domyślnej usługi (ani w aplikacji, ani na stronie dokumentacji), a konkurs OpenJarvis z nagrodą zniknął z aplikacji i dokumentacji;
- z dokumentacji zniknęła sekcja Showcase — to historie użytkowników OpenJarvis, nie AGI PROCESOR;
- aplikacja desktopowa nie pobiera aktualizacji z wydań OpenJarvis;
- sprawdzanie nowej wersji w PyPI jest wyłączone — nazwa pakietu nie jest tam zarejestrowana, więc ktoś obcy mógłby ją zająć;
- wygląd: kula AGI PROCESOR jako logo i ikony, kolory granat, chłodny błękit i złoto, czcionki Unbounded, Manrope i JetBrains Mono;
- nowy preset `inteligencja-agi`;
- testy `tests/branding` pilnują, żeby stara nazwa i stare usługi nie wróciły.

## Aktualizacje z OpenJarvis

Zmianę nazwy robi skrypt [`scripts/rebrand/agi_procesor_rebrand.py`](scripts/rebrand/README.md), więc nowe wersje OpenJarvis da się wciągać dalej — instrukcja jest w [`scripts/rebrand/README.md`](scripts/rebrand/README.md).

## Pochodzenie i licencja

AGI PROCESOR — Inteligencja AGI to zmodyfikowana wersja projektu [OpenJarvis](https://github.com/open-jarvis/OpenJarvis) (The OpenJarvis Authors; Hazy Research i Scaling Intelligence Lab, Stanford SAIL), udostępnionego na licencji Apache 2.0. Licencja: [LICENSE](LICENSE). Opis zmian: [NOTICE](NOTICE). Historia zmian projektu źródłowego: [CHANGELOG.md](CHANGELOG.md).

Prace badawcze oparte na frameworku cytują artykuł OpenJarvis:

```bibtex
@misc{saadfalcon2026openjarvispersonalaipersonal,
      title={OpenJarvis: Personal AI, On Personal Devices},
      author={Jon Saad-Falcon and Avanika Narayan and Robby Manihani and Tanvir Bhathal and Herumb Shandilya and Hakki Orhun Akengin and Gabriel Bo and Andrew Park and Matthew Hart and Caia Costello and Chuan Li and Christopher Ré and Azalia Mirhoseini},
      year={2026},
      eprint={2605.17172},
      archivePrefix={arXiv},
      primaryClass={cs.LG},
      url={https://arxiv.org/abs/2605.17172},
}
```

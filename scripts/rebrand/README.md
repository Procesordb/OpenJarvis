# Zmiana nazwy OpenJarvis → AGI PROCESOR

`agi_procesor_rebrand.py` zamienia drzewo OpenJarvis w AGI PROCESOR: zmienia nazwy plików i folderów (przez `git mv`) i przepisuje tekst według stałych reguł. Jest deterministyczny i idempotentny — drugie uruchomienie na przemianowanym drzewie niczego nie zmienia.

| Było | Jest |
| --- | --- |
| nazwa w tekście (`OpenJarvis`, `Jarvis`) | `AGI PROCESOR` |
| nazwa techniczna (ścieżki, User-Agent, pliki instalatorów) | `AGI-PROCESOR` |
| pakiet Pythona `openjarvis` | `agi_procesor` |
| nazwy z myślnikiem (`openjarvis-core`) | `agi-procesor-core` |
| folder danych `~/.openjarvis` | `~/.agi-procesor` |
| `OPENJARVIS_*`, `JARVIS_*` | `AGI_PROCESOR_*`, `AGI_*` |
| polecenie `jarvis` | `agi` |
| `JarvisConfig`, `OpenJarvisError`, klasa SDK `Jarvis` | `AgiConfig`, `AgiProcesorError`, `AgiProcesor` |
| `github.com/open-jarvis/OpenJarvis` | `github.com/Procesordb/OpenJarvis` |

Bez zmian zostają: `LICENSE` (wymóg licencji Apache 2.0), `NOTICE`, `CHANGELOG.md` (historia projektu źródłowego), cytowania artykułu OpenJarvis i ten folder. Pliki Pythona są czytane tokenizerem, więc identyfikatory i teksty dostają osobne reguły.

## Wciąganie nowych wersji OpenJarvis

```bash
git remote add upstream https://github.com/open-jarvis/OpenJarvis.git   # raz
git fetch upstream
cp scripts/rebrand/agi_procesor_rebrand.py /tmp/   # skrypt jest tylko w gałęzi AGI PROCESOR
git checkout -b sync-upstream upstream/main
python3 /tmp/agi_procesor_rebrand.py .
uv lock
uv run ruff format src/ tests/
uv run ruff check --select I001 --fix src/ tests/
git add -A
git commit -m "Rebrand upstream OpenJarvis as AGI PROCESOR"
git checkout agi-procesor
git merge sync-upstream
```

Obie gałęzie mają po zmianie nazwy te same nazwy plików i ten sam tekst, więc konflikty pojawią się tylko w liniach, które OpenJarvis zmienił w miejscach dopasowanych przez AGI PROCESOR (analityka, aktualizacje, wygląd, README, dokumentacja) albo w liniach ze starą nazwą. Na koniec uruchom testy, w tym `tests/branding`: wskażą każdą nową wzmiankę o starej nazwie, usłudze projektu źródłowego albo jego konkursie.

```bash
uv run pytest tests/ -m "not live and not cloud and not hub"
```

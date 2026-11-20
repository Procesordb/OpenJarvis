<!-- Created by the AGI PROCESOR project in 2026. -->

# AGI PROCESOR Alerts na VPS procesor.com

Ten wariant uruchamia AGI PROCESOR 24/7 na osobnym subdomenowym adresie
`alerts.procesor.com`, bez zastępowania istniejącej strony głównej. Serwer API
jest dostępny wyłącznie na loopback VPS, a publiczny ruch przechodzi przez
nginx, HTTPS i logowanie HTTP Basic.

## Stan zastany — 20 listopada 2026

- `procesor.com` i `www.procesor.com` wskazują na `69.62.120.236`;
- `https://procesor.com/` odpowiada `200` przez nginx i aplikację Next.js;
- publiczne `/health` strony głównej odpowiada `404`;
- certyfikat HTTPS strony `www.procesor.com` nie pasuje do tej nazwy;
- `alerts.procesor.com`, `api.procesor.com` i `app.procesor.com` nie mają
  rekordu A.

Nie nadpisuj obecnej konfiguracji domeny głównej. Dodaj osobny rekord A:

```text
alerts.procesor.com  A  69.62.120.236
```

Jeżeli IP VPS się zmieniło, użyj nowego adresu zamiast wartości z audytu.
Do audytu użyto wyłącznie publicznego DNS i HTTPS; nie wykonywano logowania do
Hostinger ani do VPS.

## Granica produktu

Wdrożenie zapewnia stałą dostępność, historię reguł i transport powiadomień.
Nie daje systemowi prawa do logowania się do Fomo, scrapingu ani wykonywania
transakcji. Harmonogram pozostaje wyłączony, dopóki nie zostanie podłączone
świeże, publiczne lub osobno autoryzowane źródło danych rynkowych.
Sam bundle utrzymuje API 24/7, ale nie pobiera samodzielnie notowań i nie
uruchamia cyklicznej oceny rynku. Flaga
`AGI_PROCESOR_ALERTS_SCHEDULER_ENABLED` jedynie odblokowuje endpoint kolejki;
nie tworzy crona ani źródła danych.

Domyślnie snapshot starszy niż 15 minut albo przesunięty o więcej niż minutę
w przyszłość jest odrzucany. Wysyłka używa krótkiej dzierżawy, maksymalnie
trzech prób na kanał i backoffu, aby dwa procesy nie wysłały tej samej
wiadomości jednocześnie. Wartości można stroić przez zmienne opisane w
`.env.example`, ale nie wyłączaj kontroli świeżości dla danych rynkowych.

Wiadomość może opisywać warunek obserwacji, ryzyko oraz unieważnienie
scenariusza. Nie powinna twierdzić, że zakup lub sprzedaż zapewni zysk.

## Instalacja VPS

Wymagany jest Ubuntu/Debian z Docker Engine, Docker Compose v2, nginx,
Certbotem, Git i `curl`. Operacje wykonuj z konta posiadającego `sudo`; nie
loguj się jako root przez SSH.

```bash
sudo apt-get update
sudo apt-get install -y git curl
sudo systemctl enable --now docker
sudo install -d -m 0750 -o "$USER" -g "$USER" /srv/agi-procesor
git clone --branch agi-procesor-mvp \
  https://github.com/Procesordb/OpenJarvis.git \
  /srv/agi-procesor/source
cd /srv/agi-procesor/source/deploy/vps-procesor
cp .env.example .env
chmod 0600 .env
```

Wygeneruj API key lokalnie na VPS i wstaw go do `.env`:

```bash
openssl rand -hex 32
```

Uzupełnij tylko kanały, których chcesz użyć. Nigdy nie wklejaj hasła VPS,
klucza SSH, seed phrase ani klucza prywatnego portfela do `.env`.

Sprawdź i uruchom Compose:

```bash
./scripts/validate.sh .env && \
  docker compose --env-file .env -f compose.yml build && \
  docker compose --env-file .env -f compose.yml up -d
docker compose --env-file .env -f compose.yml ps
./scripts/healthcheck.sh
```

Pierwszy start może potrwać, ponieważ obraz buduje frontend i moduł Rust, a
Ollama musi zostać uruchomiona. Kontrola `/health` sprawdza dostępność API
Ollama (`/api/tags`) i nie wymaga pobranego modelu. Model językowy jest jednak
potrzebny do rozmowy; pobierz go świadomie dopiero po sprawdzeniu wolnego
miejsca i pamięci VPS. Endpointy oceny ryzyka i alertów nie mogą udawać, że
mają aktualne dane tylko dlatego, że serwer oraz Ollama są zdrowe.
Polityka `unless-stopped` wraz z włączoną usługą Docker przywraca kontenery po
restarcie VPS; ręczne `docker compose stop` pozostaje świadomym wyłączeniem.

## nginx i logowanie

Zainstaluj narzędzia i utwórz hasło do panelu. Użyj innego hasła niż poczta,
VPS i GitHub:

```bash
sudo apt-get update
sudo apt-get install -y nginx apache2-utils certbot python3-certbot-nginx
sudo systemctl enable --now nginx
if sudo test -f /etc/nginx/.htpasswd-agi-procesor; then
  sudo htpasswd /etc/nginx/.htpasswd-agi-procesor agiprocesor
else
  sudo htpasswd -c /etc/nginx/.htpasswd-agi-procesor agiprocesor
fi
sudo chown root:www-data /etc/nginx/.htpasswd-agi-procesor
sudo chmod 0640 /etc/nginx/.htpasswd-agi-procesor
```

Utwórz root-owned snippet z tym samym `OPENJARVIS_API_KEY`, który znajduje się
w `.env`. Ten sekret zostaje na VPS i nginx dodaje go po stronie serwera — nie
jest osadzany w kodzie przeglądarki.

```nginx
proxy_set_header Authorization "Bearer REPLACE_WITH_OPENJARVIS_API_KEY";
```

Zapisz powyższą linię jako
`/etc/nginx/snippets/agi-procesor-api-key.conf`, ustaw właściciela `root:root`
i tryb `0600`. Następnie:

```bash
sudo install -m 0644 nginx/alerts.procesor.com.conf \
  /etc/nginx/sites-available/agi-procesor-alerts
test -L /etc/nginx/sites-enabled/agi-procesor-alerts || \
  sudo ln -s /etc/nginx/sites-available/agi-procesor-alerts \
    /etc/nginx/sites-enabled/agi-procesor-alerts
test "$(readlink -f /etc/nginx/sites-enabled/agi-procesor-alerts)" = \
  /etc/nginx/sites-available/agi-procesor-alerts
sudo nginx -t && sudo systemctl reload nginx
```

Polecenia można powtórzyć przed uruchomieniem Certbota. Po tym, jak Certbot
doda sekcję TLS do aktywnego vhosta, najpierw porównaj pliki (`sudo diff -u`),
aby nie usunąć ustawień certyfikatu. Plik nie modyfikuje vhosta
`procesor.com`. Jeżeli zmienisz `AGI_PROCESOR_HOST_PORT`, zmień również port
upstreamu w konfiguracji nginx.

HTTP Basic nie szyfruje hasła. Nie loguj się do panelu przez publiczne HTTP;
poczekaj na poprawny certyfikat i przekierowanie do HTTPS.
W zaporze pozostaw publicznie tylko właściwy port SSH oraz 80/443; port 8088
jest celowo zbindowany wyłącznie do `127.0.0.1`. Przed zmianą reguł zapory
sprawdź niestandardowy port SSH, aby nie odciąć sobie dostępu.

## TLS

Po propagacji rekordu DNS i poprawnym `nginx -t`:

```bash
sudo certbot --nginx -d alerts.procesor.com --redirect
sudo certbot renew --dry-run
```

Nie omijaj ostrzeżeń certyfikatu. Osobno napraw certyfikat `www.procesor.com`,
jeżeli ta nazwa ma pozostać publiczna. HSTS włącz dopiero po stabilnym teście
HTTPS i odnowienia, ponieważ przeglądarki zapamiętują tę politykę.

## Kanały wiadomości

- **E-mail:** może działać bez dodatkowej opłaty z istniejącą skrzynką domeny,
  z uwzględnieniem limitów dostawcy SMTP.
- **Telegram:** bezpłatny transport po świadomym utworzeniu bota i rozpoczęciu
  czatu przez odbiorcę.
- **ntfy:** ustaw pełny adres HTTPS prywatnego topicu; publiczny topic nie
  powinien zawierać danych prywatnych. Preferowany jest prywatny lub
  samodzielnie hostowany serwer.
- **SMS:** operatorzy i bramki HTTP zazwyczaj pobierają opłaty. Opcję włączaj
  dopiero po poznaniu ceny, limitów i numeru nadawcy. E-mail-to-SMS zależy od
  operatora i nie jest gwarantowany jako bezpłatny. Komunikat ma domyślny
  budżet 300 znaków; większy limit wymaga jawnego włączenia multipart i może
  zostać rozliczony jako kilka segmentów.

Stan kosztów sprawdzony 20 listopada 2026:

- [Telegram Bot API](https://core.telegram.org/bots/faq) pozwala botom wysyłać
  wiadomości bez opłat w standardowych limitach; płatne broadcasty dotyczą
  dopiero ruchu ponad bezpłatny limit około 30 wiadomości na sekundę.
- [ntfy](https://docs.ntfy.sh/faq/) ma bezpłatną usługę best-effort, a serwer
  jest open source i można go utrzymywać samodzielnie. Dla poufnych alertów
  wybierz prywatny topic lub własną instancję.
- [Hostinger SMTP](https://www.hostinger.com/support/1575756-how-to-get-email-account-configuration-details-for-hostinger-email/)
  obsługuje port 465/SSL albo 587/STARTTLS. Faktyczny limit wiadomości zależy
  od planu skrzynki i trzeba go sprawdzić w hPanel.
- Klasyczny SMS nie jest kanałem bezpłatnym. Przykładowo
  [Twilio dla Polski](https://www.twilio.com/en-us/sms/pricing/pl) podawało
  0,0457 USD za wychodzący segment SMS, przed ewentualnymi dodatkowymi
  opłatami. Cena może się zmienić, dlatego SMS pozostaje domyślnie wyłączony.

Wyślij najpierw wiadomość testową/dry-run. Dopiero po sprawdzeniu adresata,
treści i cooldownu ustaw flagę scheduler na `true` i skonfiguruj osobno
kontrolowany harmonogram, który przekazuje świeże snapshoty oraz opróżnia
kolejkę. Samo ustawienie flagi nie rozpoczyna pracy cyklicznej.

## Backup i odtwarzanie

Skrypt zapisuje stan `.openjarvis`, w tym paper ledger oraz alerty, do
`/srv/agi-procesor/backups`. Domyślna retencja to 14 dni.

```bash
sudo install -d -m 0700 -o "$USER" -g "$USER" \
  /srv/agi-procesor/backups
./scripts/backup.sh
sha256sum -c /srv/agi-procesor/backups/*.sha256
```

Przykładowy cron uruchamiany jako użytkownik wdrożeniowy:

```cron
15 2 * * * cd /srv/agi-procesor/source/deploy/vps-procesor && ./scripts/backup.sh >> /srv/agi-procesor/backups/backup.log 2>&1
```

Przed odtworzeniem zatrzymaj usługę, zachowaj kopię aktualnego wolumenu i
zweryfikuj sumę SHA-256. Nie nadpisuj danych bez sprawdzonego rollbacku.
Kopia na tym samym VPS chroni przed błędem aplikacji, lecz nie przed awarią
serwera. Okresowo kopiuj zaszyfrowane archiwum do osobnej lokalizacji.

## Aktualizacja i rollback

Automatyczne aktualizacje upstream są wyłączone. Aktualizuj tylko z zaufanej
gałęzi AGI PROCESOR:

```bash
cd /srv/agi-procesor/source
git fetch origin agi-procesor-mvp
git diff --stat HEAD..origin/agi-procesor-mvp
git log --oneline HEAD..origin/agi-procesor-mvp
```

Po przeglądzie zmian wykonaj backup, fast-forward, build i healthcheck. Zachowaj
poprzedni commit, aby rollback był jednoznaczny:

```bash
previous_commit="$(git rev-parse HEAD)"
git branch "rollback-$(date -u +%Y%m%dT%H%M%SZ)" "$previous_commit"
git merge --ff-only origin/agi-procesor-mvp
cd deploy/vps-procesor
./scripts/backup.sh
docker compose --env-file .env -f compose.yml build
docker compose --env-file .env -f compose.yml up -d
./scripts/healthcheck.sh
```

Jeżeli healthcheck nie przejdzie, wróć do utworzonej gałęzi `rollback-*`,
ponownie zbuduj stack i odtwórz dane wyłącznie wtedy, gdy migracja faktycznie
zmieniła ich format. Nie usuwaj starego archiwum przed weryfikacją.

## Monitoring

Minimum operacyjne:

```bash
docker compose --env-file .env -f compose.yml ps
docker compose --env-file .env -f compose.yml logs --tail=200 agi-procesor
curl --fail https://alerts.procesor.com/health
```

Alert operacyjny powinien reagować na niedostępność `/health`, brak świeżych
danych, błąd wysyłki i rosnącą kolejkę. Brak nowych sygnałów nie jest awarią.

## Dokumentacja źródłowa

- [Instalacja Docker Engine na Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Docker Compose: healthcheck i zależności](https://docs.docker.com/compose/gettingstarted/)
- [Docker Compose: polityka restartu](https://docs.docker.com/reference/compose-file/services/#restart)
- [nginx: HTTP Basic Authentication](https://nginx.org/en/docs/http/ngx_http_auth_basic_module.html)
- [nginx: limitowanie liczby żądań](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html)
- [Certbot: nginx i test odnowienia](https://eff-certbot.readthedocs.io/en/stable/using.html)

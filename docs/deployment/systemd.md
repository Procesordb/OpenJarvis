# systemd Service (Linux)

AGI PROCESOR includes a systemd unit file for running the API server as a managed background service on Linux. This provides automatic startup on boot, crash recovery, and integration with standard Linux service management tools.

## Prerequisites

Before installing the service, ensure that:

1. AGI PROCESOR is installed in a virtual environment at `/opt/agi_procesor/.venv` (or adjust paths accordingly).
2. A dedicated `agi_procesor` system user exists (recommended for security).
3. An inference engine (such as Ollama) is running and accessible.

Create the user and installation directory:

```bash
sudo useradd --system --create-home --home-dir /opt/agi_procesor agi_procesor
sudo -u agi_procesor python3 -m venv /opt/agi_procesor/.venv
sudo -u agi_procesor git clone https://github.com/Procesordb/OpenJarvis.git /opt/agi_procesor/AGI-PROCESOR
cd /opt/agi_procesor/AGI-PROCESOR && sudo -u agi_procesor uv sync --extra server
```

## Installing the Service

The unit binds `0.0.0.0`, so an **API key is required** — and the unit
declares `EnvironmentFile=/etc/agi_procesor/env` (no `-` prefix), so it will
**fail to start** until that file exists with a key. Create it first:

```bash
sudo mkdir -p /etc/agi_procesor
echo "AGI_PROCESOR_API_KEY=$(agi auth generate-key)" | sudo tee /etc/agi_procesor/env
sudo chmod 600 /etc/agi_procesor/env
```

Then copy the unit file, reload the daemon, and enable the service:

```bash
sudo cp deploy/systemd/agi-procesor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable agi_procesor
sudo systemctl start agi_procesor
```

Clients must send `Authorization: Bearer <key>` on `/v1/*` and `/api/*`
requests. (If you instead bind to `127.0.0.1`, the key is optional and you
can drop the `EnvironmentFile` line.)

Verify it is running:

```bash
sudo systemctl status agi_procesor
```

## Service File Reference

The provided unit file at `deploy/systemd/agi-procesor.service`:

```ini
[Unit]
Description=AGI PROCESOR API Server
After=network.target

[Service]
Type=simple
User=agi_procesor
WorkingDirectory=/opt/agi_procesor
ExecStart=/opt/agi_procesor/.venv/bin/agi serve --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5
Environment=HOME=/opt/agi_procesor

[Install]
WantedBy=multi-user.target
```

### `[Unit]` Section

| Directive     | Value              | Description                                                                 |
|---------------|--------------------|-----------------------------------------------------------------------------|
| `Description` | `AGI PROCESOR API Server` | Human-readable name shown in `systemctl status` and logs.              |
| `After`       | `network.target`   | Delays startup until the network stack is available, since the server binds to a network socket and may need to reach a remote engine. |

### `[Service]` Section

| Directive          | Value                                                              | Description                                                                                     |
|--------------------|--------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| `Type`             | `simple`                                                           | The process started by `ExecStart` is the main service process. systemd considers the service started immediately. |
| `User`             | `agi_procesor`                                                       | Runs the server as the `agi_procesor` user rather than root, limiting the blast radius of any security issue. |
| `WorkingDirectory` | `/opt/agi_procesor`                                                  | Sets the working directory for the process. This is where AGI PROCESOR looks for local files and writes data. |
| `ExecStart`        | `/opt/agi_procesor/.venv/bin/agi serve --host 0.0.0.0 --port 8000` | The command to start the server. Uses the full path to the `agi` binary inside the virtual environment. |
| `Restart`          | `on-failure`                                                       | Automatically restarts the service if it exits with a non-zero exit code. Does not restart on clean shutdown (`systemctl stop`). |
| `RestartSec`       | `5`                                                                | Waits 5 seconds before attempting a restart, preventing rapid restart loops if the service crashes immediately on startup. |
| `Environment`      | `HOME=/opt/agi_procesor`                                             | Sets the `HOME` environment variable so AGI PROCESOR finds its configuration at `~/.agi-procesor/config.toml` (resolving to `/opt/agi_procesor/.agi-procesor/config.toml`). |

### `[Install]` Section

| Directive    | Value               | Description                                                                                 |
|--------------|---------------------|---------------------------------------------------------------------------------------------|
| `WantedBy`   | `multi-user.target` | The service starts when the system reaches multi-user mode (standard boot target for servers). `systemctl enable` creates a symlink under this target. |

## Configuration Options

### Changing the Bind Address and Port

Edit the `ExecStart` line to change the host or port:

```ini
ExecStart=/opt/agi_procesor/.venv/bin/agi serve --host 127.0.0.1 --port 9000
```

!!! tip
    Binding to `127.0.0.1` restricts access to localhost only. Use this when running behind a reverse proxy like Nginx or Caddy.

### Setting the Engine and Model

Pass additional flags to `agi serve`:

```ini
ExecStart=/opt/agi_procesor/.venv/bin/agi serve --host 0.0.0.0 --port 8000 --engine ollama --model qwen3:8b
```

### Adding Environment Variables

Add multiple `Environment` directives or use `EnvironmentFile` for complex configurations:

```ini
[Service]
Environment=HOME=/opt/agi_procesor
Environment=AGI_PROCESOR_ENGINE_DEFAULT=vllm
Environment=AGI_PROCESOR_OLLAMA_HOST=http://localhost:11434
```

Or load from a file:

```ini
[Service]
EnvironmentFile=/opt/agi_procesor/.env
```

### Changing the User

If you prefer a different service user, update both the `User` directive and the paths:

```ini
[Service]
User=myuser
WorkingDirectory=/home/myuser/agi_procesor
ExecStart=/home/myuser/agi_procesor/.venv/bin/agi serve --host 0.0.0.0 --port 8000
Environment=HOME=/home/myuser/agi_procesor
```

### Using a Configuration File

Ensure the configuration file exists at the path where `HOME` points:

```bash
sudo -u agi_procesor mkdir -p /opt/agi_procesor/.agi-procesor
sudo -u agi_procesor cp config.toml /opt/agi_procesor/.agi-procesor/config.toml
```

The server reads `~/.agi-procesor/config.toml` on startup, where `~` resolves from the `HOME` environment variable.

## Viewing Logs

AGI PROCESOR logs are captured by journald. View them with `journalctl`:

```bash
# View all logs for the service
sudo journalctl -u agi_procesor

# Follow logs in real time
sudo journalctl -u agi_procesor -f

# View logs since the last boot
sudo journalctl -u agi_procesor -b

# View logs from the last hour
sudo journalctl -u agi_procesor --since "1 hour ago"

# View only error-level messages
sudo journalctl -u agi_procesor -p err
```

## Managing the Service

### Start, Stop, and Restart

```bash
# Start the service
sudo systemctl start agi_procesor

# Stop the service
sudo systemctl stop agi_procesor

# Restart the service (stop + start)
sudo systemctl restart agi_procesor

# Reload configuration without full restart (sends SIGHUP)
sudo systemctl reload-or-restart agi_procesor
```

### Check Status

```bash
sudo systemctl status agi_procesor
```

Example output:

```
● agi-procesor.service - AGI PROCESOR API Server
     Loaded: loaded (/etc/systemd/system/agi-procesor.service; enabled; preset: enabled)
     Active: active (running) since Fri 2026-02-21 10:00:00 UTC; 2h ago
   Main PID: 12345 (agi)
      Tasks: 4 (limit: 4915)
     Memory: 256.0M
        CPU: 1min 23s
     CGroup: /system.slice/agi-procesor.service
             └─12345 /opt/agi_procesor/.venv/bin/python /opt/agi_procesor/.venv/bin/agi serve --host 0.0.0.0 --port 8000
```

### Enable and Disable on Boot

```bash
# Enable automatic start on boot
sudo systemctl enable agi_procesor

# Disable automatic start on boot
sudo systemctl disable agi_procesor
```

### Apply Changes After Editing the Unit File

After modifying `/etc/systemd/system/agi-procesor.service`, reload the systemd daemon and restart the service:

```bash
sudo systemctl daemon-reload
sudo systemctl restart agi_procesor
```

## Running Alongside Ollama

If Ollama is also managed via systemd, you can add an ordering dependency so the AGI PROCESOR service waits for Ollama to start:

```ini
[Unit]
Description=AGI PROCESOR API Server
After=network.target ollama.service
Requires=ollama.service
```

| Directive  | Description                                                              |
|------------|--------------------------------------------------------------------------|
| `After`    | Ensures AGI PROCESOR starts after Ollama.                                  |
| `Requires` | If Ollama fails to start, AGI PROCESOR will not start either.              |

!!! note
    Use `Wants` instead of `Requires` if you want AGI PROCESOR to start even when Ollama is unavailable (for example, if you plan to start Ollama manually later).

# ping-me

`ping-me` runs a command and sends a [Pushover](https://pushover.net/) notification when it completes.

## Install

```bash
pip install .
```

## Pushover setup (quick)

1. Create a Pushover account at <https://pushover.net/>.
2. Install at least one client (iOS, Android, or Desktop) and complete device registration.
3. From your Pushover dashboard, copy your **User Key**.
4. Create an application/API token at <https://pushover.net/apps/build> and copy the **API Token/Key**.
5. Set both values before running `ping-me`:

```bash
export PING_ME_PUSHOVER_USER=your_user_key
export PING_ME_PUSHOVER_TOKEN=your_app_token
```

Pricing note: Pushover is free to try for 30 days, then currently costs about **$5 USD** (listed as **$4.99 USD**) as a one-time per-platform purchase for individuals. See <https://pushover.net/pricing>.

## Usage

```bash
PING_ME_PUSHOVER_TOKEN=... \
PING_ME_PUSHOVER_USER=... \
ping-me -- your command here
```

The `--` separator is required. Everything after `--` is executed with `subprocess.run(..., shell=False)`.

## Python API

You can also send notifications directly from Python:

```python
from ping_me import notify

notify("epoch done")
notify("evaluation failed", status="failure", return_code=1)
```

`notify(...)` supports a non-terminal progress/update status (`notify_progress`), in addition to terminal statuses like `success`, `failure`, and `interrupt`.

### Inherited context in subprocesses

When you run a command through:

```bash
ping-me --name training -- python train.py
```

`ping-me` injects run metadata into the child process environment:

- `PING_ME_CONTEXT_ACTIVE=1`
- `PING_ME_JOB_NAME=<resolved job name>` (when available)
- `PING_ME_PARENT_COMMAND=<the command text>`

Any deeper subprocesses inherit these variables by default unless a layer intentionally clears or overrides its environment.

## Development

Install test tooling with:

```bash
pip install -r tests/requirements.txt
```

Run tests with:

```bash
pytest
```

## Environment variables

Required:

- `PING_ME_PUSHOVER_TOKEN`
- `PING_ME_PUSHOVER_USER`

Optional:

- `PING_ME_TITLE` (default: `ping-me`)
- `PING_ME_NOTIFY` (default: `all`)
  - `all`, `none`, `terminal`, or a comma-separated list like `success,failure,interrupt,notify_progress`
- `PING_ME_DEVICE_NAME` (default: your system hostname from `socket.gethostname()`)
  - Set to any non-empty string to override the host shown in notifications

Examples:

```bash
# uses your system hostname
PING_ME_PUSHOVER_TOKEN=... PING_ME_PUSHOVER_USER=... ping-me -- echo ok

# override the device/host name included in the notification
PING_ME_DEVICE_NAME="work-macbook" PING_ME_PUSHOVER_TOKEN=... PING_ME_PUSHOVER_USER=... ping-me -- echo ok
```


Short note: test-only dependencies are kept in `tests/requirements.txt` so root requirements stay focused on runtime installs.

# ping-me

`ping-me` runs a command and sends a [Pushover](https://pushover.net/) notification when it completes.

## Install

```bash
pip install .
```

For test dependencies:

```bash
pip install -r tests/requirements-dev.txt
```

## Usage

```bash
PING_ME_PUSHOVER_TOKEN=... \
PING_ME_PUSHOVER_USER=... \
ping-me -- your command here
```

The `--` separator is required. Everything after `--` is executed with `subprocess.run(..., shell=False)`.

## Environment variables

Required:

- `PING_ME_PUSHOVER_TOKEN`
- `PING_ME_PUSHOVER_USER`

Optional:

- `PING_ME_TITLE` (default: `ping-me`)
- `PING_ME_NOTIFY` (default: `all`)
  - `all`, `none`, or a comma-separated list like `success,failure,interrupt`
- `PING_ME_DEVICE_NAME` (default: your system hostname from `socket.gethostname()`)
  - Set to any non-empty string to override the host shown in notifications

Examples:

```bash
# uses your system hostname
PING_ME_PUSHOVER_TOKEN=... PING_ME_PUSHOVER_USER=... ping-me -- echo ok

# override the device/host name included in the notification
PING_ME_DEVICE_NAME="work-macbook" PING_ME_PUSHOVER_TOKEN=... PING_ME_PUSHOVER_USER=... ping-me -- echo ok
```

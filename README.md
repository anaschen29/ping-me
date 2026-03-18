# ping-me

`ping-me` runs a command and sends a [Pushover](https://pushover.net/) notification when it completes.

## Install

```bash
pip install .
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
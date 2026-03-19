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

## Development

Install test tooling with:

```bash
pip install -r requirements-dev.txt
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
  - `all`, `none`, or a comma-separated list like `success,failure,interrupt`
# discord-gift-sniper

I wrote this to quickly claim Discord Nitro gifts from servers I am in. It connects directly to the Discord Gateway via websockets using a user token, parses incoming messages for gift codes, and claims them immediately via the Discord API.

It does not use any heavy bot frameworks. Just raw websockets and aiohttp to keep the latency as low as possible.

## Installation

Make sure you have Python 3.10+ installed.

Clone the repository and install the dependency:

```cmd
pip install -r requirements.txt
```

## Usage

You need a Discord user token (not a bot token). Pass it via the `--token` argument or set the `DISCORD_TOKEN` environment variable.

```cmd
python sniper.py --token YOUR_TOKEN_HERE
```

Options:

* `--token`: Your Discord account token.
* `--log`: Path to write logs to (defaults to stdout only).
* `--ignore-self`: Do not attempt to claim gifts sent by your own user account.

<!-- checked: 2026-09-14 -->

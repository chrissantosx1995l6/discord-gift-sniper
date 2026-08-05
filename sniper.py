import argparse
import asyncio
import json
import re
import sys
import time
import aiohttp

# Handles various gift formats including old links and desktop redirects
CODE_RE = re.compile(r"(?:discord\.gift/|discord(?:app)?\.com/gifts/)([a-zA-Z0-9]{16,24})")

class NitroSniper:
    """Gateway listener to catch and redeem Nitro gift codes."""
    def __init__(self, token: str):
        self.token = token
        # Modern headers to look like a desktop client request
        self.headers = {
            "Authorization": token,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json"
        }
        self.session = None
        self.heartbeat_interval = None
        self.last_sequence = None

    async def redeem(self, code: str, channel_id: str):
        url = f"https://discord.com/api/v9/entitlements/gift-codes/{code}/redeem"
        payload = {"channel_id": channel_id, "payment_source_id": None}
        
        start = time.perf_counter()
        try:
            async with self.session.post(url, headers=self.headers, json=payload) as r:
                elapsed = (time.perf_counter() - start) * 1000
                res_text = await r.text()
                try:
                    res_json = json.loads(res_text)
                    message = res_json.get("message", "no message returned")
                except json.JSONDecodeError:
                    message = "invalid json payload"

                if r.status == 200:
                    print(f"[{elapsed:.1f}ms] successfully claimed: {code}")
                else:
                    print(f"[{elapsed:.1f}ms] failed code {code}: {r.status} ({message})")
        except aiohttp.ClientError as e:
            print(f"error claiming {code}: {e}")

    async def heartbeat(self, ws):
        # We handle heartbeats as a background loop tied to the specific active ws socket
        while not ws.closed:
            await asyncio.sleep(self.heartbeat_interval / 1000.0)
            payload = {"op": 1, "d": self.last_sequence}
            try:
                await ws.send_json(payload)
            except (aiohttp.ClientError, ConnectionResetError):
                break

    async def run(self):
        # Reuse tcp connections & keep dns cached to minimize network latency on requests
        connector = aiohttp.TCPConnector(use_dns_cache=True, ttl_dns_cache=300)
        async with aiohttp.ClientSession(connector=connector) as session:
            self.session = session
            
            while True:
                try:
                    gateway_url = "wss://gateway.discord.gg/?v=9&encoding=json"
                    async with session.ws_connect(gateway_url) as ws:
                        print("connected to gateway. listening for codes...")
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                op = data.get("op")
                                t = data.get("t")
                                d = data.get("d")
                                
                                if "s" in data:
                                    self.last_sequence = data["s"]

                                # print(f"received event: {t}")

                                if op == 10:  # Hello handshake
                                    self.heartbeat_interval = d["heartbeat_interval"]
                                    asyncio.create_task(self.heartbeat(ws))
                                    
                                    identify = {
                                        "op": 2,
                                        "d": {
                                            "token": self.token,
                                            "properties": {
                                                "$os": "windows",
                                                "$browser": "chrome",
                                                "$device": "pc"
                                            }
                                        }
                                    }
                                    await ws.send_json(identify)

                                elif op == 0:  # Event dispatch
                                    if t == "MESSAGE_CREATE":
                                        content = d.get("content", "")
                                        channel_id = d.get("channel_id")
                                        match = CODE_RE.search(content)
                                        if match:
                                            code = match.group(1)
                                            print(f"found nitro code in chat: {code}")
                                            # spawn concurrently to avoid blocking gateway parser
                                            asyncio.create_task(self.redeem(code, channel_id))
                                            
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
                except aiohttp.ClientError as e:
                    # TODO: handle Gateway Resume (OP 6) on reconnect to prevent missing messages during disconnect gaps
                    print(f"websocket error: {e}. reconnecting in 5s...")
                    await asyncio.sleep(5)

def main():
    parser = argparse.ArgumentParser(
        description="lightweight gateway-based nitro sniper",
        usage="python -m sniper.sniper --token <token>"
    )
    parser.add_argument("--token", required=True, help="discord user auth token")
    args = parser.parse_args()

    if not args.token.strip():
        print("error: token is empty", file=sys.stderr)
        sys.exit(1)

    sniper = NitroSniper(args.token)
    try:
        asyncio.run(sniper.run())
    except KeyboardInterrupt:
        print("\nstopped sniper.")
    except Exception as e:
        print(f"fatal error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

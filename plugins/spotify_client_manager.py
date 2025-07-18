import aiohttp
import asyncio
import itertools
import base64
import logging

logger = logging.getLogger(__name__)

class SpotifyClientManager:
    def __init__(self, clients):
        self.clients = clients
        self.client_cycle = itertools.cycle(clients)
        self.current_token = None
        self.token_expiry = 0
        self.lock = asyncio.Lock()

    async def _get_token(self, client_id, client_secret):
        url = "https://accounts.spotify.com/api/token"
        creds = f"{client_id}:{client_secret}"
        b64_creds = base64.b64encode(creds.encode()).decode()
        headers = {
            "Authorization": f"Basic {b64_creds}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "client_credentials"}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"Failed to get token: {resp.status} {text}")
                    return None, 0
                res = await resp.json()
                return res.get("access_token"), res.get("expires_in", 3600)

    async def make_request(self, url, params=None):
        async with self.lock:
            now = asyncio.get_event_loop().time()
            if self.current_token is None or now >= self.token_expiry:
                client = next(self.client_cycle)
                token, expires_in = await self._get_token(client["client_id"], client["client_secret"])
                if token is None:
                    logger.error(f"Skipping client {client['client_id']} due to token fetch failure.")
                    # Try next client next time
                    self.current_token = None
                    self.token_expiry = 0
                    return None
                self.current_token = token
                self.token_expiry = now + expires_in - 60  # Renew 1 minute early
                logger.info(f"Switched Spotify token to client_id={client['client_id']}")

            headers = {"Authorization": f"Bearer {self.current_token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status == 429:
                    retry_after = int(resp.headers.get("Retry-After", 5))
                    logger.warning(f"Rate limited. Sleeping for {retry_after} seconds...")
                    await asyncio.sleep(retry_after + 1)
                    return None
                elif resp.status != 200:
                    text = await resp.text()
                    logger.error(f"Spotify API error {resp.status}: {text}")
                    return None
                return await resp.json()

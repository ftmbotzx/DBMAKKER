# utils.py

import aiohttp
import asyncio
import logging
import os
import re
import urllib.parse

import random

logger = logging.getLogger(__name__)

def safe_filename(name: str) -> str:
    """Remove unsafe filesystem characters from a filename."""
    return re.sub(r'[\\/*?:"<>|]', '_', name)

import asyncio

aria2c_semaphore = asyncio.Semaphore(1)  # max 1 parallel

async def download_with_aria2c(url, output_dir, filename):
    async with aria2c_semaphore:
        # optional small delay before starting
        await asyncio.sleep(1)

        cmd = [
            "aria2c",
            "-x", "2",
            "-s", "2",
            "-k", "1M",
            "--max-tries=5",
            "--retry-wait=5",
            "--timeout=60",
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "-d", output_dir,
            "-o", filename,
            url
        ]
        logger.info(f"Running command: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        logger.info(f"aria2c STDOUT:\n{stdout.decode().strip()}")
        logger.info(f"aria2c STDERR:\n{stderr.decode().strip()}")

        if process.returncode == 0:
            logger.info(f"aria2c download succeeded: {os.path.join(output_dir, filename)}")
            return True
        else:
            logger.error(f"aria2c failed with exit code {process.returncode}")
            # optionally implement exponential backoff retry here
            return False


logger = logging.getLogger(__name__)

async def get_song_download_url_by_spotify_url(spotify_url: str):
    encoded_url = urllib.parse.quote(spotify_url)
    api_urls = [
        f"https://tet-kpy4.onrender.com/spotify?url={encoded_url}",
        f"https://tet-kpy4.onrender.com/spotify2?url={encoded_url}"
    ]

    chosen_api = random.choice(api_urls)  # Randomly pick one API

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(chosen_api, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("status") and "data" in data:
                        song_data = data["data"]
                        found_title = song_data.get("title")
                        download_url = song_data.get("download")
                        if download_url:
                            download_url_fixed = urllib.parse.quote(download_url, safe=':/?&=')
                            logger.info(f"Got download URL from {chosen_api}")
                            return found_title, download_url_fixed
                        else:
                            logger.warning(f"No download URL in response from {chosen_api}")
                            return found_title, None
                    else:
                        logger.warning(f"Invalid response data from {chosen_api}: {data}")
                        return None, None
                else:
                    logger.error(f"API request failed with status {resp.status} from {chosen_api}")
                    return None, None
        except Exception as e:
            logger.error(f"Exception while requesting {chosen_api}: {e}")
            return None, None

async def download_thumbnail(thumb_url: str, output_path: str) -> bool:
    if not thumb_url:
        return False

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumb_url) as resp:
                if resp.status == 200:
                    with open(output_path, "wb") as f:
                        f.write(await resp.read())
                    logging.info(f"Thumbnail downloaded to {output_path}")
                    return True
    except Exception as e:
        logging.error(f"Thumbnail download failed: {e}")

    return False

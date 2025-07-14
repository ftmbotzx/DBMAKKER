# utils.py

import aiohttp
import asyncio
import logging
import os
import re
import urllib.parse

logger = logging.getLogger(__name__)

def safe_filename(name: str) -> str:
    """Remove unsafe filesystem characters from a filename."""
    return re.sub(r'[\\/*?:"<>|]', '_', name)

async def download_with_aria2c(url: str, output_dir: str, filename: str) -> bool:
    """
    Download a file asynchronously using aria2c CLI.
    Returns True if download succeeded, False otherwise.
    """
    cmd = [
        "aria2c",
        "-x", "16",
        "-s", "16",
        "-k", "1M",
        "-d", output_dir,
        "-o", filename,
        url
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode == 0:
        full_path = os.path.join(output_dir, filename)
        logger.info(f"aria2c download succeeded: {full_path}")
        return True
    else:
        logger.error(f"aria2c download failed: {stderr.decode().strip()}")
        return False

async def get_song_download_url_by_spotify_url(spotify_url: str):
    """
    Calls external API to get song info & download URL by Spotify track URL.
    Returns (title, download_url) or (None, None) if failed.
    """
    encoded_url = urllib.parse.quote(spotify_url)
    api_url = f"https://tet-kpy4.onrender.com/spotify?url={encoded_url}"

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("status") and "data" in data:
                    song_data = data["data"]
                    found_title = song_data.get("title")
                    download_url = song_data.get("download")

                    if download_url:
                        download_url_fixed = urllib.parse.quote(download_url, safe=':/?&=')
                        return found_title, download_url_fixed
                    else:
                        logger.warning("Download URL missing in API response data.")
                        return found_title, None
                else:
                    logger.warning(f"API response missing expected data or status is false: {data}")
                    return None, None
            else:
                logger.error(f"API request failed with status code: {resp.status}")
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


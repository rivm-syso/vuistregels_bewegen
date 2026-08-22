"""Hulpmiddelen die door meerdere adapters worden gebruikt: HTTP-
download naar disk en zip-extractie."""
import logging
import os
import zipfile

import requests

logger = logging.getLogger(__name__)


def file_downloader(url: str, local_filename: str) -> None:
    """Download het bestand op ``url`` en sla het op als
    ``local_filename``. Streamt in blokken van 8 KiB om geheugengebruik
    beperkt te houden."""
    try:
        with requests.get(url, stream=True) as response:
            response.raise_for_status()  # controleer of de download succesvol was
            with open(local_filename, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
        logger.info("Bestand gedownload en opgeslagen als %s", local_filename)
    except requests.exceptions.RequestException as e:
        logger.error("Er is een fout opgetreden bij downloaden van %s: %s", url, e)


def unzip_file(zip_file_path: str, extract_to_dir: str) -> None:
    """Pak het ZIP-bestand op ``zip_file_path`` uit in
    ``extract_to_dir``. Maakt de doelmap aan als die nog niet
    bestaat."""
    # zorg dat de doelmap bestaat
    os.makedirs(extract_to_dir, exist_ok=True)

    # open het ZIP-bestand
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        # pak alles uit naar de opgegeven map
        zip_ref.extractall(extract_to_dir)
        logger.info("Alle bestanden uitgepakt naar %s", extract_to_dir)

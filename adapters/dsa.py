"""Adapter voor buitensport-voorzieningen uit het DSA-portaal van
Mulier Instituut. Vereist een API-key en e-mailadres in ``.env``.

De nieuwe DSA-API (2026) filtert voorzieningen op gemeente-UUID in
plaats van gemeentecode; een module-helper bouwt daarvoor eenmalig
een lokale mapping van alle Nederlandse gemeenten. Voorziening-detail
levert geen volle geometrie meer, alleen een centroid.
"""
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import geopandas as gpd
import pandas as pd
import requests
from dotenv import load_dotenv
from shapely.geometry import Point

from instellingen import DATA_PATH

load_dotenv()
DSA_KEY = os.getenv("DSA_KEY")
DSA_MAIL = os.getenv("DSA_MAIL")
DSA_BASE_URL = "https://dsa.mulierinstituut.nl/api/v1"

# KEY EN MAIL staan in .env
HEADERS = {"x-api-key": DSA_KEY, "x-api-email": DSA_MAIL, "Content-Type": "application/json"}

logger = logging.getLogger(__name__)


def _bouw_gemeente_uuid_cache(data_path: str = DATA_PATH) -> None:
    """Haal alle Nederlandse gemeenten op van DSA en cache
    ``(code, uuid, naam)`` als parquet. Doet niets wanneer de cache
    al bestaat. De listing bevat alleen een href, dus per gemeente is
    een detail-fetch nodig (parallel via threads)."""
    pad = f"{data_path}/dsa/gemeenten.parquet"
    if os.path.exists(pad):
        return
    os.makedirs(f"{data_path}/dsa", exist_ok=True)

    logger.info("DSA-gemeenten worden gedownload voor UUID-mapping (~356 items)")
    hrefs = []
    page = 1
    while True:
        r = requests.get(f"{DSA_BASE_URL}/gemeenten", headers=HEADERS, params={"page": page}, timeout=30)
        payload = r.json()
        hrefs.extend([g['href'] for g in payload['_links']['gemeenten']])
        if payload['_links'].get('next') is None:
            break
        page += 1

    def fetch(href: str) -> dict:
        return requests.get(href, headers=HEADERS, timeout=15).json()

    with ThreadPoolExecutor(max_workers=10) as pool:
        details = list(pool.map(fetch, hrefs))

    rijen = [{'code': d['code'], 'uuid': d['id'], 'naam': d['naam']} for d in details]
    pd.DataFrame(rijen).to_parquet(pad)


def _get_uuid_voor_gemeente(gemeente_code: str, data_path: str = DATA_PATH) -> str:
    """Vertaal een gemeentecode (bijv. ``GM1680``) naar de bijbehorende
    DSA-UUID. Bouwt de cache als die nog niet bestaat."""
    _bouw_gemeente_uuid_cache(data_path)
    df = pd.read_parquet(f"{data_path}/dsa/gemeenten.parquet")
    match = df.loc[df['code'] == gemeente_code]
    if len(match) == 0:
        raise ValueError(f"gemeente-code {gemeente_code!r} niet gevonden in DSA-gemeenten")
    return str(match.iloc[0]['uuid'])


class DSA():
    """Adapter voor DSA-buitensport-voorzieningen van één gemeente."""

    def __init__(self, gemeente_code: str) -> None:
        self.gemeente_code = gemeente_code
        self.download_dsa_gemeente()

    def _get_voorziening_data(self, url: str, headers: dict = HEADERS) -> Optional[dict]:
        """Haal één voorziening op via haar detail-URL. Retourneert
        ``None`` voor indoor-voorzieningen of voorzieningen zonder
        centroid."""
        response = requests.get(url, headers=headers, timeout=15)
        voorziening = response.json()
        centroid = voorziening.get('centroid')
        if voorziening.get('indoor') or centroid is None:
            return None
        lon, lat = centroid
        return {'voorziening_id': voorziening['id'], 'geometry': Point(lon, lat)}

    def download_dsa_gemeente(self, headers: dict = HEADERS) -> Optional[gpd.GeoDataFrame]:
        """Download alle buitensport-voorzieningen voor deze gemeente
        en cache als parquet. Retourneert een leeg GeoDataFrame wanneer
        er geen voorzieningen zijn."""
        os.makedirs(f"{DATA_PATH}/dsa", exist_ok=True)
        cache_pad = f"{DATA_PATH}/dsa/{self.gemeente_code}_buitensporten.parquet"
        if os.path.exists(cache_pad):
            return None

        uuid = _get_uuid_voor_gemeente(self.gemeente_code)

        voorziening_data_list = []
        page = 1
        while True:
            body = {"gemeenten": [uuid], "page": page}
            response = requests.post(
                f"{DSA_BASE_URL}/voorzieningen/search",
                headers=headers,
                data=json.dumps(body),
                timeout=30,
            )
            payload = response.json()
            for voorziening in payload['_links']['voorzieningen']:
                voorziening_data = self._get_voorziening_data(voorziening['href'], headers)
                if voorziening_data is not None:
                    voorziening_data_list.append(voorziening_data)
            if payload['_links'].get('next') is None:
                break
            page += 1

        if len(voorziening_data_list) == 0:
            return gpd.GeoDataFrame([
                {'voorziening_id': None, 'geometry': None},
                {'voorziening_id': None, 'geometry': None},
            ])
        df = gpd.GeoDataFrame(voorziening_data_list)
        df = df.set_crs(4326).to_crs(28992)
        df.to_parquet(cache_pad)
        return None

    def get_buitensporten(self) -> gpd.GeoDataFrame:
        """Retourneer de buitensport-voorzieningen voor deze gemeente.
        Triggert een download wanneer nog niet gecached."""
        cache_pad = f"{DATA_PATH}/dsa/{self.gemeente_code}_buitensporten.parquet"
        if os.path.exists(cache_pad):
            return gpd.read_parquet(cache_pad)
        self.download_dsa_gemeente()
        return self.get_buitensporten()

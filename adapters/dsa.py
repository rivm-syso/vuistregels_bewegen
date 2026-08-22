"""Adapter voor buitensport-voorzieningen uit het DSA-portaal van
Mulier Instituut. Vereist een API-key en e-mailadres in ``.env``."""
import json
import os
from math import ceil
from typing import Optional

import geopandas as gpd
import requests
from dotenv import load_dotenv
from shapely.geometry import shape

from instellingen import DATA_PATH

load_dotenv()
DSA_KEY = os.getenv("DSA_KEY")
DSA_MAIL = os.getenv("DSA_MAIL")

# KEY EN MAIL staan in .env
HEADERS = {"x-api-key": DSA_KEY, "x-api-email": DSA_MAIL, "Content-Type": "application/json"}
# TODO: overweeg getters met filter op gemeente, zodat classes niet te zwaar worden
# TODO: overweeg een flag om bestaande data te overschrijven


class DSA():
    """Adapter voor DSA-buitensport-voorzieningen van één gemeente."""

    def __init__(self, gemeente_code: str) -> None:
        self.gemeente_code = gemeente_code
        self.download_dsa_gemeente()

    def _get_voorziening_data(self, url: str, headers: dict = HEADERS) -> Optional[dict]:
        """Haal één voorziening op via haar detail-URL. Retourneert
        ``None`` voor indoor-voorzieningen of voorzieningen zonder
        geometrie."""
        response = requests.get(url, headers=headers)
        voorziening = response.json()
        if voorziening['indoor'] or voorziening['geometrie'] is None:
            return None
        return {'voorziening_id': voorziening['id'], 'geometry': shape(voorziening['geometrie']['geometry'])}

    def download_dsa_gemeente(self, headers: dict = HEADERS) -> Optional[gpd.GeoDataFrame]:
        """Download alle buitensport-voorzieningen voor deze gemeente
        en cache als parquet. Retourneert een leeg GeoDataFrame wanneer
        er geen voorzieningen zijn."""
        # gemeente_code is zonder GM en zonder leading 0
        if 'dsa' not in os.listdir(DATA_PATH):
            os.mkdir(f"{DATA_PATH}/dsa")
        if os.path.exists(f"{DATA_PATH}/dsa/{self.gemeente_code}_buitensporten.parquet"):
            return None
        gemeente_code = str(int(self.gemeente_code.replace("GM", "")))
        data = {"gemeenten": [gemeente_code]}
        response = requests.post("https://dsa-portaal.mulierinstituut.nl/api/v1/voorzieningen/search/", headers=headers, data=json.dumps(data))
        voorzieningen = response.json()
        number_pages = ceil(voorzieningen['total'] / 100)
        voorziening_data_list = []
        for page in range(number_pages):
            data = {"gemeenten": [gemeente_code], "page": page + 1}
            response = requests.get("https://dsa-portaal.mulierinstituut.nl/api/v1/voorzieningen/search", headers=headers, data=json.dumps(data))
            for voorziening in response.json()['_links']['voorzieningen']:
                voorziening_data = self._get_voorziening_data(voorziening['href'], headers)
                if voorziening_data is not None:
                    voorziening_data_list.append(voorziening_data)
        if len(voorziening_data_list) == 0:
            return gpd.GeoDataFrame([{'voorziening_id': None, 'geometry': None}, {'voorziening_id': None, 'geometry': None}])
        df = gpd.GeoDataFrame(voorziening_data_list)
        df = df.set_crs(4326).to_crs(28992)
        df['geometry'] = df.geometry.centroid
        df.to_parquet(f"{DATA_PATH}/dsa/GM{gemeente_code}_buitensporten.parquet")
        return None

    def get_buitensporten(self) -> gpd.GeoDataFrame:
        """Retourneer de buitensport-voorzieningen voor deze gemeente.
        Triggert een download wanneer nog niet gecached."""
        if os.path.exists(f"{DATA_PATH}/dsa/{self.gemeente_code}_buitensporten.parquet"):
            return gpd.read_parquet(f"{DATA_PATH}/dsa/{self.gemeente_code}_buitensporten.parquet")
        self.download_dsa_gemeente()
        return self.get_buitensporten()

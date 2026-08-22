"""Adapter voor de Basisregistratie Grootschalige Topografie (BGT) via
PDOK. Downloadt en cachet BGT-features per gemeente en levert een
gefilterde, geparsete GeoDataFrame."""
import json
import os
import shutil
import time
from typing import Optional

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry

from instellingen import DATA_PATH

from .utils import file_downloader, unzip_file

# TODO: overweeg getters met filter op gemeente, zodat classes niet te zwaar worden
# TODO: overweeg een flag om bestaande data te overschrijven

DEFAULT_FEATURETYPES = [
    "begroeidterreindeel",
    "onbegroeidterreindeel",
    "ondersteunendwegdeel",
    "ondersteunendwaterdeel",
    "waterdeel",
    "wegdeel",
    "straatmeubilair",
]


class BGT():
    """Adapter voor BGT-features van één gemeente.

    Bij instantiëring wordt de BGT-data gedownload en gecategoriseerd
    wanneer die nog niet lokaal aanwezig is. De constructor triggert
    ook alvast een parse-run zodat de parquet-cache klaar staat.
    """

    def __init__(self, gemeente_code: str, geometry: BaseGeometry) -> None:
        self.gemeente_code = gemeente_code
        self.geometry = geometry
        self.download_gemeente()
        self.get_gemeente()  # TODO wat vreemd, we doen niets met het resultaat

    def download_bgt(
        self,
        local_filename: str,
        geofilter: str,
        featuretypes: Optional[list] = None,
    ) -> None:
        """Downloadt de tegels van de BGT-server en slaat de zip op als
        ``local_filename``.

        :param local_filename: bestandsnaam waaronder de gedownloade zip
            wordt opgeslagen.
        :param geofilter: een polygoon in WKT-formaat die het gebied
            aangeeft waarvoor de BGT moet worden opgevraagd.
        :param featuretypes: op te vragen featuretypes. Standaard alle
            typen uit ``DEFAULT_FEATURETYPES``.
        """
        if featuretypes is None:
            featuretypes = DEFAULT_FEATURETYPES

        API_URL = "https://api.pdok.nl"
        prepare_download_url = API_URL + "/lv/bgt/download/v1_0/full/custom"
        post_params = {
            "format": "gmllight",
            "featuretypes": featuretypes,
            "geofilter": geofilter,
        }
        headers = {'accept': 'application/json', 'Content-Type': 'application/json'}

        download_link = requests.post(prepare_download_url, data=json.dumps(post_params), headers=headers)

        if download_link.status_code != 202:
            raise RuntimeError("Fout bij aanvragen BGT-download")
        download_status_url = f"{API_URL}{download_link.json()['_links']['status']['href']}"
        download_status = requests.get(download_status_url)
        while download_status.status_code == 200:
            download_status = requests.get(download_status_url)
            time.sleep(1)
        if download_status.status_code == 201:
            file_downloader(f"{API_URL}{download_status.json()['_links']['download']['href']}", local_filename)

    def _geometry_to_bounding_box(self, geometry: BaseGeometry) -> Polygon:
        """Retourneer de axis-aligned bounding box van de gegeven
        geometrie als een gesloten polygoon."""
        min_x, min_y, max_x, max_y = geometry.bounds

        return Polygon([
            (min_x, min_y),
            (max_x, min_y),
            (max_x, max_y),
            (min_x, max_y),
            (min_x, min_y),  # sluit de polygoon door het eerste punt te herhalen
        ])

    def _load_feature(self, feature: str) -> gpd.GeoDataFrame:
        """Laad één BGT-featuretype uit het GML-bestand voor deze
        gemeente. Retourneert een leeg GeoDataFrame wanneer het bestand
        niet leesbaar is."""
        try:
            df = gpd.read_file(f"{DATA_PATH}/bgt/gemeenten/{self.gemeente_code}/bgt_{feature}.gml")
        except IndexError:
            df = gpd.GeoDataFrame()
        df['file'] = feature
        return df

    def download_gemeente(self, features: Optional[list] = None) -> None:
        """Download alle featuretypes voor deze gemeente, laad ze samen
        en cache als parquet. Doet niets wanneer de cache al bestaat."""
        if features is None:
            features = DEFAULT_FEATURETYPES

        if os.path.exists(f"{DATA_PATH}/bgt/gemeenten/{self.gemeente_code}_bgt_features.parquet"):
            return
        if 'bgt' not in os.listdir(DATA_PATH):
            os.mkdir(f"{DATA_PATH}/bgt")
            os.mkdir(f"{DATA_PATH}/bgt/gemeenten")
        self.download_bgt(f"{DATA_PATH}/bgt/{self.gemeente_code}.zip", self._geometry_to_bounding_box(self.geometry).wkt)
        unzip_file(f"{DATA_PATH}/bgt/{self.gemeente_code}.zip", f"{DATA_PATH}/bgt/gemeenten/{self.gemeente_code}")
        os.remove(f"{DATA_PATH}/bgt/{self.gemeente_code}.zip")

        dfs = [self._load_feature(feature) for feature in features]
        df = pd.concat(dfs, ignore_index=True)
        df = df.loc[pd.isnull(df.eindRegistratie)]
        df.to_parquet(f"{DATA_PATH}/bgt/gemeenten/{self.gemeente_code}_bgt_features.parquet")
        shutil.rmtree(f"{DATA_PATH}/bgt/gemeenten/{self.gemeente_code}")

    def get_gemeente(self) -> gpd.GeoDataFrame:
        """Retourneer de gefilterde en gecategoriseerde BGT-features
        voor deze gemeente. Triggert een download wanneer nog niet
        gecached."""
        if os.path.exists(f"{DATA_PATH}/bgt/gemeenten/{self.gemeente_code}_bgt_features.parquet"):
            return self.parse_gemeente()
        self.download_gemeente()
        return self.get_gemeente()

    def parse_gemeente(self) -> gpd.GeoDataFrame:
        """Verwijder straatmeubilair en erven, splits speelvoorzieningen
        af naar een aparte cache, en retourneer de opgeschoonde
        BGT-features."""
        if os.path.exists(f"{DATA_PATH}/bgt/gemeenten/{self.gemeente_code}_bgt_features_parsed.parquet"):
            return gpd.read_parquet(f"{DATA_PATH}/bgt/gemeenten/{self.gemeente_code}_bgt_features_parsed.parquet")
        bgt_gemeente = gpd.read_parquet(f"{DATA_PATH}/bgt/gemeenten/{self.gemeente_code}_bgt_features.parquet")
        bgt_speel_df = bgt_gemeente.loc[bgt_gemeente["plus-type"] == "speelvoorziening"]
        bgt_speel_df['naam'] = 'from_bgt'
        bgt_speel_df = bgt_speel_df[['naam', 'geometry']]
        bgt_gemeente = bgt_gemeente.loc[bgt_gemeente.file != 'straatmeubilair']
        bgt_gemeente = bgt_gemeente.loc[bgt_gemeente['bgt-fysiekVoorkomen'] != 'erf']
        bgt_gemeente = bgt_gemeente.drop(['opTalud'], axis=1)
        bgt_gemeente.to_parquet(f"{DATA_PATH}/bgt/gemeenten/{self.gemeente_code}_bgt_features_parsed.parquet")
        bgt_speel_df.to_parquet(f"{DATA_PATH}/bgt/gemeenten/{self.gemeente_code}_bgt_playgrounds_parsed.parquet")
        return self.parse_gemeente()

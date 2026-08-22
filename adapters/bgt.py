"""Adapter voor de Basisregistratie Grootschalige Topografie (BGT) via
PDOK. Downloadt en cachet BGT-features per gemeente en levert een
gefilterde, geparsete GeoDataFrame.

Opgesplitst in drie verantwoordelijkheden:

- ``BgtDownloader``: haalt de zip via de asynchrone PDOK-API, pakt uit
  en cacht de losse GML-bestanden op disk (I/O).
- ``BgtParser``: leest de GML-bestanden, filtert straatmeubilair/erven,
  splitst speelvoorzieningen af, en cacht per stap als parquet
  (transformatie).
- ``BGT``: facade die downloader en parser combineert en de
  ``BgtPoort`` implementeert.
"""
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

DEFAULT_FEATURETYPES = [
    "begroeidterreindeel",
    "onbegroeidterreindeel",
    "ondersteunendwegdeel",
    "ondersteunendwaterdeel",
    "waterdeel",
    "wegdeel",
    "straatmeubilair",
]


class BgtDownloader():
    """Downloadt BGT-features via de asynchrone PDOK-API en pakt de
    zip uit tot losse GML-bestanden per featuretype. Idempotent."""

    def __init__(self, data_path: str = DATA_PATH) -> None:
        self.data_path = data_path

    def zorg_voor_gmls(
        self,
        gemeente_code: str,
        geometry: BaseGeometry,
        featuretypes: Optional[list] = None,
    ) -> None:
        """Zorg dat de GML-bestanden voor deze gemeente op disk staan.
        Doet niets wanneer de raw-parquet of de GML-map al bestaat."""
        raw_parquet = f"{self.data_path}/bgt/gemeenten/{gemeente_code}_bgt_features.parquet"
        gml_dir = f"{self.data_path}/bgt/gemeenten/{gemeente_code}"
        if os.path.exists(raw_parquet) or os.path.exists(gml_dir):
            return
        if 'bgt' not in os.listdir(self.data_path):
            os.mkdir(f"{self.data_path}/bgt")
            os.mkdir(f"{self.data_path}/bgt/gemeenten")
        zip_pad = f"{self.data_path}/bgt/{gemeente_code}.zip"
        self._download_zip_via_api(zip_pad, self._bounding_box(geometry).wkt, featuretypes)
        unzip_file(zip_pad, gml_dir)
        os.remove(zip_pad)

    def _download_zip_via_api(
        self,
        local_filename: str,
        geofilter: str,
        featuretypes: Optional[list] = None,
    ) -> None:
        """Vraag de BGT-download aan via de asynchrone PDOK-API en
        download de zip zodra beschikbaar."""
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

    def _bounding_box(self, geometry: BaseGeometry) -> Polygon:
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


class BgtParser():
    """Leest GML-bestanden of eerder gecachte parquets en levert de
    gefilterde BGT-features als GeoDataFrame. Cacht tussenstappen."""

    def __init__(self, data_path: str = DATA_PATH) -> None:
        self.data_path = data_path

    def parse(self, gemeente_code: str, featuretypes: Optional[list] = None) -> gpd.GeoDataFrame:
        """Retourneer de gefilterde BGT-features voor deze gemeente.
        Bouwt raw- en gefilterde parquet-caches wanneer die nog niet
        bestaan."""
        self._zorg_voor_raw_parquet(gemeente_code, featuretypes)
        return self._zorg_voor_features_parquet(gemeente_code)

    def _zorg_voor_raw_parquet(self, gemeente_code: str, featuretypes: Optional[list] = None) -> None:
        """Combineer de losse GML-bestanden tot één parquet met alle
        raw features. Verwijdert de GML-map na afloop."""
        if featuretypes is None:
            featuretypes = DEFAULT_FEATURETYPES

        raw_parquet = f"{self.data_path}/bgt/gemeenten/{gemeente_code}_bgt_features.parquet"
        if os.path.exists(raw_parquet):
            return

        dfs = [self._laad_feature_gml(gemeente_code, feature) for feature in featuretypes]
        df = pd.concat(dfs, ignore_index=True)
        df = df.loc[pd.isnull(df.eindRegistratie)]
        df.to_parquet(raw_parquet)
        shutil.rmtree(f"{self.data_path}/bgt/gemeenten/{gemeente_code}")

    def _zorg_voor_features_parquet(self, gemeente_code: str) -> gpd.GeoDataFrame:
        """Verwijder straatmeubilair en erven, splits speelvoorzieningen
        af naar een aparte parquet, cache de opgeschoonde features en
        retourneer ze."""
        features_parquet = f"{self.data_path}/bgt/gemeenten/{gemeente_code}_bgt_features_parsed.parquet"
        if os.path.exists(features_parquet):
            return gpd.read_parquet(features_parquet)

        bgt_gemeente = gpd.read_parquet(f"{self.data_path}/bgt/gemeenten/{gemeente_code}_bgt_features.parquet")
        bgt_speel_df = bgt_gemeente.loc[bgt_gemeente["plus-type"] == "speelvoorziening"]
        bgt_speel_df['naam'] = 'from_bgt'
        bgt_speel_df = bgt_speel_df[['naam', 'geometry']]
        bgt_gemeente = bgt_gemeente.loc[bgt_gemeente.file != 'straatmeubilair']
        bgt_gemeente = bgt_gemeente.loc[bgt_gemeente['bgt-fysiekVoorkomen'] != 'erf']
        bgt_gemeente = bgt_gemeente.drop(['opTalud'], axis=1)
        bgt_gemeente.to_parquet(features_parquet)
        bgt_speel_df.to_parquet(f"{self.data_path}/bgt/gemeenten/{gemeente_code}_bgt_playgrounds_parsed.parquet")
        return bgt_gemeente

    def _laad_feature_gml(self, gemeente_code: str, feature: str) -> gpd.GeoDataFrame:
        """Laad één BGT-featuretype uit het GML-bestand voor deze
        gemeente. Retourneert een leeg GeoDataFrame wanneer het bestand
        niet aanwezig is (bijv. omdat de gemeente dat featuretype niet
        heeft)."""
        file_path = f"{self.data_path}/bgt/gemeenten/{gemeente_code}/bgt_{feature}.gml"
        if not os.path.exists(file_path):
            df = gpd.GeoDataFrame()
        else:
            df = gpd.read_file(file_path)
        df['file'] = feature
        return df


class BGT():
    """Facade voor BGT-features van één gemeente. Combineert downloader
    en parser en implementeert ``BgtPoort``.

    Downloader en parser zijn te vervangen via de constructor voor
    tests of alternatieve bronnen.
    """

    def __init__(
        self,
        gemeente_code: str,
        geometry: BaseGeometry,
        downloader: Optional[BgtDownloader] = None,
        parser: Optional[BgtParser] = None,
    ) -> None:
        self.gemeente_code = gemeente_code
        self.geometry = geometry
        self._downloader = downloader or BgtDownloader()
        self._parser = parser or BgtParser()
        self._downloader.zorg_voor_gmls(gemeente_code, geometry)

    def get_features(self) -> gpd.GeoDataFrame:
        """Retourneer de gefilterde en gecategoriseerde BGT-features
        voor deze gemeente."""
        return self._parser.parse(self.gemeente_code)

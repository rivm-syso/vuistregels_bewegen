"""Adapter voor speelpleklocaties. Combineert drie bronnen:
Buitenspeelkaart (optioneel, vereist expliciete toestemming van de
gebruiker), OpenStreetMap (Geofabrik-shapefiles per provincie), en de
speelvoorzieningen die door de BGT-adapter zijn afgezonderd.

Opgesplitst in drie verantwoordelijkheden:

- ``SpeelplekkenDownloader``: haalt de twee landelijke bronnen op en
  cacht ze op disk (I/O).
- ``SpeelplekkenParser``: filtert de landelijke bronnen op de
  buurt-geometrie, voegt de BGT-speelvoorzieningen toe, converteert
  alles naar puntgeometrie en cacht per gemeente (transformatie).
- ``Speelplekken``: facade die downloader en parser combineert en de
  ``SpeelplekkenPoort`` implementeert.
"""
import logging
import os
import shutil
from typing import Optional

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry.base import BaseGeometry

from instellingen import DATA_PATH

from .utils import file_downloader, unzip_file

logger = logging.getLogger(__name__)

DEFAULT_PROVINCIES = [
    'groningen',
    'friesland',
    'drenthe',
    'overijssel',
    'gelderland',
    'noord-holland',
    'flevoland',
    'zuid-holland',
    'utrecht',
    'zeeland',
    'noord-brabant',
    'limburg',
]


class SpeelplekkenDownloader():
    """Downloadt de twee landelijke bronnen (Buitenspeelkaart en OSM)
    naar disk. Idempotent."""

    def __init__(self, data_path: str = DATA_PATH) -> None:
        self.data_path = data_path

    def download_buitenspeelkaart(self) -> None:
        """Haal per plaats de speelplek-features op van
        buitenspeelkaart.nl en sla die op als GeoJSON."""
        plaatsen = requests.get("https://www.buitenspeelkaart.nl/getPlaatsen")
        plaats_ids = gpd.GeoDataFrame.from_features(plaatsen.json()).id.to_list()
        for plaats_id in plaats_ids:
            if not os.path.exists(f"{self.data_path}/buitenspeelkaart/{plaats_id}.geojson"):
                logger.info("Buitenspeelkaart-data wordt gedownload voor plaats %s", plaats_id)
                sp = requests.get(f"https://www.buitenspeelkaart.nl/getFeatures/1/p/{plaats_id}")
                sp = gpd.GeoDataFrame.from_features(sp.json(), crs="EPSG:4326")
                if 'buitenspeelkaart' not in os.listdir(self.data_path):
                    os.mkdir(f"{self.data_path}/buitenspeelkaart")
                sp.to_file(f"{self.data_path}/buitenspeelkaart/{plaats_id}.geojson", driver='GeoJSON')
        logger.info("Buitenspeelkaart-data compleet.")

    def download_osm_playgrounds(self, fclasses: list = ['playground']) -> None:
        """Haal per provincie de OSM POI-shapefiles op via Geofabrik en
        filter op speelpleken (``fclass == 'playground'``). Resultaat
        wordt per provincie opgeslagen als GeoJSON in RD-New."""
        for provincie in DEFAULT_PROVINCIES:
            if not os.path.exists(f"{self.data_path}/osm/{provincie}_playgrounds.geojson"):
                if 'osm' not in os.listdir(self.data_path):
                    os.mkdir(f"{self.data_path}/osm")
                file_downloader(f"https://download.geofabrik.de/europe/netherlands/{provincie}-latest-free.shp.zip", f"{self.data_path}/osm/{provincie}-latest-free.shp.zip")
                unzip_file(f"{self.data_path}/osm/{provincie}-latest-free.shp.zip", f"{self.data_path}/osm/{provincie}")
                os.remove(f"{self.data_path}/osm/{provincie}-latest-free.shp.zip")
                file1 = gpd.read_file(f'{self.data_path}/osm/{provincie}/gis_osm_pois_a_free_1.shp')
                file2 = gpd.read_file(f'{self.data_path}/osm/{provincie}/gis_osm_pois_free_1.shp')
                shutil.rmtree(f'{self.data_path}/osm/{provincie}')
                df_provincie = pd.concat([file1, file2]).to_crs(28992)
                df_provincie = df_provincie.loc[df_provincie.fclass.isin(fclasses)]
                df_provincie.geometry = df_provincie.geometry.centroid
                df_provincie.to_file(f"{self.data_path}/osm/{provincie}_playgrounds.geojson", driver='GeoJSON')


class SpeelplekkenParser():
    """Filtert de landelijke bronnen op de gemeente-geometrie, voegt de
    BGT-speelvoorzieningen toe, en cacht het resultaat per gemeente."""

    def __init__(self, data_path: str = DATA_PATH) -> None:
        self.data_path = data_path

    def parse(
        self,
        gemeente_code: str,
        geometry: BaseGeometry,
        toestemming_buitenspeelkaart: bool = False,
    ) -> gpd.GeoDataFrame:
        """Retourneer de gecombineerde speelpleklocaties voor deze
        gemeente. Bouwt de gecachte parquet wanneer die nog niet
        bestaat. Bij ``toestemming_buitenspeelkaart=False`` wordt de
        Buitenspeelkaart-bron overgeslagen en een aparte cache
        gebruikt zodat toestemming en niet-toestemming naast elkaar
        kunnen bestaan."""
        cache_pad = self._cache_pad(gemeente_code, toestemming_buitenspeelkaart)
        if os.path.exists(cache_pad):
            return gpd.read_parquet(cache_pad)
        return self._bouw_en_cache(gemeente_code, geometry, toestemming_buitenspeelkaart)

    def _bouw_en_cache(
        self,
        gemeente_code: str,
        geometry: BaseGeometry,
        toestemming_buitenspeelkaart: bool,
    ) -> gpd.GeoDataFrame:
        """Combineer de bronnen tot één GeoDataFrame met puntgeometrie
        en cache het resultaat als parquet. Buitenspeelkaart wordt
        alleen opgenomen wanneer daar expliciet toestemming voor is."""
        bronnen = [
            self._osm_binnen(geometry),
            self._bgt_speelvoorzieningen(gemeente_code),
        ]
        if toestemming_buitenspeelkaart:
            bronnen.insert(0, self._buitenspeelkaart_binnen(geometry))

        speelplekken_df = pd.concat(bronnen, ignore_index=True)
        speelplekken_df['geometry'] = speelplekken_df['geometry'].apply(_naar_punt)

        cache_pad = self._cache_pad(gemeente_code, toestemming_buitenspeelkaart)
        if 'processed' not in os.listdir(self.data_path):
            os.mkdir(f"{self.data_path}/processed")
            os.mkdir(f"{self.data_path}/processed/gemeenten")
        if gemeente_code not in os.listdir(f"{self.data_path}/processed/gemeenten"):
            os.mkdir(f"{self.data_path}/processed/gemeenten/{gemeente_code}")
        speelplekken_df.to_parquet(cache_pad)
        return speelplekken_df

    def _cache_pad(self, gemeente_code: str, toestemming_buitenspeelkaart: bool) -> str:
        suffix = "" if toestemming_buitenspeelkaart else "_zonder_buitenspeelkaart"
        return f"{self.data_path}/processed/gemeenten/{gemeente_code}/speelplekken{suffix}.parquet"

    def _buitenspeelkaart_binnen(self, geometry: BaseGeometry) -> gpd.GeoDataFrame:
        """Filter de landelijke buitenspeelkaart op features binnen de
        gegeven geometrie."""
        df = _combineer_geojsons(f"{self.data_path}/buitenspeelkaart/").to_crs(28992)
        return df.loc[df.intersects(geometry)][['naam', 'geometry']]

    def _osm_binnen(self, geometry: BaseGeometry) -> gpd.GeoDataFrame:
        """Filter de landelijke OSM-speelplekken op features binnen de
        gegeven geometrie."""
        df = _combineer_geojsons(f"{self.data_path}/osm/")
        df = df.loc[df.intersects(geometry)]
        df = df[['name', 'geometry']]
        df.rename(columns={'name': 'naam'}, inplace=True)
        return df

    def _bgt_speelvoorzieningen(self, gemeente_code: str) -> gpd.GeoDataFrame:
        """Retourneer de speelvoorzieningen die door de BGT-adapter zijn
        afgezonderd voor deze gemeente."""
        return gpd.read_parquet(f"{self.data_path}/bgt/gemeenten/{gemeente_code}_bgt_playgrounds_parsed.parquet")


def _combineer_geojsons(directory: str) -> gpd.GeoDataFrame:
    """Combineer alle GeoJSON-bestanden in de gegeven map tot één
    GeoDataFrame."""
    geojson_files = [f for f in os.listdir(directory) if f.endswith('.geojson')]
    gdfs = [gpd.read_file(os.path.join(directory, f)) for f in geojson_files]
    return gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))


def _naar_punt(geometry: BaseGeometry) -> BaseGeometry:
    """Zet een geometrie om naar een representatief punt. Punten blijven
    ongewijzigd."""
    if geometry.geom_type == 'Point':
        return geometry
    return geometry.representative_point()


class Speelplekken():
    """Facade voor speelpleklocaties. Combineert downloader en parser
    en implementeert ``SpeelplekkenPoort``.

    Downloader en parser zijn te vervangen via de constructor voor
    tests of alternatieve bronnen.
    """

    def __init__(
        self,
        gemeente_code: str,
        geometry: BaseGeometry,
        toestemming_buitenspeelkaart: bool = False,
        downloader: Optional[SpeelplekkenDownloader] = None,
        parser: Optional[SpeelplekkenParser] = None,
    ) -> None:
        self.gemeente_code = gemeente_code
        self.geometry = geometry
        self.toestemming_buitenspeelkaart = toestemming_buitenspeelkaart
        self._downloader = downloader or SpeelplekkenDownloader()
        self._parser = parser or SpeelplekkenParser()
        if self.toestemming_buitenspeelkaart:
            self._downloader.download_buitenspeelkaart()
        self._downloader.download_osm_playgrounds()

    def get_alle(self) -> gpd.GeoDataFrame:
        """Retourneer de gecombineerde speelpleklocaties voor deze
        gemeente."""
        return self._parser.parse(
            self.gemeente_code,
            self.geometry,
            toestemming_buitenspeelkaart=self.toestemming_buitenspeelkaart,
        )

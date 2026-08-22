"""Adapter voor speelpleklocaties. Combineert drie bronnen:
Buitenspeelkaart (jantje beton / kern-registratie), OpenStreetMap
(Geofabrik-shapefiles per provincie), en de speelvoorzieningen die
door de BGT-adapter zijn afgezonderd."""
import os
import shutil

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry.base import BaseGeometry

from instellingen import DATA_PATH

from .utils import file_downloader, unzip_file

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


class Speelplekken():
    """Adapter voor speelpleklocaties uit meerdere bronnen. Bij
    instantiëring wordt alle landelijke brondata gedownload wanneer die
    nog niet lokaal aanwezig is."""

    def __init__(self) -> None:
        self.download_buitenspeelkaart()
        self.download_osm_playgrounds()

    def download_buitenspeelkaart(self) -> None:
        """Haal per plaats de speelplek-features op van
        buitenspeelkaart.nl en sla die op als GeoJSON."""
        plaatsen = requests.get("https://www.buitenspeelkaart.nl/getPlaatsen")
        plaats_ids = gpd.GeoDataFrame.from_features(plaatsen.json()).id.to_list()
        for plaats_id in plaats_ids:
            if not os.path.exists(f"{DATA_PATH}/buitenspeelkaart/{plaats_id}.geojson"):
                print("Buitenspeelkaart data wordt gedownload")
                sp = requests.get(f"https://www.buitenspeelkaart.nl/getFeatures/1/p/{plaats_id}")
                sp = gpd.GeoDataFrame.from_features(sp.json())
                if 'buitenspeelkaart' not in os.listdir(DATA_PATH):
                    os.mkdir(f"{DATA_PATH}/buitenspeelkaart")
                sp.to_file(f"{DATA_PATH}/buitenspeelkaart/{plaats_id}.geojson", driver='GeoJSON')
        print("Buitenspeelkaart data gevonden.")

    def download_osm_playgrounds(self, fclasses: list = ['playground']) -> None:
        """Haal per provincie de OSM POI-shapefiles op via Geofabrik en
        filter op speelpleken (``fclass == 'playground'``). Resultaat
        wordt per provincie opgeslagen als GeoJSON in RD-New."""
        for provincie in DEFAULT_PROVINCIES:
            if not os.path.exists(f"{DATA_PATH}/osm/{provincie}_playgrounds.geojson"):
                if 'osm' not in os.listdir(DATA_PATH):
                    os.mkdir(f"{DATA_PATH}/osm")
                file_downloader(f"https://download.geofabrik.de/europe/netherlands/{provincie}-latest-free.shp.zip", f"{DATA_PATH}/osm/{provincie}-latest-free.shp.zip")
                unzip_file(f"{DATA_PATH}/osm/{provincie}-latest-free.shp.zip", f"{DATA_PATH}/osm/{provincie}")
                os.remove(f"{DATA_PATH}/osm/{provincie}-latest-free.shp.zip")
                file1 = gpd.read_file(f'{DATA_PATH}/osm/{provincie}/gis_osm_pois_a_free_1.shp')
                file2 = gpd.read_file(f'{DATA_PATH}/osm/{provincie}/gis_osm_pois_free_1.shp')
                shutil.rmtree(f'{DATA_PATH}/osm/{provincie}')
                df_provincie = pd.concat([file1, file2]).to_crs(28992)
                df_provincie = df_provincie.loc[df_provincie.fclass.isin(fclasses)]
                df_provincie.geometry = df_provincie.geometry.centroid
                df_provincie.to_file(f"{DATA_PATH}/osm/{provincie}_playgrounds.geojson", driver='GeoJSON')

    def concat_geojsons(self, directory: str) -> gpd.GeoDataFrame:
        """Combineer alle GeoJSON-bestanden in de gegeven map tot één
        GeoDataFrame."""
        files = os.listdir(directory)

        # filter op GeoJSON-bestanden
        geojson_files = [f for f in files if f.endswith('.geojson')]

        # verzamel de losse GeoDataFrames
        gdfs = []

        for file in geojson_files:
            file_path = os.path.join(directory, file)
            gdf = gpd.read_file(file_path)
            gdfs.append(gdf)

        # combineer tot één GeoDataFrame
        return gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))

    def get_buitenspeelkaart(self) -> gpd.GeoDataFrame:
        """Retourneer alle buitenspeelkaart-features als één
        GeoDataFrame."""
        return self.concat_geojsons(f"{DATA_PATH}/buitenspeelkaart/")

    def get_osm_playgrounds(self) -> gpd.GeoDataFrame:
        """Retourneer alle OSM-speelplekken als één GeoDataFrame."""
        return self.concat_geojsons(f"{DATA_PATH}/osm/")

    def _get_buitenspeelkaart_for_geometry(self, geometry: BaseGeometry) -> gpd.GeoDataFrame:
        """Filter de buitenspeelkaart op features binnen de gegeven
        geometrie."""
        df = self.get_buitenspeelkaart().to_crs(28992)
        return df.loc[df.intersects(geometry)][['naam', 'geometry']]

    def _get_osm_for_geometry(self, geometry: BaseGeometry) -> gpd.GeoDataFrame:
        """Filter de OSM-speelplekken op features binnen de gegeven
        geometrie."""
        df = self.get_osm_playgrounds()
        df = df.loc[df.intersects(geometry)]
        df = df[['name', 'geometry']]
        df.rename(columns={'name': 'naam'}, inplace=True)
        return df

    def _get_bgt_for_gemeente(self, gemeente_code: str) -> gpd.GeoDataFrame:
        """Retourneer de speelvoorzieningen die door de BGT-adapter zijn
        afgezonderd voor deze gemeente."""
        return gpd.read_parquet(f"{DATA_PATH}/bgt/gemeenten/{gemeente_code}_bgt_playgrounds_parsed.parquet")

    def _merge_speelplek_data(self, geometry: BaseGeometry, gemeente_code: str) -> gpd.GeoDataFrame:
        """Combineer de drie bronnen tot één GeoDataFrame met puntgeometrie
        en cache het resultaat als parquet."""
        def convert_to_point(geometry: BaseGeometry) -> BaseGeometry:
            if geometry.geom_type == 'Point':
                return geometry
            else:
                return geometry.representative_point()

        speelplekken_df = pd.concat([
            self._get_buitenspeelkaart_for_geometry(geometry),
            self._get_osm_for_geometry(geometry),
            self._get_bgt_for_gemeente(gemeente_code),
        ], ignore_index=True)
        speelplekken_df['geometry'] = speelplekken_df['geometry'].apply(convert_to_point)
        if 'processed' not in os.listdir(DATA_PATH):
            os.mkdir(f"{DATA_PATH}/processed")
            os.mkdir(f"{DATA_PATH}/processed/gemeenten")
        if gemeente_code not in os.listdir(f"{DATA_PATH}/processed/gemeenten"):
            os.mkdir(f"{DATA_PATH}/processed/gemeenten/{gemeente_code}")
        speelplekken_df.to_parquet(f"{DATA_PATH}/processed/gemeenten/{gemeente_code}/speelplekken.parquet")

        return speelplekken_df

    def get_alle(self, gemeente_code: str, geometry: BaseGeometry) -> gpd.GeoDataFrame:
        """Retourneer de gecombineerde speelpleklocaties binnen de
        gegeven geometrie voor deze gemeente. Bouwt de gecachte parquet
        wanneer die nog niet bestaat."""
        if os.path.exists(f"{DATA_PATH}/processed/gemeenten/{gemeente_code}/speelplekken.parquet"):
            return gpd.read_parquet(f"{DATA_PATH}/processed/gemeenten/{gemeente_code}/speelplekken.parquet")
        self._merge_speelplek_data(geometry, gemeente_code)
        return self.get_alle(gemeente_code, geometry)

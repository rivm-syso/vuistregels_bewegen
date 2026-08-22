import requests
import geopandas as gpd
import pandas as pd
import os
import shutil

from instellingen import DATA_PATH
from .utils import file_downloader, unzip_file

class Speelplekken():
    def __init__(self):
        self.download_buitenspeelkaart()
        self.download_osm_playgrounds()

    def download_buitenspeelkaart(self):
        plaatsen=requests.get("https://www.buitenspeelkaart.nl/getPlaatsen")
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

    def download_osm_playgrounds(self, fclasses=['playground']):
        provincies = [
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
            'limburg'
        ]
        for provincie in provincies:
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

    def concat_geojsons(self, directory):
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

    def get_buitenspeelkaart(self):
        return self.concat_geojsons(f"{DATA_PATH}/buitenspeelkaart/")

    def get_osm_playgrounds(self):
        return self.concat_geojsons(f"{DATA_PATH}/osm/")

    def _get_buitenspeelkaart_for_geometry(self, geometry):
        df = self.get_buitenspeelkaart().to_crs(28992)
        return df.loc[df.intersects(geometry)][['naam', 'geometry']]

    def _get_osm_for_geometry(self, geometry):
        df = self.get_osm_playgrounds()
        df = df.loc[df.intersects(geometry)]
        df = df[['name', 'geometry']]
        df.rename(columns={'name': 'naam'}, inplace=True)
        return df

    def _get_bgt_for_gemeente(self, gemeente_code):
        return gpd.read_parquet(f"{DATA_PATH}/bgt/gemeenten/{gemeente_code}_bgt_playgrounds_parsed.parquet")


    def _merge_speelplek_data(self, geometry, gemeente_code):
        def convert_to_point(geometry):
                if geometry.geom_type == 'Point':
                    return geometry
                else:
                    return geometry.representative_point()

        speelplekken_df = pd.concat([self._get_buitenspeelkaart_for_geometry(geometry), self._get_osm_for_geometry(geometry), self._get_bgt_for_gemeente(gemeente_code)], ignore_index=True)
        speelplekken_df['geometry'] = speelplekken_df['geometry'].apply(convert_to_point)
        if 'processed' not in os.listdir(DATA_PATH):
            os.mkdir(f"{DATA_PATH}/processed")
            os.mkdir(f"{DATA_PATH}/processed/gemeenten")
        if gemeente_code not in os.listdir(f"{DATA_PATH}/processed/gemeenten"):
            os.mkdir(f"{DATA_PATH}/processed/gemeenten/{gemeente_code}")
        speelplekken_df.to_parquet(f"{DATA_PATH}/processed/gemeenten/{gemeente_code}/speelplekken.parquet")

        return speelplekken_df

    def get_alle(self, gemeente_code, geometry):
        if os.path.exists(f"{DATA_PATH}/processed/gemeenten/{gemeente_code}/speelplekken.parquet"):
            return gpd.read_parquet(f"{DATA_PATH}/processed/gemeenten/{gemeente_code}/speelplekken.parquet")
        self._merge_speelplek_data(geometry, gemeente_code)
        return self.get_alle(gemeente_code, geometry)

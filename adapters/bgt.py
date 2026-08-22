import json
import time
import requests
import geopandas as gpd
import pandas as pd
import os
import shutil
from shapely.geometry import Polygon

from instellingen import DATA_PATH
from .utils import file_downloader, unzip_file

# TODO: overweeg getters met filter op gemeente, zodat classes niet te zwaar worden
# TODO: overweeg een flag om bestaande data te overschrijven

class BGT():
    def __init__(self,gemeente_code, geometry):
        self.gemeente_code = gemeente_code
        self.geometry = geometry
        self.download_gemeente()
        self.get_gemeente()  # TODO wat vreemd — we doen niets met het resultaat


    def download_bgt(self, local_filename, geofilter, featuretypes = ["begroeidterreindeel", "onbegroeidterreindeel", "ondersteunendwegdeel", "ondersteunendwaterdeel", "waterdeel", "wegdeel", "straatmeubilair"]):
        '''
        Downloadt de tegels van de BGT-server en slaat de zip op als
        `local_filename`.

        Vereiste parameters:

        - `local_filename`  bestandsnaam waaronder de gedownloade zip
                            wordt opgeslagen.
        - `geofilter`       een polygoon in WKT-formaat.

        Optionele parameters:

        - `featuretypes`    De op te vragen featuretypes. Zonder waarde
                            wordt de standaardset met alle
                            BGT-featuretypes gebruikt.
        '''


        API_URL = "https://api.pdok.nl"
        prepare_download_url = API_URL + "/lv/bgt/download/v1_0/full/custom"
        post_params = { "format":           "gmllight",
                        "featuretypes":     featuretypes,
                        "geofilter":        geofilter }
        headers =  {'accept': 'application/json', 'Content-Type': 'application/json'}

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

    def _geometry_to_bounding_box(self, geometry):
        min_x, min_y, max_x, max_y = geometry.bounds

        # bouw een bounding box-polygoon
        return Polygon([
            (min_x, min_y),
            (max_x, min_y),
            (max_x, max_y),
            (min_x, max_y),
            (min_x, min_y)  # sluit de polygoon door het eerste punt te herhalen
        ])

    def _load_feature(self, feature):
        try:
            df = gpd.read_file(f"{DATA_PATH}/bgt/gemeenten/{self.gemeente_code}/bgt_{feature}.gml")
        except IndexError as e:
            df = gpd.GeoDataFrame()
        df['file'] = feature
        return df

    def download_gemeente(self, features=["begroeidterreindeel", "onbegroeidterreindeel", "ondersteunendwegdeel", "ondersteunendwaterdeel", "waterdeel", "wegdeel", "straatmeubilair"]):
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

    def get_gemeente(self):
        if os.path.exists(f"{DATA_PATH}/bgt/gemeenten/{self.gemeente_code}_bgt_features.parquet"):
            return self.parse_gemeente()
        self.download_gemeente()
        return self.get_gemeente()

    def parse_gemeente(self):
        if os.path.exists(f"{DATA_PATH}/bgt/gemeenten/{self.gemeente_code}_bgt_features_parsed.parquet"):
            return gpd.read_parquet(f"{DATA_PATH}/bgt/gemeenten/{self.gemeente_code}_bgt_features_parsed.parquet")
        bgt_gemeente = gpd.read_parquet(f"{DATA_PATH}/bgt/gemeenten/{self.gemeente_code}_bgt_features.parquet")
        bgt_speel_df = bgt_gemeente.loc[bgt_gemeente["plus-type"]=="speelvoorziening"]
        bgt_speel_df['naam'] = 'from_bgt'
        bgt_speel_df = bgt_speel_df[['naam', 'geometry']]
        bgt_gemeente = bgt_gemeente.loc[bgt_gemeente.file!='straatmeubilair']
        bgt_gemeente = bgt_gemeente.loc[bgt_gemeente['bgt-fysiekVoorkomen']!='erf']
        bgt_gemeente = bgt_gemeente.drop(['opTalud'], axis=1)
        bgt_gemeente.to_parquet(f"{DATA_PATH}/bgt/gemeenten/{self.gemeente_code}_bgt_features_parsed.parquet")
        bgt_speel_df.to_parquet(f"{DATA_PATH}/bgt/gemeenten/{self.gemeente_code}_bgt_playgrounds_parsed.parquet")
        return self.parse_gemeente()

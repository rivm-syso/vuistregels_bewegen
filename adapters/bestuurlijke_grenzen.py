import geopandas as gpd
import os

from instellingen import DATA_PATH
from .utils import file_downloader, unzip_file

class BestuurlijkeGrenzen():
    def __init__(self, gemeente_code=None):
        self.download_gemeente_grenzen()
        self.download_buurt_grenzen()
        self.gemeente_code = gemeente_code


    def download_buurt_grenzen(self, layer="buurten"):
        if not os.path.exists(f"{DATA_PATH}/bestuurlijkegrenzen/{layer}"):
            print("Download gestart")
            os.mkdir(f"{DATA_PATH}/bestuurlijkegrenzen/{layer}")
            df = gpd.read_file("https://service.pdok.nl/cbs/wijkenbuurten/2024/atom/downloads/wijkenbuurten_2024.gpkg", layer=layer)
            df.to_parquet(f"{DATA_PATH}/bestuurlijkegrenzen/{layer}/grenzen.parquet")

    def download_gemeente_grenzen(self):
        if not os.path.exists(f"{DATA_PATH}/bestuurlijkegrenzen/gemeenten"):
            file_downloader("https://service.pdok.nl/kadaster/au/atom/v2_0/downloads/administrativeunits.zip", "administrativeunits.zip")
            unzip_file(f"{DATA_PATH}/administrativeunits.zip", f"{DATA_PATH}/bestuurlijkegrenzen/gemeenten")
            os.remove(f"{DATA_PATH}/administrativeunits.zip")

    def get_gemeenten(self):
        df_adm = gpd.read_file(f"{DATA_PATH}/bestuurlijkegrenzen/gemeenten/administrativeunits.gml", layer="AdministrativeUnit")
        return df_adm

    def get_gemeente(self):
        df_adm = self.parse_gemeenten(self.get_gemeenten())
        return df_adm.loc[df_adm.localId==self.gemeente_code]

    def get_buurten(self,):
        df = gpd.read_parquet(f"{DATA_PATH}/bestuurlijkegrenzen/buurten/grenzen.parquet")
        return df.loc[df.gemeentecode == self.gemeente_code]

    def parse_gemeenten(self, df_adm):
        df_adm_prov = df_adm.loc[df_adm.LocalisedCharacterString=="Provincie"]
        df_adm_prov = df_adm_prov[['text', 'geometry']]
        df_adm_prov.rename(columns={'text': 'provincie'}, inplace=True)
        df_adm_gem = df_adm.loc[df_adm.LocalisedCharacterString=="Gemeente"]
        df_adm_gem = df_adm_gem[['text', "localId", 'geometry']]
        df_adm_gem.rename(columns={'text': 'gemeente'}, inplace=True)
        gemeenten_in_provincies = gpd.sjoin(df_adm_gem, df_adm_prov, how="left", predicate="within")
        gemeenten_in_provincies.loc[gemeenten_in_provincies.gemeente=="Maasdriel", 'provincie'] = "Gelderland"
        return gemeenten_in_provincies[['gemeente', "localId", 'provincie', 'geometry']].to_crs(28992)

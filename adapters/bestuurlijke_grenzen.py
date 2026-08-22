"""Adapter voor Kadaster/CBS bestuurlijke grenzen (gemeenten en
buurten) via PDOK. Retourneert domein-entiteiten (Gemeente, Buurt) in
plaats van rauwe GeoDataFrames."""
import os
from typing import Optional

import geopandas as gpd

from domein.entiteiten import Buurt, Gemeente
from instellingen import DATA_PATH

from .utils import file_downloader, unzip_file


class BestuurlijkeGrenzen():
    """Adapter voor Kadaster/CBS bestuurlijke grenzen.

    Wordt geïnstantieerd voor één gemeente. Bij aanmaken wordt de
    landelijke bron gedownload wanneer die nog niet lokaal beschikbaar
    is.
    """

    def __init__(self, gemeente_code: Optional[str] = None) -> None:
        self.download_gemeente_grenzen()
        self.download_buurt_grenzen()
        self.gemeente_code = gemeente_code

    def download_buurt_grenzen(self, layer: str = "buurten") -> None:
        """Download de landelijke wijk- en buurtgrenzen van CBS/PDOK
        wanneer die nog niet lokaal aanwezig zijn."""
        if not os.path.exists(f"{DATA_PATH}/bestuurlijkegrenzen/{layer}"):
            print("Download gestart")
            os.mkdir(f"{DATA_PATH}/bestuurlijkegrenzen/{layer}")
            df = gpd.read_file("https://service.pdok.nl/cbs/wijkenbuurten/2024/atom/downloads/wijkenbuurten_2024.gpkg", layer=layer)
            df.to_parquet(f"{DATA_PATH}/bestuurlijkegrenzen/{layer}/grenzen.parquet")

    def download_gemeente_grenzen(self) -> None:
        """Download de landelijke gemeentegrenzen (administrative units)
        van Kadaster/PDOK wanneer die nog niet lokaal aanwezig zijn."""
        if not os.path.exists(f"{DATA_PATH}/bestuurlijkegrenzen/gemeenten"):
            file_downloader("https://service.pdok.nl/kadaster/au/atom/v2_0/downloads/administrativeunits.zip", "administrativeunits.zip")
            unzip_file(f"{DATA_PATH}/administrativeunits.zip", f"{DATA_PATH}/bestuurlijkegrenzen/gemeenten")
            os.remove(f"{DATA_PATH}/administrativeunits.zip")

    def get_gemeenten(self) -> gpd.GeoDataFrame:
        """Retourneer alle gemeenten als rauwe GeoDataFrame uit het
        administrative-units GML-bestand. Bedoeld voor intern gebruik;
        gebruik ``get_gemeente()`` voor één gemeente als
        domein-entiteit."""
        df_adm = gpd.read_file(f"{DATA_PATH}/bestuurlijkegrenzen/gemeenten/administrativeunits.gml", layer="AdministrativeUnit")
        return df_adm

    def get_gemeente(self) -> Gemeente:
        """Retourneer de gemeente waarvoor deze adapter is
        geïnstantieerd als domein-entiteit."""
        if self.gemeente_code is None:
            raise ValueError("gemeente_code is niet gezet op deze adapter")
        df_adm = self.parse_gemeenten(self.get_gemeenten())
        rij = df_adm.loc[df_adm.localId == self.gemeente_code].iloc[0]
        return Gemeente(
            code=rij['localId'],
            naam=rij['gemeente'],
            provincie=rij['provincie'],
            geometrie=rij['geometry'],
        )

    def get_buurten(self) -> list[Buurt]:
        """Retourneer alle buurten binnen deze gemeente als lijst van
        domein-entiteiten."""
        if self.gemeente_code is None:
            raise ValueError("gemeente_code is niet gezet op deze adapter")
        df = gpd.read_parquet(f"{DATA_PATH}/bestuurlijkegrenzen/buurten/grenzen.parquet")
        df = df.loc[df.gemeentecode == self.gemeente_code]
        return [
            Buurt(
                code=rij['buurtcode'],
                naam=rij['buurtnaam'],
                wijkcode=rij['wijkcode'],
                gemeentecode=rij['gemeentecode'],
                geometrie=rij['geometry'],
            )
            for _, rij in df.iterrows()
        ]

    def parse_gemeenten(self, df_adm: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Zet de rauwe administrative-units DataFrame om naar een
        DataFrame met per gemeente de kolommen ``gemeente``, ``localId``,
        ``provincie`` en ``geometry``, en herprojecteer naar RD-New."""
        df_adm_prov = df_adm.loc[df_adm.LocalisedCharacterString == "Provincie"]
        df_adm_prov = df_adm_prov[['text', 'geometry']]
        df_adm_prov.rename(columns={'text': 'provincie'}, inplace=True)
        df_adm_gem = df_adm.loc[df_adm.LocalisedCharacterString == "Gemeente"]
        df_adm_gem = df_adm_gem[['text', "localId", 'geometry']]
        df_adm_gem.rename(columns={'text': 'gemeente'}, inplace=True)
        gemeenten_in_provincies = gpd.sjoin(df_adm_gem, df_adm_prov, how="left", predicate="within")
        # Maasdriel valt geometrisch niet netjes binnen één provincie; hard vaststellen op Gelderland.
        gemeenten_in_provincies.loc[gemeenten_in_provincies.gemeente == "Maasdriel", 'provincie'] = "Gelderland"
        return gemeenten_in_provincies[['gemeente', "localId", 'provincie', 'geometry']].to_crs(28992)

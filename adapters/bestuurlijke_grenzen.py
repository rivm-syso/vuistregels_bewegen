"""Adapter voor Kadaster/CBS bestuurlijke grenzen (gemeenten en
buurten) via PDOK. Retourneert domein-entiteiten (Gemeente, Buurt) in
plaats van rauwe GeoDataFrames.

Opgesplitst in drie verantwoordelijkheden:

- ``BestuurlijkeGrenzenDownloader``: haalt de landelijke bronnen op en
  cacht ze op disk (I/O).
- ``BestuurlijkeGrenzenParser``: leest de gecachte bestanden en zet ze
  om naar domein-entiteiten (transformatie).
- ``BestuurlijkeGrenzen``: facade die downloader en parser combineert
  en de ``BestuurlijkeGrenzenInterface`` implementeert.
"""
import logging
import os
import shutil
from typing import Optional

import geopandas as gpd

from domein.entiteiten import Buurt, Gemeente
from instellingen import DATA_PATH

from .utils import file_downloader, unzip_file

logger = logging.getLogger(__name__)


def _zoek_administrativeunits_gml(data_path: str) -> Optional[str]:
    """Zoek het administrativeunits-GML-bestand onder de gemeenten-cache.
    De zip die PDOK aanbiedt bevat soms een subfolder; walk daarom
    recursief."""
    gemeenten_dir = f"{data_path}/bestuurlijkegrenzen/gemeenten"
    if not os.path.exists(gemeenten_dir):
        return None
    for root, _, bestanden in os.walk(gemeenten_dir):
        for naam in bestanden:
            if naam.lower().endswith(".gml") and "administrativeunit" in naam.lower():
                return os.path.join(root, naam)
    return None


class BestuurlijkeGrenzenDownloader():
    """Downloadt de landelijke gemeente- en buurtgrenzen naar disk.
    Idempotent: bestaande caches worden overgeslagen."""

    def __init__(self, data_path: str = DATA_PATH) -> None:
        self.data_path = data_path

    def download_gemeente_grenzen(self) -> None:
        """Download de landelijke gemeentegrenzen (administrative units)
        van Kadaster/PDOK wanneer die nog niet lokaal aanwezig zijn.
        Controleert op het aanwezige GML-bestand (niet alleen de dir)
        zodat een lege of corrupte cache uit een eerdere mislukte run
        wordt opgeruimd en opnieuw gedownload."""
        if _zoek_administrativeunits_gml(self.data_path) is not None:
            return

        gemeenten_dir = f"{self.data_path}/bestuurlijkegrenzen/gemeenten"
        if os.path.exists(gemeenten_dir):
            shutil.rmtree(gemeenten_dir)

        os.makedirs(self.data_path, exist_ok=True)
        zip_pad = f"{self.data_path}/administrativeunits.zip"
        try:
            file_downloader(
                "https://service.pdok.nl/kadaster/au/atom/v2_0/downloads/administrativeunits.zip",
                zip_pad,
            )
            unzip_file(zip_pad, gemeenten_dir)
            os.remove(zip_pad)
        except Exception:
            if os.path.exists(zip_pad):
                os.remove(zip_pad)
            if os.path.exists(gemeenten_dir):
                shutil.rmtree(gemeenten_dir)
            raise

    def download_buurt_grenzen(self, layer: str = "buurten") -> None:
        """Download de landelijke wijk- en buurtgrenzen van CBS/PDOK
        wanneer die nog niet lokaal aanwezig zijn."""
        if not os.path.exists(f"{self.data_path}/bestuurlijkegrenzen/{layer}"):
            logger.info("Download bestuurlijke grenzen (%s) gestart", layer)
            os.mkdir(f"{self.data_path}/bestuurlijkegrenzen/{layer}")
            df = gpd.read_file(
                "https://service.pdok.nl/cbs/wijkenbuurten/2024/atom/downloads/wijkenbuurten_2024.gpkg",
                layer=layer,
            )
            df.to_parquet(f"{self.data_path}/bestuurlijkegrenzen/{layer}/grenzen.parquet")


class BestuurlijkeGrenzenParser():
    """Leest de gecachte bestanden en zet ze om naar domein-entiteiten.
    Doet geen I/O naar externe bronnen; wel disk-reads uit de cache."""

    def __init__(self, data_path: str = DATA_PATH) -> None:
        self.data_path = data_path

    def parse_gemeente(self, gemeente_code: str) -> Gemeente:
        """Retourneer de gemeente voor ``gemeente_code`` als
        domein-entiteit."""
        df_adm = self._laad_alle_gemeenten()
        df_adm = self._normaliseer_gemeenten(df_adm)
        rij = df_adm.loc[df_adm.localId == gemeente_code].iloc[0]
        return Gemeente(
            code=rij['localId'],
            naam=rij['gemeente'],
            provincie=rij['provincie'],
            geometrie=rij['geometry'],
        )

    def parse_alle_gemeenten(self) -> list[Gemeente]:
        """Retourneer alle Nederlandse gemeenten als lijst van
        domein-entiteiten."""
        df_adm = self._laad_alle_gemeenten()
        df_adm = self._normaliseer_gemeenten(df_adm)
        return [
            Gemeente(
                code=rij['localId'],
                naam=rij['gemeente'],
                provincie=rij['provincie'],
                geometrie=rij['geometry'],
            )
            for _, rij in df_adm.iterrows()
        ]

    def parse_buurten(self, gemeente_code: str) -> list[Buurt]:
        """Retourneer alle buurten binnen ``gemeente_code`` als lijst
        van domein-entiteiten."""
        df = gpd.read_parquet(f"{self.data_path}/bestuurlijkegrenzen/buurten/grenzen.parquet")
        df = df.loc[df.gemeentecode == gemeente_code]
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

    def _laad_alle_gemeenten(self) -> gpd.GeoDataFrame:
        """Lees de rauwe administrative-units GML in. Zoekt recursief
        zodat zip-structuren met subfolder (zoals PDOK soms aanlevert)
        ook werken."""
        gml_pad = _zoek_administrativeunits_gml(self.data_path)
        if gml_pad is None:
            raise FileNotFoundError(
                f"Geen administrativeunits-GML gevonden onder "
                f"{self.data_path}/bestuurlijkegrenzen/gemeenten; "
                f"ruim die map op en draai opnieuw."
            )
        return gpd.read_file(gml_pad, layer="AdministrativeUnit")

    def _normaliseer_gemeenten(self, df_adm: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Zet de rauwe administrative-units DataFrame om naar een
        DataFrame met per gemeente de kolommen ``gemeente``, ``localId``,
        ``provincie`` en ``geometry``, herprojecteert naar RD-New."""
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


class BestuurlijkeGrenzen():
    """Facade voor Kadaster/CBS bestuurlijke grenzen. Combineert
    downloader en parser en implementeert ``BestuurlijkeGrenzenInterface``.

    Downloader en parser zijn te vervangen via de constructor voor
    tests of alternatieve bronnen.
    """

    def __init__(
        self,
        gemeente_code: Optional[str] = None,
        downloader: Optional[BestuurlijkeGrenzenDownloader] = None,
        parser: Optional[BestuurlijkeGrenzenParser] = None,
    ) -> None:
        self.gemeente_code = gemeente_code
        self._downloader = downloader or BestuurlijkeGrenzenDownloader()
        self._parser = parser or BestuurlijkeGrenzenParser()
        self._downloader.download_gemeente_grenzen()
        self._downloader.download_buurt_grenzen()

    def get_gemeente(self) -> Gemeente:
        """Retourneer de gemeente waarvoor deze adapter is
        geïnstantieerd als domein-entiteit."""
        if self.gemeente_code is None:
            raise ValueError("gemeente_code is niet gezet op deze adapter")
        return self._parser.parse_gemeente(self.gemeente_code)

    def get_buurten(self) -> list[Buurt]:
        """Retourneer alle buurten binnen deze gemeente als lijst van
        domein-entiteiten."""
        if self.gemeente_code is None:
            raise ValueError("gemeente_code is niet gezet op deze adapter")
        return self._parser.parse_buurten(self.gemeente_code)

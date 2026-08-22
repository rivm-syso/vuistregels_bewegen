"""Adapter voor RUDIFUN (PBL) buurt-kenmerken: dichtheden, functies,
oppervlakten. Wordt in de huidige use case nog niet actief gebruikt."""
import logging
import os
import shutil
import zipfile

import geopandas as gpd
import pandas as pd
import requests

from instellingen import DATA_PATH

logger = logging.getLogger(__name__)


class ORI():
    """Adapter voor RUDIFUN-buurtdata. Bij instantiëring wordt de
    landelijke bron gedownload wanneer die nog niet lokaal aanwezig
    is."""

    def __init__(self) -> None:
        self.download_rudifun()

    def download_rudifun(self) -> None:
        """Download de RUDIFUN-2024 GDB, extract de buurtlaag naar een
        parquet-cache, en verwijder de overige uitgepakte bestanden."""
        url = "https://dataportaal.pbl.nl/data/RUDIFUN/RUDIFUN_2024/NL_Rudifun2024_fgdb.zip"
        target_dir = f"{DATA_PATH}/rudifun"
        gdb_path = os.path.join(target_dir, "buurt2024.parquet")
        zip_path = os.path.join(target_dir, "NL_Rudifun2024_fgdb.zip")

        if not os.path.exists(gdb_path):
            os.makedirs(target_dir, exist_ok=True)
            logger.info("RUDIFUN-zip wordt gedownload...")
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(zip_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            logger.info("Download voltooid.")

            logger.info("Uitpakken...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            logger.info("Uitgepakt.")

            df = gpd.read_file(f"{DATA_PATH}/rudifun/Rudifun_2024_nl.gdb", layer='nl2_03_Basis_Buurt')
            df.drop('geometry', axis=1, inplace=True)
            df = df.rename(columns={"BU_CODE": "buurtcode"})
            df.to_parquet(f"{DATA_PATH}/rudifun/buurt2024.parquet")

            keep_file = "buurt2024.parquet"
            self._empty_dir_except(target_dir, keep_file)
            logger.info("RUDIFUN-cache klaar.")
        else:
            logger.info("RUDIFUN-cache bestaat al, download overgeslagen.")

    def _empty_dir_except(self, target_dir: str, keep_file: str) -> None:
        """Verwijder alle bestanden en submappen in ``target_dir``
        behalve ``keep_file``."""
        for fname in os.listdir(target_dir):
            file_path = os.path.join(target_dir, fname)
            if fname != keep_file:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)

    def get_rudifun(self) -> pd.DataFrame:
        """Retourneer de RUDIFUN-buurtdata als DataFrame (zonder
        geometrie; join op ``buurtcode`` met een andere bron voor
        geometrische context)."""
        return pd.read_parquet(f"{DATA_PATH}/rudifun/buurt2024.parquet")

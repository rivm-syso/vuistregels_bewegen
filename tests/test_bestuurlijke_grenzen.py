"""Tests voor de BestuurlijkeGrenzen-adapter en zijn onderdelen.

De ``parse_buurten``-test schrijft een minimale buurten-parquet naar
een tijdelijke map en verifieert dat de parser die correct omzet naar
``Buurt``-entiteiten. Geen externe I/O of downloads."""
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

from adapters.bestuurlijke_grenzen import (
    BestuurlijkeGrenzen,
    BestuurlijkeGrenzenParser,
)
from domein.entiteiten import Buurt
from domein.porten import BestuurlijkeGrenzenPoort


def _schrijf_buurten_fixture(data_path: Path, gemeente_code: str) -> None:
    """Schrijf een minimale buurten-parquet naar ``data_path`` in de
    layout die de parser verwacht."""
    (data_path / "bestuurlijkegrenzen" / "buurten").mkdir(parents=True)
    df = gpd.GeoDataFrame({
        'buurtcode': ['BU00000001', 'BU00000002'],
        'buurtnaam': ['Testbuurt A', 'Testbuurt B'],
        'wijkcode': ['WK0000', 'WK0000'],
        'gemeentecode': [gemeente_code, gemeente_code],
        'geometry': [box(0, 0, 100, 100), box(100, 0, 200, 100)],
    }, geometry='geometry', crs="EPSG:28992")
    df.to_parquet(data_path / "bestuurlijkegrenzen" / "buurten" / "grenzen.parquet")


def test_parse_buurten_leest_parquet_en_geeft_domein_entiteiten(tmp_path: Path):
    _schrijf_buurten_fixture(tmp_path, "GM9999")
    parser = BestuurlijkeGrenzenParser(data_path=str(tmp_path))

    buurten = parser.parse_buurten("GM9999")

    assert len(buurten) == 2
    assert all(isinstance(b, Buurt) for b in buurten)
    codes = {b.code for b in buurten}
    assert codes == {'BU00000001', 'BU00000002'}
    for b in buurten:
        assert b.gemeentecode == "GM9999"
        assert b.wijkcode == "WK0000"
        assert b.geometrie is not None


def test_parse_buurten_filtert_op_gemeentecode(tmp_path: Path):
    (tmp_path / "bestuurlijkegrenzen" / "buurten").mkdir(parents=True)
    df = gpd.GeoDataFrame({
        'buurtcode': ['BU00000001', 'BU00000002'],
        'buurtnaam': ['A', 'B'],
        'wijkcode': ['WK0', 'WK0'],
        'gemeentecode': ['GM9999', 'GM8888'],
        'geometry': [box(0, 0, 1, 1), box(1, 0, 2, 1)],
    }, geometry='geometry', crs="EPSG:28992")
    df.to_parquet(tmp_path / "bestuurlijkegrenzen" / "buurten" / "grenzen.parquet")

    parser = BestuurlijkeGrenzenParser(data_path=str(tmp_path))
    buurten = parser.parse_buurten("GM9999")

    assert len(buurten) == 1
    assert buurten[0].code == 'BU00000001'


class _FakeDownloader:
    """Doet niets; de tests hebben de cache-bestanden al klaargezet."""

    def download_gemeente_grenzen(self) -> None: pass
    def download_buurt_grenzen(self) -> None: pass


def test_facade_delegeert_naar_geinjecteerde_parser(tmp_path: Path):
    _schrijf_buurten_fixture(tmp_path, "GM9999")
    parser = BestuurlijkeGrenzenParser(data_path=str(tmp_path))

    adapter = BestuurlijkeGrenzen(
        gemeente_code="GM9999",
        downloader=_FakeDownloader(),
        parser=parser,
    )

    buurten = adapter.get_buurten()
    assert len(buurten) == 2
    assert isinstance(adapter, BestuurlijkeGrenzenPoort)

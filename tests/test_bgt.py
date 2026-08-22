"""Tests voor de BGT-adapter-onderdelen (Downloader en Parser). Geen
externe I/O; gebruikt tijdelijke fixture-parquets."""
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

from adapters.bgt import BgtDownloader, BgtParser


def test_bounding_box_omvat_geometrie():
    downloader = BgtDownloader()
    bbox = downloader._bounding_box(box(10, 20, 30, 40))
    min_x, min_y, max_x, max_y = bbox.bounds
    assert (min_x, min_y, max_x, max_y) == (10.0, 20.0, 30.0, 40.0)


def _schrijf_raw_parquet(data_path: Path, gemeente_code: str) -> None:
    """Minimale raw-features-parquet met alle kolommen die de parser
    aanraakt."""
    gemeenten_dir = data_path / "bgt" / "gemeenten"
    gemeenten_dir.mkdir(parents=True)
    df = gpd.GeoDataFrame({
        'geometry': [box(0, 0, 10, 10), box(10, 0, 20, 10), box(20, 0, 30, 10), box(30, 0, 40, 10)],
        'file': ['begroeidterreindeel', 'wegdeel', 'straatmeubilair', 'begroeidterreindeel'],
        'plus-type': [None, None, None, 'speelvoorziening'],
        'bgt-fysiekVoorkomen': ['groenvoorziening', None, None, 'erf'],
        'opTalud': [False, False, False, False],
        'naam': [None, None, None, None],
    }, geometry='geometry', crs="EPSG:28992")
    df.to_parquet(gemeenten_dir / f"{gemeente_code}_bgt_features.parquet")


def test_parser_verwijdert_straatmeubilair_en_erf(tmp_path: Path):
    _schrijf_raw_parquet(tmp_path, "GM9999")
    parser = BgtParser(data_path=str(tmp_path))

    df = parser.parse("GM9999")

    # Straatmeubilair, erf en speelvoorziening zijn eruit; alleen de
    # groenvoorziening en het wegdeel blijven over.
    files = sorted(df['file'].tolist())
    assert files == ['begroeidterreindeel', 'wegdeel']


def test_parser_splitst_speelvoorzieningen_naar_aparte_parquet(tmp_path: Path):
    _schrijf_raw_parquet(tmp_path, "GM9999")
    parser = BgtParser(data_path=str(tmp_path))
    parser.parse("GM9999")

    speel_parquet = tmp_path / "bgt" / "gemeenten" / "GM9999_bgt_playgrounds_parsed.parquet"
    assert speel_parquet.exists()
    speel_df = gpd.read_parquet(speel_parquet)
    assert len(speel_df) == 1
    assert speel_df.iloc[0]['naam'] == 'from_bgt'


def test_parser_dropt_opTalud_kolom(tmp_path: Path):
    _schrijf_raw_parquet(tmp_path, "GM9999")
    parser = BgtParser(data_path=str(tmp_path))

    df = parser.parse("GM9999")

    assert 'opTalud' not in df.columns


def test_parser_gebruikt_cache_bij_tweede_aanroep(tmp_path: Path):
    _schrijf_raw_parquet(tmp_path, "GM9999")
    parser = BgtParser(data_path=str(tmp_path))
    parser.parse("GM9999")

    features_parquet = tmp_path / "bgt" / "gemeenten" / "GM9999_bgt_features_parsed.parquet"
    assert features_parquet.exists()

    # tweede call moet gewoon slagen zonder te crashen op ontbrekende
    # bronbestanden (de raw-parquet is in de eerste run niet verwijderd
    # omdat we de GML-map niet hebben)
    df = parser.parse("GM9999")
    assert not df.empty

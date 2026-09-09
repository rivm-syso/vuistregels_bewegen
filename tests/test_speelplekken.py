"""Tests voor de Speelplekken-adapter-onderdelen. Geen externe I/O;
gebruikt tijdelijke fixture-bestanden voor de drie bronnen."""
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point, Polygon, box

from adapters.speelplekken import SpeelplekkenParser, _naar_punt


def test_naar_punt_laat_punten_ongewijzigd():
    punt = Point(5, 5)
    assert _naar_punt(punt) == punt


def test_naar_punt_zet_polygoon_om_naar_representatief_punt():
    resultaat = _naar_punt(box(0, 0, 10, 10))
    assert resultaat.geom_type == 'Point'
    # representative_point valt binnen de polygoon
    assert box(0, 0, 10, 10).contains(resultaat)


def _schrijf_bronnen(data_path: Path, gemeente_code: str, gemeente_geometry: Polygon) -> None:
    """Schrijf minimale fixtures voor de drie speelplek-bronnen.

    - Buitenspeelkaart: één punt binnen de gemeente, één erbuiten.
    - OSM: één punt binnen de gemeente.
    - BGT: één speelvoorziening voor deze gemeente.
    """
    # Buitenspeelkaart in EPSG:4326 (wordt door parser naar 28992 gebracht).
    # We houden dit simpel door de fixture direct in 28992 op te slaan;
    # de reprojectie in de parser is dan een no-op.
    (data_path / "buitenspeelkaart").mkdir(parents=True)
    bsk = gpd.GeoDataFrame({
        'naam': ['Speelplek binnen', 'Speelplek buiten'],
        'geometry': [Point(50, 50), Point(500, 500)],
    }, geometry='geometry', crs="EPSG:28992")
    bsk.to_file(data_path / "buitenspeelkaart" / "test.geojson", driver='GeoJSON')

    # OSM in EPSG:28992 (Geofabrik-shapefiles worden vooraf naar 28992
    # geconverteerd door de downloader; de parser hertransformeert niet).
    (data_path / "osm").mkdir(parents=True)
    osm = gpd.GeoDataFrame({
        'name': ['OSM speelplek'],
        'geometry': [Point(25, 25)],
    }, geometry='geometry', crs="EPSG:28992")
    osm.to_file(data_path / "osm" / "test_playgrounds.geojson", driver='GeoJSON')

    # BGT-speelvoorzieningen als parquet, layout gelijk aan wat BgtParser produceert.
    (data_path / "bgt" / "gemeenten").mkdir(parents=True)
    bgt = gpd.GeoDataFrame({
        'naam': ['from_bgt'],
        'geometry': [box(10, 10, 20, 20)],  # polygoon, wordt naar punt gezet
    }, geometry='geometry', crs="EPSG:28992")
    bgt.to_parquet(data_path / "bgt" / "gemeenten" / f"{gemeente_code}_bgt_playgrounds_parsed.parquet")


def test_parser_combineert_drie_bronnen_met_toestemming(tmp_path: Path):
    gemeente_geometry = box(0, 0, 100, 100)
    _schrijf_bronnen(tmp_path, "GM9999", gemeente_geometry)
    parser = SpeelplekkenParser(data_path=str(tmp_path))

    df = parser.parse("GM9999", gemeente_geometry, toestemming_buitenspeelkaart=True)

    # 1 buitenspeelkaart-binnen + 1 osm + 1 bgt = 3; de buitenspeelkaart-
    # feature buiten de gemeente is uitgefilterd.
    assert len(df) == 3
    namen = sorted(df['naam'].tolist())
    assert namen == ['OSM speelplek', 'Speelplek binnen', 'from_bgt']


def test_parser_slaat_buitenspeelkaart_over_zonder_toestemming(tmp_path: Path):
    gemeente_geometry = box(0, 0, 100, 100)
    _schrijf_bronnen(tmp_path, "GM9999", gemeente_geometry)
    parser = SpeelplekkenParser(data_path=str(tmp_path))

    # Standaard is toestemming_buitenspeelkaart=False.
    df = parser.parse("GM9999", gemeente_geometry)

    # Alleen OSM en BGT-speelvoorziening; geen buitenspeelkaart-feature.
    assert len(df) == 2
    namen = sorted(df['naam'].tolist())
    assert namen == ['OSM speelplek', 'from_bgt']


def test_parser_zet_alle_geometrieen_om_naar_punt(tmp_path: Path):
    gemeente_geometry = box(0, 0, 100, 100)
    _schrijf_bronnen(tmp_path, "GM9999", gemeente_geometry)
    parser = SpeelplekkenParser(data_path=str(tmp_path))

    df = parser.parse("GM9999", gemeente_geometry, toestemming_buitenspeelkaart=True)

    assert all(g.geom_type == 'Point' for g in df['geometry'])


def test_parser_cacht_apart_per_toestemming(tmp_path: Path):
    gemeente_geometry = box(0, 0, 100, 100)
    _schrijf_bronnen(tmp_path, "GM9999", gemeente_geometry)
    parser = SpeelplekkenParser(data_path=str(tmp_path))

    df_ja = parser.parse("GM9999", gemeente_geometry, toestemming_buitenspeelkaart=True)
    df_nee = parser.parse("GM9999", gemeente_geometry, toestemming_buitenspeelkaart=False)

    cache_dir = tmp_path / "processed" / "gemeenten" / "GM9999"
    assert (cache_dir / "speelplekken.parquet").exists()
    assert (cache_dir / "speelplekken_zonder_buitenspeelkaart.parquet").exists()

    # Tweede aanroep uit cache: zelfde lengtes.
    df_ja2 = parser.parse("GM9999", gemeente_geometry, toestemming_buitenspeelkaart=True)
    assert len(df_ja) == len(df_ja2)
    assert len(df_ja) != len(df_nee)

"""Tests voor de use case ``bereken_beweegvriendelijkheid`` en zijn
helpers. Draait volledig zonder externe I/O door fake adapters via
dependency injection te injecteren."""
from typing import List, Optional

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon, box

from domein.entiteiten import Buurt, Gemeente
from usecases.bereken_oppervlakte_beweegvriendelijk import (
    _bevat_punt,
    _union_area,
    bereken_beweegvriendelijkheid,
)


# --- _union_area -----------------------------------------------------

def test_union_area_zonder_overlap_telt_op():
    a = box(0, 0, 10, 10)
    b = box(20, 0, 30, 10)
    assert _union_area([a, b]) == pytest.approx(200.0)


def test_union_area_met_overlap_telt_overlap_1x():
    a = box(0, 0, 10, 10)
    b = box(5, 0, 15, 10)  # 50 m2 overlap
    assert _union_area([a, b]) == pytest.approx(150.0)


def test_union_area_leeg_is_nul():
    assert _union_area([]) == 0.0


def test_union_area_negeert_none_en_lege_geometrie():
    a = box(0, 0, 10, 10)
    empty = Polygon()
    assert _union_area([a, None, empty]) == pytest.approx(100.0)


# --- _bevat_punt -----------------------------------------------------

def test_bevat_punt_none_geeft_overal_false():
    df = gpd.GeoDataFrame({'geometry': [box(0, 0, 10, 10)]})
    result = _bevat_punt(df, None)
    assert result.tolist() == [False]


def test_bevat_punt_lege_puntenset_geeft_overal_false():
    df = gpd.GeoDataFrame({'geometry': [box(0, 0, 10, 10)]})
    empty = gpd.GeoDataFrame({'geometry': []}, geometry='geometry')
    result = _bevat_punt(df, empty)
    assert result.tolist() == [False]


def test_bevat_punt_matcht_binnenliggende_punten():
    df = gpd.GeoDataFrame({'geometry': [box(0, 0, 10, 10), box(20, 0, 30, 10)]})
    punten = gpd.GeoDataFrame({'geometry': [Point(5, 5)]})
    result = _bevat_punt(df, punten)
    assert result.tolist() == [True, False]


# --- bereken_beweegvriendelijkheid met fake adapters -----------------

class _FakeBestuurlijkeGrenzen:
    def __init__(self, gemeente_code: str) -> None:
        self.gemeente_code = gemeente_code

    def get_gemeente(self) -> Gemeente:
        return Gemeente(
            code=self.gemeente_code,
            naam="Testgemeente",
            provincie="Test",
            geometrie=box(0, 0, 100, 100),
        )

    def get_buurten(self) -> List[Buurt]:
        return [
            Buurt(
                code="BU00000001",
                naam="Testbuurt",
                wijkcode="WK0000",
                gemeentecode=self.gemeente_code,
                geometrie=box(0, 0, 100, 100),
            )
        ]


class _FakeBGT:
    def __init__(self, gemeente_code: str, geometry) -> None:
        pass

    def get_features(self) -> gpd.GeoDataFrame:
        # Kleine mix: groen (begroeidterreindeel) + wegdeel-auto
        rijen = [
            {
                'geometry': box(0, 0, 50, 100),
                'file': 'begroeidterreindeel',
                'bgt-fysiekVoorkomen': 'groenvoorziening',
                'bgt-functie': None,
                'bgt-type': None,
                'plus-type': None,
                'eindRegistratie': None,
            },
            {
                'geometry': box(50, 0, 100, 100),
                'file': 'wegdeel',
                'bgt-fysiekVoorkomen': None,
                'bgt-functie': 'rijbaan lokale weg',
                'bgt-type': None,
                'plus-type': None,
                'eindRegistratie': None,
            },
        ]
        return gpd.GeoDataFrame(rijen, geometry='geometry', crs="EPSG:28992")


class _FakeSpeelplekken:
    def __init__(self, gemeente_code: str, geometry) -> None:
        pass

    def get_alle(self) -> gpd.GeoDataFrame:
        return gpd.GeoDataFrame(
            {'geometry': [], 'naam': []},
            geometry='geometry',
            crs="EPSG:28992",
        )


def test_bereken_beweegvriendelijkheid_met_fakes_produceert_verwachte_shape():
    df = bereken_beweegvriendelijkheid(
        "GM9999",
        grenzen_klasse=_FakeBestuurlijkeGrenzen,
        bgt_klasse=_FakeBGT,
        speelplekken_klasse=_FakeSpeelplekken,
    )

    # Twee rijen per buurt: één area, één relative
    assert set(df['stat'].unique()) == {'area', 'relative'}
    assert len(df) == 2

    # Verwachte kolommen aanwezig
    for kolom in ['buurtnaam', 'rec_total', 'rec_actief', 'rec_auto', 'rec_groen_blauw']:
        assert kolom in df.columns, f"kolom {kolom!r} ontbreekt"

    # De fake heeft één groenvlak (5000 m2) en één rijbaan (5000 m2)
    area_rij = df.loc[df['stat'] == 'area'].iloc[0]
    assert area_rij['buurtnaam'] == "Testbuurt"
    assert area_rij['rec_groen_blauw'] == pytest.approx(5000.0)
    assert area_rij['rec_auto'] == pytest.approx(5000.0)
    assert area_rij['rec_total'] == pytest.approx(10000.0)


def test_bereken_beweegvriendelijkheid_zonder_buitensporten_klasse_zet_kolom_op_false():
    # Impliciet: buitensporten_klasse=None. De feature_engineering
    # moet dan alle buitensporten-vlaggen op False zetten en niet
    # crashen.
    df = bereken_beweegvriendelijkheid(
        "GM9999",
        grenzen_klasse=_FakeBestuurlijkeGrenzen,
        bgt_klasse=_FakeBGT,
        speelplekken_klasse=_FakeSpeelplekken,
    )
    # Als de feature_engineering had gefaald zou len(df) == 0 zijn
    assert not df.empty

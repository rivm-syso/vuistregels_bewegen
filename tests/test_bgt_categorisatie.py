"""Tests voor de BGT-categorisatie-regels."""
import geopandas as gpd
from shapely.geometry import Point

from domein.bgt_categorisatie import (
    pas_categorisatie_toe,
    structure,
    structure_wegdeel,
)


def _lege_df_met_kolommen() -> gpd.GeoDataFrame:
    """Minimale DataFrame met de kolommen die de regels raadplegen."""
    return gpd.GeoDataFrame({
        'geometry': [Point(0, 0), Point(1, 1), Point(2, 2)],
        'file': ['wegdeel', 'wegdeel', 'begroeidterreindeel'],
        'bgt-functie': ['fietspad', 'parkeervlak', None],
        'bgt-fysiekVoorkomen': [None, None, 'groenvoorziening'],
        'bgt-type': [None, None, None],
        'speelplekken': [False, False, False],
        'buitensporten': [False, False, False],
        'categorie': [None, None, None],
        'subcategorie': [None, None, None],
    })


def test_pas_categorisatie_toe_if_regel_labelt_matches():
    df = _lege_df_met_kolommen()
    df = pas_categorisatie_toe(df, {
        'feature_layer': 'wegdeel',
        'steps': structure_wegdeel,
    })
    assert df.loc[0, 'categorie'] == 'fiets'
    assert df.loc[1, 'categorie'] == 'parkeren'
    # begroeidterreindeel-feature blijft ongemoeid door wegdeel-regels
    assert df.loc[2, 'categorie'] is None


def test_pas_categorisatie_toe_else_regel_vult_niet_gematchte_rijen():
    df = _lege_df_met_kolommen()
    laag_met_else = {
        'feature_layer': 'wegdeel',
        'steps': [
            {'column': 'bgt-functie',
             'operator': 'if',
             'type': 'categorie',
             'from': ['fietspad'],
             'to': 'fiets'},
            {'column': 'bgt-functie',
             'operator': 'else',
             'type': 'categorie',
             'to': 'onbekend'},
        ],
    }
    df = pas_categorisatie_toe(df, laag_met_else)
    assert df.loc[0, 'categorie'] == 'fiets'
    assert df.loc[1, 'categorie'] == 'onbekend'  # else-vulling
    assert df.loc[2, 'categorie'] is None  # andere featurelaag


def test_structure_bevat_alle_zes_bgt_lagen():
    lagen = {laag['feature_layer'] for laag in structure}
    assert lagen == {
        'begroeidterreindeel',
        'onbegroeidterreindeel',
        'ondersteunendwaterdeel',
        'ondersteunendwegdeel',
        'waterdeel',
        'wegdeel',
    }

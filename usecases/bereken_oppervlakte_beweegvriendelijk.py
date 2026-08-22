"""Use case: bereken per buurt de oppervlakte-verdeling van BGT-features
naar categorieën (auto, fiets, groen, water, spelen, buitensport, etc.)
en aggregeer naar rec_features die aangeven hoeveel ruimte
beweegvriendelijk is.

De structure-tabellen bovenaan bepalen hoe elke BGT-feature wordt
gecategoriseerd. De ratio's per buurt worden berekend met
``unary_union`` zodat overlappende features (bijv. wegdeel-parkeervlak
over onbegroeidterreindeel-verharding) niet dubbel tellen.
"""
import logging
from typing import Any, Iterable, Optional

import geopandas as gpd
import pandas as pd
from shapely import errors as se
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from domein.bgt_categorisatie import pas_categorisatie_toe, structure
from domein.entiteiten import Buurt
from usecases.initialiseer_data import load_and_initialise_gemeente_data

logger = logging.getLogger(__name__)


def _bevat_punt(df: gpd.GeoDataFrame, punten: Optional[gpd.GeoDataFrame]) -> pd.Series:
    """Retourneer per feature in ``df`` een bool: bevat de polygoon
    minstens één van de punten in ``punten``? Bij ``None`` of een lege
    puntenset overal ``False``."""
    if punten is None or len(punten) == 0:
        return pd.Series(False, index=df.index)
    return df['geometry'].apply(lambda poly: punten.within(poly).any())


def feature_engineering(
    df: gpd.GeoDataFrame,
    df_speelplekken: Optional[gpd.GeoDataFrame],
    df_buitensporten: Optional[gpd.GeoDataFrame],
    structure: list = structure,
) -> gpd.GeoDataFrame:
    """Voeg per BGT-feature de kolommen ``categorie``, ``subcategorie``,
    ``speelplekken`` en ``buitensporten`` toe."""
    df['speelplekken'] = _bevat_punt(df, df_speelplekken)
    df['buitensporten'] = _bevat_punt(df, df_buitensporten)
    for laag_regels in structure:
        df = pas_categorisatie_toe(df, laag_regels)
    return df

recoded_features = {
    'rec_auto': ['auto', 'parkeren', 'verkeer'],
    'rec_actief_transport': ['fiets', 'voetganger'],
    'rec_spelen': ['groen_spelen', 'overig_spelen', 'buitengebied_spelen'],
    'rec_buitensport': ['groen_buitensport', 'overig_buitensport', 'buitengebied_buitensport'],
    'rec_groen_blauw': ['groen', 'groen_groenblauw', 'water', 'buitengebied', 'buitengebied_natuur'],
    'rec_overig': ['overig_verharding', 'gemengd'],
    'rec_OV': ['OV']
}


def _union_area(geometries: Iterable[BaseGeometry]) -> float:
    """Oppervlak van de union van alle geometrieën, waarbij overlap
    tussen features maar één keer wordt geteld."""
    geoms = [g for g in geometries if g is not None and not g.is_empty]
    if not geoms:
        return 0.0
    return unary_union(geoms).area


def get_stats_per_geometry(
    geometry: BaseGeometry,
    df: gpd.GeoDataFrame,
    exclude_subcategories: list = ['agrarisch'],
    recoded_features: dict = recoded_features,
) -> Optional[pd.DataFrame]:
    """Bereken de oppervlakte-verdeling van BGT-features binnen de
    gegeven geometrie (typisch een buurt). Retourneert een DataFrame met
    per (categorie, subcategorie) een absolute oppervlakte en aandeel,
    plus vergelijkbare rijen per rec_feature.

    Retourneert ``None`` wanneer de geometrie niet valide is voor
    clipping."""
    try:
        clipped_gdf = gpd.clip(df, gpd.GeoSeries([geometry], crs=df.crs))
    except se.GEOSException as error:
        logger.warning("GEOS-exceptie bij clippen van buurt-geometrie: %s", error)
        return None

    clipped_gdf = clipped_gdf.copy()
    clipped_gdf.loc[clipped_gdf.subcategorie.isnull(), 'subcategorie'] = ""
    clipped_gdf['subcategorie'] = clipped_gdf['subcategorie'].apply(
        lambda x: x.strip() if isinstance(x, str) else x
    )

    # Filter agrarisch (en andere excluded) volledig uit: de
    # union-benadering kan niet met area=0 werken zoals de oude
    # sum-benadering.
    non_excluded = clipped_gdf.loc[
        ~clipped_gdf.subcategorie.isin(exclude_subcategories)
    ].copy()

    # Per (categorie, subcategorie) de union-oppervlakte; dubbeltellingen
    # tussen features van dezelfde class gaan weg.
    summary_df = (
        non_excluded.groupby(['categorie', 'subcategorie'])['geometry']
        .apply(_union_area)
        .reset_index(name='area')
    )

    # total_area moet de union zijn over álle non-excluded features,
    # niet de som van per-class-unions, want die telt overlap TUSSEN
    # classes alsnog dubbel.
    total_area = _union_area(non_excluded['geometry'])
    summary_df['relative'] = (
        summary_df['area'] / total_area if total_area > 0 else 0.0
    )

    summary_df['totaal_categorie'] = summary_df['categorie']
    summary_df.loc[summary_df.subcategorie != "", 'totaal_categorie'] = (
        summary_df['categorie'] + "_" + summary_df['subcategorie']
    )
    result = summary_df[['totaal_categorie', 'area', 'relative']]

    # Per rec_feature: union over alle constituerende (cat, subcat) samen,
    # zodat overlap tussen classes binnen één rec_feature ook 1× telt.
    non_excluded['totaal_categorie'] = non_excluded['categorie']
    mask = non_excluded['subcategorie'] != ""
    non_excluded.loc[mask, 'totaal_categorie'] = (
        non_excluded['categorie'] + "_" + non_excluded['subcategorie']
    )
    totaal_to_rec = {
        feat: rec for rec, feats in recoded_features.items() for feat in feats
    }
    non_excluded['rec_feature'] = non_excluded['totaal_categorie'].map(totaal_to_rec)
    rec_summary = (
        non_excluded.dropna(subset=['rec_feature'])
        .groupby('rec_feature')['geometry']
        .apply(_union_area)
        .reset_index(name='area')
    )
    rec_summary['relative'] = (
        rec_summary['area'] / total_area if total_area > 0 else 0.0
    )
    rec_summary = rec_summary.rename(columns={'rec_feature': 'totaal_categorie'})

    return pd.concat(
        [result, rec_summary[['totaal_categorie', 'area', 'relative']]],
        ignore_index=True,
    )

def get_buurt_data(buurten: list[Buurt], df: gpd.GeoDataFrame) -> list[pd.DataFrame]:
    """Bereken voor elke buurt de oppervlakte-verdeling van
    BGT-features. Retourneert een lijst van breed-getransformeerde
    DataFrames (één rij per buurt, kolommen per categorie)."""
    out = []
    for buurt in buurten:
        stats_df = get_stats_per_geometry(buurt.geometrie, df)
        if stats_df is None:
            # buurt-geometrie was niet valide voor clipping
            continue

        stats_df['buurtcode'] = buurt.code
        stats_df = stats_df.pivot(index='buurtcode', columns='totaal_categorie', values=['area', 'relative'])
        stats_df['buurtnaam'] = buurt.naam
        stats_df['buurtcode'] = buurt.code
        stats_df['wijkcode'] = buurt.wijkcode
        stats_df['gemeentecode'] = buurt.gemeentecode
        out.append(stats_df)
    return out


def transform_buurt_data(buurten: list[Buurt], df: gpd.GeoDataFrame) -> pd.DataFrame:
    """Combineer per-buurt statistieken tot één long-format DataFrame
    met kolom ``stat`` (``area`` of ``relative``) en per categorie een
    kolom met de waarde."""
    stats_df = get_buurt_data(buurten, df)
    combined_df = pd.concat(stats_df)

    def create_area_and_relative_df(stat: str, combined_df: pd.DataFrame) -> pd.DataFrame:
        temp_df = combined_df[stat].copy()
        temp_df['stat'] = stat
        temp_df['buurtnaam'] = combined_df['buurtnaam']
        temp_df['wijkcode'] = combined_df['wijkcode']
        temp_df['gemeentecode'] = combined_df['gemeentecode']
        return temp_df
    return pd.concat([create_area_and_relative_df(stat, combined_df) for stat in ['area', 'relative']]).reset_index()


features = ['auto',
       'fiets', 'groen', 'groen_buitensport', 'groen_groenblauw',
       'groen_spelen', 'overig_buitensport', 'overig_spelen',
       'overig_verharding', 'parkeren', 'verkeer', 'voetganger', 'water', 'OV',
       'buitengebied_buitensport', 'gemengd', 'buitengebied', 'buitengebied_spelen', 'buitengebied_agrarisch', 'buitengebied_natuur']


def bereken_beweegvriendelijkheid(
    gemeente_code: str,
    **adapter_kwargs: Any,
) -> pd.DataFrame:
    """Bereken de oppervlakte-verdeling van beweegvriendelijke ruimte
    per buurt voor de gegeven gemeente.

    :param gemeente_code: gemeentecode inclusief prefix (bijv. "GM1680").
    :param adapter_kwargs: extra keyword-argumenten die worden
        doorgegeven aan ``load_and_initialise_gemeente_data`` om
        adapters te vervangen (dependency injection voor tests).
    :returns: DataFrame met per buurt twee rijen (``stat == 'area'`` en
        ``stat == 'relative'``) en per categorie en rec_feature een
        kolom.
    """
    gemeente_data = load_and_initialise_gemeente_data(gemeente_code, **adapter_kwargs)
    df = feature_engineering(
        gemeente_data['bgt_df'],
        gemeente_data['speelplekken_df'],
        gemeente_data['buitensporten_df'],
    )
    df = transform_buurt_data(gemeente_data['buurten'], df)

    for feature in list(features) + list(recoded_features.keys()):
        if feature in df.columns:
            df.loc[df[feature].isnull(), feature] = 0
        else:
            df[feature] = 0

    df['rec_total'] = df[list(recoded_features.keys())].sum(axis=1)
    df['rec_inactief'] = df['rec_auto'] + df['rec_overig']
    df['rec_actief'] = df['rec_actief_transport'] + df['rec_spelen']

    return df


if __name__ == "__main__":
    df = bereken_beweegvriendelijkheid("GM1680")
    print(df.loc[df['stat'] == 'area', ['buurtnaam', 'rec_total', 'rec_actief']].head(20))

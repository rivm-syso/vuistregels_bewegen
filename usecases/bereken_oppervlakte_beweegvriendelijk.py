from usecases.initialiseer_data import load_and_initialise_gemeente_data
import geopandas as gpd
import pandas as pd
from shapely import errors as se
from shapely.ops import unary_union

structure_begroeidterreindeel = [
    {'column': 'bgt-fysiekVoorkomen',
     'operator': 'if',
     'type': 'categorie',
     'from': ['groenvoorziening'],
     'to': 'groen'},
    {'column': 'bgt-fysiekVoorkomen',
     'operator': 'if',
     'type': 'categorie',
     'from': ['struiken'],
     'to': 'groen'},
    {'column': 'bgt-fysiekVoorkomen',
     'operator': 'else',
     'type': 'categorie',
     'to': 'buitengebied'},
    {'column': 'bgt-fysiekVoorkomen',
     'operator': 'if',
     'type': 'subcategorie',
     'from': ['boomteelt', 'bouwland', 'fruitteelt', 'grasland agrarisch'],
     'to': 'agragrisch'},
    {'column': 'bgt-fysiekVoorkomen',
     'operator': 'if',
     'type': 'subcategorie',
     'from': ['gemengd bos', 'houtwal', 'loofbos', 'moeras', 'naaldbos', 'rietland', 'grasland overig'],
     'to': 'natuur'},
    {'column': 'speelplekken',
     'operator': 'if',
     'type': 'subcategorie',
     'from': [True],
     'to': 'spelen'},
    {'column': 'buitensporten',
     'operator': 'if',
     'type': 'subcategorie',
     'from': [True],
     'to': 'buitensport'}
]

structure_onbegroeidterreindeel = [
    {'column': 'bgt-fysiekVoorkomen',
     'operator': 'else',
     'type': 'categorie',
     'to': 'overig'},
    {'column': 'speelplekken',
     'operator': 'if',
     'type': 'subcategorie',
     'from': [True],
     'to': 'spelen'},
    {'column': 'buitensporten',
     'operator': 'if',
     'type': 'subcategorie',
     'from': [True],
     'to': 'buitensport'},
    {'column': 'bgt-fysiekVoorkomen',
     'operator': 'else',
     'type': 'subcategorie',
     'to': 'verharding'}
]

structure_ondersteunendwaterdeel = [
    {'column': 'bgt-fysiekVoorkomen',
     'operator': 'else',
     'type': 'categorie',
     'to': 'groen'},
    {'column': 'bgt-fysiekVoorkomen',
     'operator': 'else',
     'type': 'subcategorie',
     'to': 'groenblauw'}
]

structure_ondersteunendwegdeel = [
    {'column': 'bgt-fysiekVoorkomen',
     'operator': 'if',
     'type': 'categorie',
     'from': ['groenvoorziening'],
     'to': 'groen'},
    {'column': 'bgt-fysiekVoorkomen',
     'operator': 'else',
     'type': 'categorie',
     'to': 'verkeer'}
]


structure_waterdeel = [
    {'column': 'bgt-type',
     'operator': 'if',
     'type': 'categorie',
     'from': ['greppel, droge sloot'],
     'to': 'groen'},
    {'column': 'bgt-type',
     'operator': 'else',
     'type': 'categorie',
     'to': 'water'},
    {'column': 'bgt-type',
     'operator': 'if',
     'type': 'subcategorie',
     'from': ['greppel, droge sloot'],
     'to': 'groenblauw'}
]

structure_wegdeel = [
    {'column': 'bgt-functie',
     'operator': 'if',
     'type': 'categorie',
     'from': ['fietspad'],
     'to': 'fiets'},
    {'column': 'bgt-functie',
     'operator': 'if',
     'type': 'categorie',
     'from': ['inrit', 'rijbaan autosnelweg', 'rijbaan autoweg', 'rijbaan lokale weg', 'rijbaan regionale weg'],
     'to': 'auto'},
    {'column': 'bgt-functie',
     'operator': 'if',
     'type': 'categorie',
     'from': ['OV-baan', 'spoorbaan'],
     'to': 'OV'},
     {'column': 'bgt-functie',
     'operator': 'if',
     'type': 'categorie',
     'from': ['overweg', 'woonerf'],
     'to': 'gemengd'},
        {'column': 'bgt-functie',
     'operator': 'if',
     'type': 'categorie',
     'from': ['parkeervlak'],
     'to': 'parkeren'},
        {'column': 'bgt-functie',
     'operator': 'if',
     'type': 'categorie',
     'from': ['ruiterpad', 'voetgangersgebied', 'voetpad op trap', 'voetpad'],
     'to': 'voetganger'},
]

structure = [
    {'feature_layer': 'begroeidterreindeel', 'steps': structure_begroeidterreindeel},
    {'feature_layer': 'onbegroeidterreindeel', 'steps': structure_onbegroeidterreindeel},
    {'feature_layer': 'ondersteunendwaterdeel', 'steps': structure_ondersteunendwaterdeel},
    {'feature_layer': 'ondersteunendwegdeel', 'steps': structure_ondersteunendwegdeel},
    {'feature_layer': 'waterdeel', 'steps': structure_waterdeel},
    {'feature_layer': 'wegdeel', 'steps': structure_wegdeel},
]

def _casewhen(df, structure):
    feature_layer = structure['feature_layer']
    for step in structure['steps']:
        outcome_col = step['type']
        input_col = step['column']
        if step['operator'] == "if":
            df.loc[df[input_col].isin(step['from']) & df.file.isin([feature_layer]), outcome_col] = step['to']
        if step['operator'] == "else":
            df.loc[df[outcome_col].isnull() & df.file.isin([feature_layer]), outcome_col] = step['to']
    return df

def feature_engineering(df, df_speelplekken, df_buitensporten, structure=structure):
    def check_presence(polygon, df_points=df_speelplekken):
        return df_points.within(polygon).any()
    try:
        df['speelplekken'] = df['geometry'].apply(lambda poly: check_presence(poly))
    except:
        df['speelplekken'] = False

    if df_buitensporten is not None:
        try:
            df['buitensporten'] = df['geometry'].apply(lambda poly: check_presence(poly, df_points=df_buitensporten))
        except:
            df['buitensporten'] = False
    else:
        df['buitensporten'] = False
    for feature in structure:
        df = _casewhen(df, feature)
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


def _union_area(geometries):
    """Oppervlak van de union van alle features — overlap telt 1×."""
    geoms = [g for g in geometries if g is not None and not g.is_empty]
    if not geoms:
        return 0.0
    return unary_union(geoms).area


def get_stats_per_geometry(geometry, df, exclude_subcategories=['agragrisch'],
                           recoded_features=recoded_features):
    try:
        clipped_gdf = gpd.clip(df, gpd.GeoSeries(geometry))
    except se.GEOSException as error:
        print("WARNING WARNING: GEOS_EXCEPTION DID NOT PARSE")
        return None

    clipped_gdf = clipped_gdf.copy()
    clipped_gdf.loc[clipped_gdf.subcategorie.isnull(), 'subcategorie'] = ""
    clipped_gdf['subcategorie'] = clipped_gdf['subcategorie'].apply(
        lambda x: x.strip() if isinstance(x, str) else x
    )

    # Filter agragrisch (en andere excluded) volledig uit — union-benadering
    # kan niet met area=0 werken zoals de oude sum-benadering.
    non_excluded = clipped_gdf.loc[
        ~clipped_gdf.subcategorie.isin(exclude_subcategories)
    ].copy()

    # Per (categorie, subcategorie) de union-oppervlakte — dubbeltellingen
    # tussen features van dezelfde class gaan weg.
    summary_df = (
        non_excluded.groupby(['categorie', 'subcategorie'])['geometry']
        .apply(_union_area)
        .reset_index(name='area')
    )

    # total_area moet de union zijn over álle non-excluded features — niet
    # de som van per-class-unions, want die telt overlap TUSSEN classes
    # alsnog dubbel.
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

def get_buurt_data(df_bw, df):
    out = []
    for buurt in df_bw.iterrows():
        stats_df = get_stats_per_geometry(buurt[1]['geometry'], df)
        if stats_df is None:
            #this happens when geometry is invalid
            continue

        #bla = pd.melt(bla, id_vars=['buurtcode', 'buurtnaam', 'wijkcode', 'gemeentecode'], value_vars=['area', 'relative'])
        stats_df['buurtcode'] = buurt[1]['buurtcode']
        stats_df = stats_df.pivot(index='buurtcode', columns='totaal_categorie', values=['area', 'relative'])
        stats_df['buurtnaam'] = buurt[1]['buurtnaam']
        stats_df['buurtcode'] = buurt[1]['buurtcode']
        stats_df['wijkcode'] = buurt[1]['wijkcode']
        stats_df['gemeentecode'] = buurt[1]['gemeentecode']
        out.append(stats_df)
    return out

def transform_buurt_data(df_bw, df):
    stats_df = get_buurt_data(df_bw, df)
    combined_df = pd.concat(stats_df)
    def create_area_and_relative_df(stat, combined_df):
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
       'buitengebied_buitensport', 'gemengd', 'buitengebied', 'buitengebied_spelen', 'buitengebied_agragrisch', 'buitengebied_natuur']


def bereken_beweegvriendelijkheid(gemeente_code):
    """Bereken de oppervlakte-verdeling van beweegvriendelijke ruimte
    per buurt voor de gegeven gemeente. Retourneert een DataFrame met
    per buurt zowel absolute m² (`stat == 'area'`) als aandelen
    (`stat == 'relative'`) voor alle categorieën en rec_features."""
    gemeente_data = load_and_initialise_gemeente_data(gemeente_code)
    df = feature_engineering(
        gemeente_data['bgt_df'],
        gemeente_data['speelplekken_df'],
        gemeente_data['buitensporten_df'],
    )
    df = transform_buurt_data(gemeente_data['buurt_geometrie_df'], df)

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

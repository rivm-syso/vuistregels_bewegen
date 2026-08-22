"""Regels voor het categoriseren van BGT-features naar categorie en
subcategorie (auto, fiets, groen, verharding, spelen, etc.).

Elke ``structure_*`` is een lijst van if/else-stappen voor één
BGT-featurelaag. ``structure`` bundelt alle featurelagen.
``pas_categorisatie_toe`` past de regels toe op een GeoDataFrame."""
import geopandas as gpd

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
     'to': 'agrarisch'},
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
     'to': 'buitensport'},
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
     'to': 'verharding'},
]

structure_ondersteunendwaterdeel = [
    {'column': 'bgt-fysiekVoorkomen',
     'operator': 'else',
     'type': 'categorie',
     'to': 'groen'},
    {'column': 'bgt-fysiekVoorkomen',
     'operator': 'else',
     'type': 'subcategorie',
     'to': 'groenblauw'},
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
     'to': 'verkeer'},
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
     'to': 'groenblauw'},
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


def pas_categorisatie_toe(df: gpd.GeoDataFrame, laag_regels: dict) -> gpd.GeoDataFrame:
    """Voeg categorie- en subcategoriekolommen toe aan ``df`` op basis
    van de regels voor één BGT-featurelaag.

    :param df: GeoDataFrame met BGT-features, met kolom ``file`` die
        de featurelaag aangeeft.
    :param laag_regels: dict met ``feature_layer`` (laagnaam) en
        ``steps`` (lijst van if/else-stappen).
    """
    feature_layer = laag_regels['feature_layer']
    for step in laag_regels['steps']:
        outcome_col = step['type']
        input_col = step['column']
        if step['operator'] == "if":
            df.loc[df[input_col].isin(step['from']) & df.file.isin([feature_layer]), outcome_col] = step['to']
        if step['operator'] == "else":
            df.loc[df[outcome_col].isnull() & df.file.isin([feature_layer]), outcome_col] = step['to']
    return df

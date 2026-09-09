"""Domein-entiteiten voor de vuistregels-repo.

Kleine, immutable objecten die het domein modelleren (gemeenten,
buurten). Grote feature-verzamelingen zoals BGT-vlakken blijven
GeoDataFrames omdat pandas/geopandas de werkende currency zijn voor die
soort data.
"""
from dataclasses import dataclass
from typing import Optional

from shapely.geometry.base import BaseGeometry


@dataclass(frozen=True)
class Gemeente:
    """Nederlandse gemeente met haar geometrische begrenzing.

    :param code: gemeentecode inclusief prefix (bijv. "GM1680").
    :param naam: officiële gemeentenaam.
    :param provincie: naam van de provincie waarin de gemeente valt.
    :param geometrie: polygoon of multipolygoon in RD-New (EPSG:28992).
    """
    code: str
    naam: str
    provincie: Optional[str]
    geometrie: BaseGeometry


@dataclass(frozen=True)
class BeweegvriendelijkheidPerBuurt:
    """Uitkomst van een beweegvriendelijkheidsberekening voor één
    buurt.

    :param buurt: de buurt waarop deze uitkomst betrekking heeft.
    :param gemeente: de gemeente waarin de buurt valt (bevat naam
        en provincie).
    :param absoluut_m2: per (rec_)feature het aandeel in m². Bevat
        zowel raw categorieen (bijv. ``'groen'``, ``'fiets'``) als
        aggregaties (``'rec_auto'``, ``'rec_actief_transport'``,
        ``'rec_total'``, ``'rec_inactief'``, ``'rec_actief'``).
    :param relatief_aandeel: dezelfde keys als ``absoluut_m2``, maar
        als aandeel (tussen 0 en 1) van de totale gebiedsoppervlakte.
    """
    buurt: "Buurt"
    gemeente: "Gemeente"
    absoluut_m2: dict
    relatief_aandeel: dict


@dataclass(frozen=True)
class Buurt:
    """CBS-buurt binnen een gemeente.

    :param code: CBS-buurtcode (bijv. "BU16800000").
    :param naam: buurtnaam zoals in de CBS-bestanden.
    :param wijkcode: CBS-wijkcode waaronder de buurt valt.
    :param gemeentecode: gemeentecode inclusief prefix.
    :param geometrie: polygoon of multipolygoon in RD-New (EPSG:28992).
    """
    code: str
    naam: str
    wijkcode: str
    gemeentecode: str
    geometrie: BaseGeometry

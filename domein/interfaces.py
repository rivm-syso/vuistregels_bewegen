"""Interfaces (Protocols) tussen use cases en adapters. Kleine,
gefinaliseerde objecten (Gemeente, Buurt) worden geretourneerd als
domein-entiteiten. Grote featureverzamelingen blijven GeoDataFrames.
"""
from typing import Optional, Protocol, runtime_checkable

from geopandas import GeoDataFrame

from .entiteiten import Buurt, Gemeente


@runtime_checkable
class BestuurlijkeGrenzenInterface(Protocol):
    """Bron van gemeente- en buurtgrenzen."""

    def get_gemeente(self) -> Gemeente:
        """Haal de gemeente op waarvoor deze adapter is geïnstantieerd."""
        ...

    def get_buurten(self) -> list[Buurt]:
        """Haal alle buurten binnen deze gemeente op."""
        ...


@runtime_checkable
class BgtInterface(Protocol):
    """Bron van BGT-features (verharding, groen, water, wegen, en
    overige terreindelen) voor één gemeente."""

    def get_features(self) -> GeoDataFrame:
        """Retourneer de gefilterde BGT-features voor deze gemeente.

        Verwachte kolommen in de GeoDataFrame:
        - ``geometry``: polygoon in RD-New (EPSG:28992).
        - ``file``: naam van de BGT-featurelaag (bijv. ``wegdeel``).
        - ``bgt-fysiekVoorkomen``, ``bgt-functie``, ``bgt-type``:
          categoriseerbare attributen (afhankelijk van de laag).
        - ``plus-type``: optionele plus-aanduiding (bijv.
          ``speelvoorziening``).

        Alleen actuele features (``eindRegistratie`` leeg) en zonder
        de uitgesloten groepen (straatmeubilair, erven) horen hier in
        te zitten.
        """
        ...


@runtime_checkable
class SpeelplekkenInterface(Protocol):
    """Bron van speelpleklocaties voor één gemeente."""

    def get_alle(self) -> GeoDataFrame:
        """Retourneer de speelpleklocaties binnen deze gemeente.

        Verwachte kolommen:
        - ``geometry``: puntgeometrie in RD-New (EPSG:28992).
        - ``naam``: korte beschrijving of herkomst (bijv. ``from_bgt``).
        """
        ...


@runtime_checkable
class BuitensportenInterface(Protocol):
    """Bron van buitensport-voorzieningen (Mulier DSA-portaal) voor
    één gemeente."""

    def get_buitensporten(self) -> Optional[GeoDataFrame]:
        """Retourneer de buitensport-voorzieningen voor deze gemeente,
        of ``None`` wanneer geen bron beschikbaar is.

        Verwachte kolommen (indien niet-None):
        - ``geometry``: puntgeometrie in RD-New (EPSG:28992).
        - ``voorziening_id``: identifier van de voorziening in DSA.
        """
        ...

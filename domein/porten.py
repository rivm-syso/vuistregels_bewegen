"""Poorten (Protocols) die de interface tussen use cases en adapters
formaliseren. Kleine, gefinaliseerde objecten (Gemeente, Buurt) worden
geretourneerd als domein-entiteiten. Grote featureverzamelingen blijven
GeoDataFrames.
"""
from typing import Optional, Protocol, runtime_checkable

from geopandas import GeoDataFrame
from shapely.geometry.base import BaseGeometry

from .entiteiten import Buurt, Gemeente


@runtime_checkable
class BestuurlijkeGrenzenPoort(Protocol):
    """Bron van gemeente- en buurtgrenzen."""

    def get_gemeente(self) -> Gemeente:
        """Haal de gemeente op waarvoor deze adapter is geïnstantieerd."""
        ...

    def get_buurten(self) -> list[Buurt]:
        """Haal alle buurten binnen deze gemeente op."""
        ...


@runtime_checkable
class BgtPoort(Protocol):
    """Bron van BGT-features (verharding, groen, water, wegen, etc.)
    voor één gemeente."""

    def get_features(self) -> GeoDataFrame:
        """Retourneer de gefilterde en gecategoriseerde BGT-features
        voor deze gemeente."""
        ...


@runtime_checkable
class SpeelplekkenPoort(Protocol):
    """Bron van speelpleklocaties (samengevoegd uit Buitenspeelkaart,
    OSM en BGT)."""

    def get_alle(self) -> GeoDataFrame:
        """Retourneer de speelpleklocaties binnen deze gemeente."""
        ...


@runtime_checkable
class BuitensportenPoort(Protocol):
    """Bron van buitensport-voorzieningen (Mulier DSA-portaal)."""

    def get_buitensporten(self) -> Optional[GeoDataFrame]:
        """Retourneer de buitensport-voorzieningen voor deze gemeente,
        of ``None`` wanneer geen bron beschikbaar is."""
        ...

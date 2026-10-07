"""Tests die verifiëren dat de concrete adapters de Protocols
implementeren die de use case verwacht. Gebruikt ``issubclass`` op de
``@runtime_checkable``-Protocols, zodat er geen instances (en dus geen
downloads of externe I/O) nodig zijn."""
from adapters.bestuurlijke_grenzen import BestuurlijkeGrenzen
from adapters.bgt import BGT
from adapters.dsa import DSA
from adapters.speelplekken import Speelplekken
from domein.interfaces import (
    BestuurlijkeGrenzenInterface,
    BgtInterface,
    BuitensportenInterface,
    SpeelplekkenInterface,
)


def test_bestuurlijke_grenzen_voldoet_aan_interface():
    assert issubclass(BestuurlijkeGrenzen, BestuurlijkeGrenzenInterface)


def test_bgt_voldoet_aan_interface():
    assert issubclass(BGT, BgtInterface)


def test_speelplekken_voldoet_aan_interface():
    assert issubclass(Speelplekken, SpeelplekkenInterface)


def test_dsa_voldoet_aan_interface():
    assert issubclass(DSA, BuitensportenInterface)

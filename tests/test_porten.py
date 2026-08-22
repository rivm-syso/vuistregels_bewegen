"""Tests die verifiëren dat de concrete adapters de Protocols
implementeren die de use case verwacht. Gebruikt ``issubclass`` op de
``@runtime_checkable``-Protocols, zodat er geen instances (en dus geen
downloads of externe I/O) nodig zijn."""
from adapters.bestuurlijke_grenzen import BestuurlijkeGrenzen
from adapters.bgt import BGT
from adapters.dsa import DSA
from adapters.speelplekken import Speelplekken
from domein.porten import (
    BestuurlijkeGrenzenPoort,
    BgtPoort,
    BuitensportenPoort,
    SpeelplekkenPoort,
)


def test_bestuurlijke_grenzen_voldoet_aan_poort():
    assert issubclass(BestuurlijkeGrenzen, BestuurlijkeGrenzenPoort)


def test_bgt_voldoet_aan_poort():
    assert issubclass(BGT, BgtPoort)


def test_speelplekken_voldoet_aan_poort():
    assert issubclass(Speelplekken, SpeelplekkenPoort)


def test_dsa_voldoet_aan_poort():
    assert issubclass(DSA, BuitensportenPoort)

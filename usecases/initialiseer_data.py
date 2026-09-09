"""Orchestreert de adapters die de ruwe brondata leveren voor een
gemeente. De retourwaarde bundelt de losse databronnen zodat use cases
er niet zelf naar hoeven te reiken.

Adapter-klassen kunnen via de parameters worden vervangen (dependency
injection); handig voor tests met fakes of alternatieve bronnen.
"""
from typing import Optional, Type

from adapters.bestuurlijke_grenzen import BestuurlijkeGrenzen
from adapters.bgt import BGT
from adapters.speelplekken import Speelplekken
from domein.porten import (
    BestuurlijkeGrenzenPoort,
    BgtPoort,
    BuitensportenPoort,
    SpeelplekkenPoort,
)


def load_and_initialise_gemeente_data(
    gemeente_code: str,
    grenzen_klasse: Type[BestuurlijkeGrenzenPoort] = BestuurlijkeGrenzen,
    bgt_klasse: Type[BgtPoort] = BGT,
    speelplekken_klasse: Type[SpeelplekkenPoort] = Speelplekken,
    buitensporten_klasse: Optional[Type[BuitensportenPoort]] = None,
    toestemming_buitenspeelkaart: bool = False,
) -> dict:
    """Bundel de gemeente-brondata voor de gegeven gemeentecode.

    :param gemeente_code: gemeentecode inclusief prefix (bijv. "GM1680").
    :param grenzen_klasse: adapter-klasse voor bestuurlijke grenzen.
    :param bgt_klasse: adapter-klasse voor BGT-features.
    :param speelplekken_klasse: adapter-klasse voor speelpleklocaties.
    :param buitensporten_klasse: adapter-klasse voor buitensporten. Bij
        ``None`` wordt geen buitensport-data opgehaald.
    :param toestemming_buitenspeelkaart: doorgegeven aan de
        speelplekken-adapter. Bij ``False`` (standaard) wordt de
        Buitenspeelkaart-bron overgeslagen; OSM- en
        BGT-speelvoorzieningen blijven altijd meegenomen.
    :returns: dict met ``gemeente``, ``buurten``, ``bgt_df``,
        ``speelplekken_df``, ``buitensporten_df``.
    """
    bg_instance = grenzen_klasse(gemeente_code=gemeente_code)
    gemeente = bg_instance.get_gemeente()
    buurten = bg_instance.get_buurten()

    bgt_gemeente = bgt_klasse(gemeente_code, gemeente.geometrie)
    bgt_df = bgt_gemeente.get_features()

    sp = speelplekken_klasse(
        gemeente_code,
        gemeente.geometrie,
        toestemming_buitenspeelkaart=toestemming_buitenspeelkaart,
    )
    speelplekken_df = sp.get_alle()

    buitensporten_df = None
    if buitensporten_klasse is not None:
        buitensporten_df = buitensporten_klasse(gemeente_code).get_buitensporten()

    return {
        'gemeente': gemeente,
        'buurten': buurten,
        'bgt_df': bgt_df,
        'speelplekken_df': speelplekken_df,
        'buitensporten_df': buitensporten_df,
    }

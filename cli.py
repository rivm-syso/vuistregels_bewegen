"""Command-line interface voor de vuistregels-repo.

Voorbeelden::

    python -m cli bereken beweegvriendelijk GM1680
    vuistregels bereken beweegvriendelijk GM1680  # na `pip install -e .`
    vuistregels bereken beweegvriendelijk GM1680 GM0518 --workers 4 --uit resultaat.csv
    vuistregels bereken beweegvriendelijk --gemeenten-csv gemeenten.csv --uit resultaat.csv
"""
import argparse
import logging
import os
import sys
from typing import Optional

import pandas as pd

from usecases.bereken_oppervlakte_beweegvriendelijk import (
    _default_toestemming_buitenspeelkaart,
    bereken_beweegvriendelijkheid_voor_gemeenten,
    naar_dataframe_beperkt,
)


def _cmd_bereken_beweegvriendelijk(args: argparse.Namespace) -> None:
    """Voer de use case uit voor een of meer gemeenten en toon of
    schrijf het resultaat weg."""
    codes = _verzamel_gemeente_codes(args.gemeente_codes, args.gemeenten_csv)
    toestemming = _resolve_toestemming_buitenspeelkaart(args.toestemming_buitenspeelkaart)
    _resolve_dsa_credentials()
    resultaten = bereken_beweegvriendelijkheid_voor_gemeenten(
        codes,
        workers=args.workers,
        toestemming_buitenspeelkaart=toestemming,
    )
    df = naar_dataframe_beperkt(resultaten)
    if args.uit:
        if args.uit.endswith(".parquet"):
            df.to_parquet(args.uit)
        else:
            df.to_csv(args.uit, index=False)
        print(f"Resultaat opgeslagen naar {args.uit} ({len(resultaten)} buurten uit {len(codes)} gemeente(n))")
    else:
        print(df.head(20).to_string(index=False))


def _resolve_toestemming_buitenspeelkaart(cli_waarde: Optional[bool]) -> bool:
    """Bepaal of Buitenspeelkaart gebruikt mag worden. Precedentie:

    1. Expliciete CLI-flag (``--toestemming-buitenspeelkaart`` of
       ``--no-toestemming-buitenspeelkaart``) wint altijd.
    2. Anders de env-var ``TOESTEMMING_BUITENSPEELKAART`` uit ``.env``.
    3. Anders, als stdin een TTY is, interactieve prompt met default
       nee.
    4. Anders: nee, met logmelding.
    """
    if cli_waarde is not None:
        return cli_waarde
    if os.getenv("TOESTEMMING_BUITENSPEELKAART") is not None:
        return _default_toestemming_buitenspeelkaart()
    if not sys.stdin.isatty():
        print(
            "INFO: TOESTEMMING_BUITENSPEELKAART niet gezet; "
            "Buitenspeelkaart-data wordt niet meegenomen.",
            file=sys.stderr,
        )
        return False
    antwoord = input(
        "Heb je toestemming van Speelplan om Buitenspeelkaart-data te gebruiken? "
        "(ja/nee, standaard nee): "
    ).strip().lower()
    return antwoord in ("ja", "j", "yes", "y", "true", "1")


def _resolve_dsa_credentials() -> None:
    """Als ``DSA_KEY`` en ``DSA_MAIL`` ontbreken: meld dat DSA wordt
    overgeslagen, en bied in interactieve shells aan ze alsnog in te
    vullen voor deze run. De use case leest ``os.environ`` runtime, dus
    hier gezette waarden worden automatisch opgepakt."""
    if os.getenv("DSA_KEY") and os.getenv("DSA_MAIL"):
        return
    if not sys.stdin.isatty():
        print(
            "INFO: DSA_KEY/DSA_MAIL ontbreken; "
            "DSA-buitensporten worden niet meegenomen.",
            file=sys.stderr,
        )
        return
    print(
        "DSA_KEY en DSA_MAIL ontbreken in de omgeving. "
        "Zonder deze worden buitensport-voorzieningen uit DSA overgeslagen."
    )
    antwoord = input("Nu invullen voor deze run? (ja/nee, standaard nee): ").strip().lower()
    if antwoord not in ("ja", "j", "yes", "y", "true", "1"):
        print("DSA wordt overgeslagen.")
        return
    key = input("DSA_KEY: ").strip()
    mail = input("DSA_MAIL: ").strip()
    if key and mail:
        os.environ["DSA_KEY"] = key
        os.environ["DSA_MAIL"] = mail
    else:
        print("Lege invoer; DSA wordt overgeslagen.")


def _verzamel_gemeente_codes(positional: list, csv_pad: Optional[str]) -> list[str]:
    """Combineer gemeente-codes uit positional args en optionele CSV
    tot een gededupliceerde lijst met behoud van volgorde."""
    codes = list(positional or [])
    if csv_pad:
        codes.extend(_lees_gemeenten_csv(csv_pad))
    if not codes:
        raise ValueError("geen gemeente-codes opgegeven (positional of via --gemeenten-csv)")
    return list(dict.fromkeys(codes))


def _lees_gemeenten_csv(pad: str) -> list[str]:
    """Lees een CSV met kolom ``gemeente_code`` en retourneer de codes
    als lijst. De separator wordt auto-gedetecteerd."""
    df = pd.read_csv(pad, sep=None, engine="python")
    if "gemeente_code" not in df.columns:
        raise ValueError(
            f"CSV mist kolom 'gemeente_code'. Gevonden kolommen: {list(df.columns)}."
        )
    return [str(c) for c in df["gemeente_code"].tolist()]


def bouw_parser() -> argparse.ArgumentParser:
    """Bouw de argparse-parser met alle subcommando's."""
    parser = argparse.ArgumentParser(
        prog="vuistregels",
        description="Vuistregels voor beweegvriendelijke buitenruimte per gemeente/buurt.",
    )
    subparsers = parser.add_subparsers(dest="commando", required=True)

    bereken = subparsers.add_parser(
        "bereken",
        help="Berekeningen uitvoeren voor een gemeente.",
    )
    bereken_sub = bereken.add_subparsers(dest="berekening", required=True)

    bw = bereken_sub.add_parser(
        "beweegvriendelijk",
        help="Oppervlakte-verdeling van beweegvriendelijke openbare buitenruimte per buurt (voor een of meer gemeenten).",
    )
    bw.add_argument(
        "gemeente_codes",
        nargs="*",
        help="Een of meer gemeentecodes inclusief prefix, bijv. GM1680 GM0518.",
    )
    bw.add_argument(
        "--gemeenten-csv",
        help="Optioneel pad naar CSV met kolom 'gemeente_code'; aanvullend op positional args.",
    )
    bw.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Aantal parallelle workers (standaard: aantal CPU-cores; 1 = serieel).",
    )
    bw.add_argument(
        "--toestemming-buitenspeelkaart",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Expliciet aan- of uitzetten of Buitenspeelkaart-data wordt meegenomen "
             "(--toestemming-buitenspeelkaart / --no-toestemming-buitenspeelkaart). "
             "Zonder flag valt het terug op TOESTEMMING_BUITENSPEELKAART uit .env; "
             "als die ook ontbreekt wordt (bij een TTY) interactief gevraagd en is de default nee. "
             "OSM en BGT-speelvoorzieningen worden altijd meegenomen.",
    )
    bw.add_argument(
        "--uit",
        help="Optioneel pad om resultaat weg te schrijven (.csv of .parquet).",
    )
    bw.set_defaults(func=_cmd_bereken_beweegvriendelijk)

    return parser


def main(argv: Optional[list] = None) -> None:
    """Entry point van de CLI. Parseer argumenten en dispatch naar het
    juiste subcommando."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = bouw_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

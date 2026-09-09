"""Command-line interface voor de vuistregels-repo.

Voorbeelden::

    python -m cli bereken beweegvriendelijk GM1680
    vuistregels bereken beweegvriendelijk GM1680  # na `pip install -e .`
    vuistregels bereken beweegvriendelijk GM1680 GM0518 --workers 4 --uit resultaat.csv
    vuistregels bereken beweegvriendelijk --gemeenten-csv gemeenten.csv --uit resultaat.csv
"""
import argparse
import logging
from typing import Optional

import pandas as pd

from usecases.bereken_oppervlakte_beweegvriendelijk import (
    bereken_beweegvriendelijkheid_voor_gemeenten,
    naar_dataframe_beperkt,
)


def _cmd_bereken_beweegvriendelijk(args: argparse.Namespace) -> None:
    """Voer de use case uit voor een of meer gemeenten en toon of
    schrijf het resultaat weg."""
    codes = _verzamel_gemeente_codes(args.gemeente_codes, args.gemeenten_csv)
    resultaten = bereken_beweegvriendelijkheid_voor_gemeenten(
        codes,
        workers=args.workers,
        toestemming_buitenspeelkaart=args.toestemming_buitenspeelkaart,
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
        help="Oppervlakte-verdeling van beweegvriendelijke ruimte per buurt (voor een of meer gemeenten).",
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
        action="store_true",
        default=False,
        help="Zet aan als je toestemming hebt om Buitenspeelkaart-data mee te nemen. "
             "Standaard uit; OSM en BGT-speelvoorzieningen worden altijd meegenomen.",
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

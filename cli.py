"""Command-line interface voor de vuistregels-repo.

Voorbeelden::

    python -m cli bereken beweegvriendelijk GM1680
    vuistregels bereken beweegvriendelijk GM1680  # na `pip install -e .`
    vuistregels bereken beweegvriendelijk GM1680 --uit resultaat.csv
"""
import argparse
import logging
from typing import Optional

from usecases.bereken_oppervlakte_beweegvriendelijk import (
    bereken_beweegvriendelijkheid,
)


def _cmd_bereken_beweegvriendelijk(args: argparse.Namespace) -> None:
    """Voer de use case ``bereken_beweegvriendelijkheid`` uit en toon
    of schrijf het resultaat weg."""
    df = bereken_beweegvriendelijkheid(args.gemeente_code)
    if args.uit:
        if args.uit.endswith(".parquet"):
            df.to_parquet(args.uit)
        else:
            df.to_csv(args.uit, index=False)
        print(f"Resultaat opgeslagen naar {args.uit}")
    else:
        print(
            df.loc[
                df["stat"] == "area",
                ["buurtnaam", "rec_total", "rec_actief"],
            ]
            .head(20)
            .to_string(index=False)
        )


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
        help="Oppervlakte-verdeling van beweegvriendelijke ruimte per buurt.",
    )
    bw.add_argument(
        "gemeente_code",
        help="Gemeentecode inclusief prefix, bijv. GM1680.",
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

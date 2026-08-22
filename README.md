# vuistregels

Bereken hoeveel oppervlakte in een buurt of rond een puntlocatie
"beweegvriendelijk" is: welk aandeel groen, welk aandeel voor
langzaam verkeer (fiets, voetganger), welk aandeel voor speelplekken
en buitensport. Gebruikt open bronnen: de Basisregistratie
Grootschalige Topografie (BGT) via PDOK, de CBS-wijk- en
buurtgrenzen, de Buitenspeelkaart, en OpenStreetMap.

Wordt onderhouden door het [RIVM](https://www.rivm.nl) als hulpmiddel
voor onderzoek naar beweegvriendelijke leefomgevingen en voor
beleidsondersteuning van gemeenten en GGD'en.

## Wat je krijgt

Per gebied (buurt of puntbuffer) een DataFrame met per categorie
zowel absolute m² als aandeel:

- `rec_actief_transport`: fiets, voetganger
- `rec_spelen`: speelplekken (uit Buitenspeelkaart, OSM, BGT)
- `rec_buitensport`: buitensportvoorzieningen
- `rec_groen_blauw`: groen, water, natuur
- `rec_auto`, `rec_overig`, `rec_OV`: overige categorieen
- Afgeleide totalen: `rec_total`, `rec_actief`, `rec_inactief`

Overlappende BGT-features (bijv. een parkeervlak boven een
verhardingsvlak) tellen 1x dankzij een `unary_union`-benadering.

## Installatie

Activeer een venv en installeer de repo als package:

    python -m pip install -e .

Voor ontwikkeling (met tests):

    python -m pip install -e ".[dev]"

## Gebruik

Per buurt voor een gemeente:

    vuistregels bereken beweegvriendelijk GM1680

Rond een set puntlocaties met een buffer:

    vuistregels bereken beweegvriendelijk-punten punten.csv --buffer 800

De CSV met punten heeft kolommen `id`, `x`, `y` in RD-New
(EPSG:28992). Standaardbuffer is 800 meter.

Resultaat wegschrijven in plaats van tonen:

    vuistregels bereken beweegvriendelijk GM1680 --uit resultaat.csv
    vuistregels bereken beweegvriendelijk GM1680 --uit resultaat.parquet

Zonder installatie werkt het ook direct vanuit de root:

    python -m cli bereken beweegvriendelijk GM1680

## Data

De adapters downloaden hun bronnen bij eerste gebruik naar `./data/`
en cachen als Parquet. Landelijke bronnen (gemeente- en buurtgrenzen,
Buitenspeelkaart, OSM) worden een keer opgehaald. Per gemeente wordt
BGT via de asynchrone PDOK-API opgehaald (kan een paar minuten
duren).

## Tests

    python -m pytest

Zie [CONTRIBUTING.md](CONTRIBUTING.md) voor de ontwikkel-workflow.

## Architectuur

Clean architecture in drie lagen:

- `domein/`: entiteiten (`Gemeente`, `Buurt`, `Punt`), poorten
  (Protocols) en pure domeinkennis (BGT-categorisatie-regels).
- `adapters/`: implementaties van de poorten, opgesplitst in
  Downloader (I/O), Parser (transformatie) en een facade-class.
- `usecases/`: business-logica die adapters via dependency injection
  gebruikt.

## Conventies

Voertaal is hybride NL/EN: domeintermen NL, code-mechanica EN, Brits
Engels. Volledige regels in [CONTRIBUTING.md](CONTRIBUTING.md).

## Licentie

[European Union Public Licence v1.2](LICENSE) (EUPL-1.2).

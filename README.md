# Vuistregels

Bereken hoeveel oppervlakte in een buurt of rond een puntlocatie
"beweegvriendelijk" is: welk aandeel voor
langzaam verkeer (fiets, voetganger), welk aandeel voor speelplekken
en buitensport. Gebruikt open bronnen: de Basisregistratie
Grootschalige Topografie (BGT) via PDOK, de CBS-wijk- en
buurtgrenzen, de Buitenspeelkaart (toestemming van Speelplan nodig), 
DatabaseSportAanbod (Mulier Instituut) en OpenStreetMap.

Wordt onderhouden door het [RIVM](https://www.rivm.nl) als hulpmiddel
voor onderzoek naar beweegvriendelijke leefomgevingen en voor
beleidsondersteuning van gemeenten en GGD'en. Outputdata op buurtniveau beschikbaar via 
statline.rivm.nl

## Wat je krijgt

Per gebied (buurt of puntbuffer) een DataFrame met per categorie
zowel absolute m² als aandeel:

- `rec_actief_transport`: fiets, voetganger
- `rec_spelen`: speelplekken (uit Buitenspeelkaart, OSM, BGT)
- `rec_buitensport`: buitensportvoorzieningen
- `rec_groen_blauw`: groen, water, natuur (tellen niet mee)
- `rec_auto`, `rec_overig`, `rec_OV`: overige categorieen
- Afgeleide totalen: `rec_total`, `rec_actief`, `rec_inactief`

Overlappende BGT-features (bijv. een parkeervlak boven een
verhardingsvlak) tellen 1x dankzij een `unary_union`-benadering.

## Installatie

Activeer een venv en installeer de repo als package:

    python -m pip install -e .

Voor ontwikkeling (met tests):

    python -m pip install -e ".[dev]"

Indien gebruikgemaakt wordt van de DSA (dsa.mulierinstituut.nl): 
vraag bij het Mulier Instituut een API-key aan en vul het volgende in 
een .env in:

DSA_KEY=xxxxxx
DSA_MAIL=yyyy@zzzz.ext
TOESTEMMING_BUITENSPEELKAART=false

Indien wel expliciete toestemming voor gebruik van Buitenspeelkaart, zet deze op true.

## Gebruik

Per buurt voor een gemeente:

    vuistregels bereken beweegvriendelijk GM1680

Meerdere gemeenten tegelijk (parallel):

    vuistregels bereken beweegvriendelijk GM1680 GM0518 --workers 4

Of lees gemeenten uit een CSV met kolom `gemeente_code`:

    vuistregels bereken beweegvriendelijk --gemeenten-csv gemeenten.csv

Resultaat wegschrijven in plaats van tonen:

    vuistregels bereken beweegvriendelijk GM1680 --uit resultaat.csv
    vuistregels bereken beweegvriendelijk GM1680 --uit resultaat.parquet

Zonder installatie werkt het ook direct vanuit de root:

    python -m cli bereken beweegvriendelijk GM1680

## Data

De adapters downloaden hun bronnen bij eerste gebruik naar `./data/`
en cachen als Parquet. Landelijke bronnen (gemeente- en buurtgrenzen,
Buitenspeelkaart, OSM) worden eenmalig opgehaald. Per gemeente wordt
BGT via de asynchrone PDOK-API opgehaald (kan een paar minuten
duren). Let wel op dat caching in /data plaatsvindt en dat dit voor heel 
Nederland een omvangrijke hoeveelheid data zijn. Momenteel is het advies
om handmatig te verwijderen als deze data niet meer nodig zijn.

De Buitenspeelkaart data zijn GEEN open data en hier moet expliciet
toestemming voor komen van Speelplan. De adapters voor de Buitenspeelkaart
zijn wel opgenomen in deze scripts i.v.m. reproduceerbaarheid van de 
data. Deze data zijn aanvullend op data uit de BGT en OSM en completeren
het beeld van beweegplekken in de openbare buitenruimte. In de .env moet, 
zoals hierboven beschreven de toestemming expliciet ingevuld worden.

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

## Licentie

[European Union Public Licence v1.2](LICENSE) (EUPL-1.2).

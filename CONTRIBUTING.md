# Bijdragen aan vuistregels

Bedankt voor je interesse. Deze repo is beheerd door het RIVM en volgt
een aantal simpele conventies. Nieuwe bijdragen worden verwacht die te
respecteren.

## Ontwikkelsetup

1. Clone de repo en maak een virtuele omgeving:

   ```bash
   git clone <repo-url>
   cd vuistregels
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Installeer de repo als package met dev-dependencies:

   ```bash
   python -m pip install -e ".[dev]"
   ```

3. Draai de tests:

   ```bash
   python -m pytest
   ```

## Voertaal-conventies

Voertaal is **hybride NL/EN**. Onder deze regels valt alle nieuwe code
en alle bestaande code die je aanraakt.

**Nederlands** voor:
- Domein-termen in identifiers: `gemeente`, `buurt`, `speelplek`,
  `buitensport`, `beweegvriendelijk`, `oppervlakte`, `bereken_*`.
- Bestandsnamen (`bereken_oppervlakte_beweegvriendelijk.py`).
- Comments, docstrings.
- Print-statements, log-messages en foutmeldingen richting gebruiker.

**Engels** voor:
- Code-mechanica die niet domeinspecifiek is: `load_`, `get_`, `parse_`,
  `download_`, `fetch_`, `save_`, `build_`, `__init__`, `__main__`.
- Type-namen uit libraries (`GeoDataFrame`, `Polygon`).
- Britse spelling (`initialise`, `centre`, `colour`), niet Amerikaans.

**Casing:**
- Classes: `PascalCase` (`BestuurlijkeGrenzen`, niet
  `Bestuurlijkegrenzen`). Meerdere woorden = meerdere hoofdletters.
- Acroniemen als één blok (`BGT`, `DSA`, `API_URL`).
- Functies en variabelen: `snake_case`.
- Constanten: `UPPER_SNAKE_CASE`.
- Bestanden en modules: `snake_case.py`.

## Architectuur

De repo volgt clean architecture in drie lagen:

- `domein/`: entiteiten (`Gemeente`, `Buurt`, `Punt`), interfaces
  (Protocols) en pure domeinkennis (BGT-categorisatie-regels).
- `adapters/`: implementaties van de poorten, opgesplitst in
  Downloader (I/O), Parser (transformatie) en een facade-class die
  de Poort implementeert.
- `usecases/`: business-logica die adapters via dependency injection
  gebruikt.

Adapters retourneren waar zinvol domein-entiteiten (Gemeente, Buurt),
en voor grote featureverzamelingen `GeoDataFrame` als werkende
"currency".

## Pull requests

- Werk in een aparte branch. Naam mag NL of EN.
- Voeg tests toe voor nieuwe use cases en niet-triviale helpers.
- Zorg dat `python -m pytest` groen is voordat je een PR aanmaakt.
- Commit-berichten in het Nederlands, in de imperatief, kort en
  concreet ("Fix typo agragrisch", niet "typos gefixed").

## Vragen of ideeen

Open een issue op GitHub. Voor grotere veranderingen: eerst een issue
met het voorstel voordat je begint met bouwen.

# vuistregels

## Installatie

Activeer eerst je venv, en installeer de repo als package:

    python -m pip install -e .

## Draaien

    vuistregels bereken beweegvriendelijk GM1680

Resultaat wegschrijven in plaats van tonen:

    vuistregels bereken beweegvriendelijk GM1680 --uit resultaat.csv
    vuistregels bereken beweegvriendelijk GM1680 --uit resultaat.parquet

Zonder installatie werkt het ook direct vanuit de root:

    python -m cli bereken beweegvriendelijk GM1680

## Conventies

Voertaal: **hybride NL/EN**. De regels zijn strikt — nieuwe code hoort
er direct aan te voldoen, bestaande code wordt bij aanraken meegetrokken.

### Nederlands

- **Domein-termen** in identifiers: `gemeente`, `buurt`, `speelplek`,
  `buitensport`, `beweegvriendelijk`, `oppervlakte`, `bereken_*`.
- **Bestandsnamen** (`bereken_oppervlakte_beweegvriendelijk.py`,
  `bestuurlijke_grenzen.py`, `hulpmiddelen.py`).
- **Comments** en docstrings.
- **Print-statements** en foutmeldingen richting de gebruiker.

### Engels

- **Code-mechanica** die niet domeinspecifiek is: `load_`, `get_`,
  `parse_`, `download_`, `fetch_`, `save_`, `build_`, `__init__`,
  `__main__`.
- **Type-namen** uit libraries (`GeoDataFrame`, `Polygon`) — niet
  vertalen.
- **Britse spelling** (`initialise`, `centre`, `colour`) — niet
  Amerikaans.

### Casing

- Classes: `PascalCase` (`BestuurlijkeGrenzen`, niet
  `Bestuurlijkegrenzen`). Meerdere woorden = meerdere hoofdletters.
- Acroniemen als één blok (`BGT`, `DSA`, `ORI`, `API_URL`).
- Functies en variabelen: `snake_case`.
- Constanten: `UPPER_SNAKE_CASE`.
- Bestanden en modules: `snake_case.py`.

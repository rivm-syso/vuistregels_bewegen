from adapters import bestuurlijke_grenzen, bgt, speelplekken, dsa


def load_and_initialise_gemeente_data(gemeente_code):
    bg_instance = bestuurlijke_grenzen.BestuurlijkeGrenzen(gemeente_code=gemeente_code)
    gemeente = bg_instance.get_gemeente()
    buurten = bg_instance.get_buurten()
    gemeente_geometry = gemeente.geometry.iloc[0]
    bgt_gemeente = bgt.BGT(gemeente_code, gemeente_geometry)
    sp = speelplekken.Speelplekken()
    sps = sp.get_alle(gemeente_code, gemeente_geometry)
    # dsa_gemeente = dsa.DSA(gemeente_code).get_buitensporten()
    dsa_gemeente = None
    return {
        'bgt_df': bgt_gemeente.get_gemeente(),
        'buurt_geometrie_df': buurten,
        'speelplekken_df': sps,
        'buitensporten_df': dsa_gemeente,
    }

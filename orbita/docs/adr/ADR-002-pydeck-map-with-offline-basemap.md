# ADR-002 - pydeck map with an offline Natural Earth basemap

- Status: Accepted (2026-10-30)

## Context

The map must redraw 20 satellites, the ISS ground track and the user's marker every 1 s (RF-01, RNF-01), let the
user click a satellite to open its card (RF-03), and work without internet (RF-05). It must also not send the user's
location to any external service (SEC-04). A map with web tiles (for example, Carto, the default basemap of
`st.pydeck_chart`) makes the browser request the tiles of the area being viewed: a map zoomed on the user's
marker would tell the tile provider where the user is.

## Decision

- Map library: **pydeck** through `st.pydeck_chart`, inside the live fragment. pydeck is already a dependency of
  Streamlit (no new runtime dependency, SEC-39), draws with WebGL and supports selection with `on_select`; every
  layer has a fixed `id` so the selection survives reruns.
- Basemap: **none from the internet**. `map_provider=None` (pydeck 0.9 or later) and a `GeoJsonLayer` with the
  country outlines of Natural Earth 1:110m, versioned in `assets/ne_110m_countries.geojson`. Natural Earth is in the
  public domain.
- Tooltips use pydeck's plain `text` option, never `html` (SEC-13).
- The map starts with a world view and never centers or zooms on the user automatically.

## Rejected alternatives

- **folium + `streamlit-folium`:** one more third-party dependency, and the Leaflet map is rebuilt as an iframe on
  each rerun, which risks flicker every second.
- **pydeck with the default Carto basemap:** depends on the internet, may need a key for advanced features and leaks
  the viewed area to the tile provider.
- **Mapbox:** requires an account and a key, which is a secret to manage (SEC-21).

## Consequences

- The whole page works offline: positions are computed locally and the basemap is a local file.
- The map shows country outlines only, without streets or terrain; that is enough for satellites.
- Spec 000 adds `assets/` to the folder structure. The 1 s refresh is measured in the spec of the live view; if it
  flickers or exceeds RNF-01, the interval goes to 2 s and a new ADR records it.

## Affected governing rules

`ARCHITECTURE.md` §5, §7.1; `security-rules.md` SEC-04, SEC-13, SEC-22, SEC-39; `docs/00-requirements.md` RF-01,
RF-03, RF-05, RNF-03.

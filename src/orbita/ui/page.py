"""Streamlit UI page: refresh data, fragment redraws map (ARCHITECTURE.md §7.1)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import streamlit as st

from orbita.app.get_live_view import GetLiveView
from orbita.app.live_view import LiveView
from orbita.app.refresh_satellite_data import RefreshSatelliteData
from orbita.domain.observer import Observer
from orbita.domain.sky import moon_subpoint, sun_subpoint
from orbita.ui.cards import card_rows, freshness_notice
from orbita.ui.continuous_location import continuous_location_section
from orbita.ui.location import OBSERVER_KEY, location_section
from orbita.ui.map_view import SATELLITE_LAYER_ID, SkyLayers, build_deck, load_basemap
from orbita.ui.night_mask import write_night_mask

logger = logging.getLogger(__name__)

STARFIELD_STYLE: Final = """<style>
.stApp {
  background-color: #03040a;
  background-image:
    radial-gradient(1px 1px at 20px 30px, #ffffff, transparent),
    radial-gradient(1px 1px at 90px 140px, #d8e4ff, transparent),
    radial-gradient(1.5px 1.5px at 160px 70px, #ffffff, transparent),
    radial-gradient(1px 1px at 230px 200px, #fff3d6, transparent),
    radial-gradient(1px 1px at 300px 120px, #ffffff, transparent);
  background-size: 320px 260px;
}
header[data-testid="stHeader"] { background: transparent; }
</style>"""


@dataclass(frozen=True, slots=True)
class PageDependencies:
    """What the page receives from the composition root (ARCHITECTURE.md §2, rule 5)."""

    refresh: RefreshSatelliteData
    live: GetLiveView
    texts: dict[str, str]
    basemap_path: Path
    refresh_seconds: int
    earth_texture_path: Path
    data_dir: Path


def render_page(deps: PageDependencies) -> None:
    """Draw the title, the approximation notice, run the refresh once and start the live map."""
    st.set_page_config(page_title=deps.texts["title"], layout="wide")
    st.markdown(STARFIELD_STYLE, unsafe_allow_html=True)
    st.title(deps.texts["title"])
    st.caption(deps.texts["approximate_notice"])
    deps.refresh.execute()
    location_section(deps.texts)
    continuous_location_section(deps.texts)
    _make_live_fragment(deps)()


def _make_live_fragment(deps: PageDependencies) -> Callable[[], None]:
    """Return the fragment that redraws the map every refresh_seconds (ARCHITECTURE.md §7.1)."""

    @st.fragment(run_every=deps.refresh_seconds)
    def live_map() -> None:
        try:
            observer: Observer | None = st.session_state.get(OBSERVER_KEY)
            _draw(deps, deps.live.execute(observer), observer)
        except Exception:  # noqa: BLE001 - a failure must not freeze the map (ARCHITECTURE.md §6)
            logger.exception("live_view_failed")
            st.error(deps.texts["unexpected_error"])

    return live_map


def _draw(deps: PageDependencies, view: LiveView, observer: Observer | None) -> None:
    """Draw the notices, the map and the card of the selected satellite."""
    notice = freshness_notice(view.freshness, view.age_days, deps.texts)
    if notice is not None:
        st.warning(notice)
    if view.freshness is None:
        return
    if observer is None:
        st.info(deps.texts["location_unavailable"])
    if view.missing_norad:
        numbers = ", ".join(str(number) for number in view.missing_norad)
        st.caption(deps.texts["missing_satellites"].format(norad_numbers=numbers))
    if view.downloaded_text is not None:
        st.caption(f"{deps.texts['label_last_download']}: {view.downloaded_text}")
    basemap = load_basemap(deps.basemap_path)
    sky = _sky_layers(deps)
    state: Any = st.pydeck_chart(
        build_deck(view, observer, basemap, str(deps.earth_texture_path), sky),
        on_select="rerun",
        selection_mode="single-object",
        key="satellite_map",
        height=520,
    )
    _show_card(deps, view, _selected_norad(state))


def _sky_layers(deps: PageDependencies) -> SkyLayers:
    """Where the Sun and the Moon are overhead now, and the night mask (offline formulas)."""
    now = datetime.now(UTC)
    sun = sun_subpoint(now)
    mask_path = deps.data_dir / "night_mask.png"
    night_image: str | None = None
    try:
        write_night_mask(mask_path, sun)
        night_image = str(mask_path)
    except OSError:
        logger.warning("night_mask_not_written")
    return SkyLayers(sun=sun, moon=moon_subpoint(now), night_image=night_image)


def _selected_norad(state: Any) -> int | None:
    """Return the NORAD number of the satellite clicked on the map, if any."""
    selection = getattr(state, "selection", None) or {}
    objects = selection.get("objects", {}).get(SATELLITE_LAYER_ID, [])
    if not objects:
        return None
    norad = objects[0].get("norad")
    return norad if isinstance(norad, int) else None


def _show_card(deps: PageDependencies, view: LiveView, norad: int | None) -> None:
    """Show the card of the selected satellite as plain text (SEC-13)."""
    if norad is None:
        st.caption(deps.texts["select_satellite"])
        return
    chosen = next((item for item in view.satellites if item.norad == norad), None)
    if chosen is None:
        return
    with st.container(border=True):
        st.text(chosen.name)
        for label, value in card_rows(chosen, deps.texts):
            st.text(f"{label}: {value}")

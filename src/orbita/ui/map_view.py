"""Builds the pydeck map from a LiveView (ADR-002). Pure functions: they do not call Streamlit."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import pydeck  # type: ignore[import-untyped]

from orbita.app.live_view import LiveView
from orbita.domain.errors import ConfigError
from orbita.domain.observer import GroundPoint, Observer

BASEMAP_LAYER_ID: Final = "basemap"
OCEAN_LAYER_ID: Final = "ocean"
EARTH_LAYER_ID: Final = "earth"
NIGHT_LAYER_ID: Final = "night"
SUN_LAYER_ID: Final = "sun"
MOON_LAYER_ID: Final = "moon"
SUN_RADIUS_M: Final = 120_000
MOON_RADIUS_M: Final = 90_000
# One polygon covering the whole planet: the sea color under the country outlines (offline).
OCEAN_FEATURES: Final[dict[str, Any]] = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]],
            },
        }
    ],
}
TRACK_LAYER_ID: Final = "iss_track"
SATELLITE_LAYER_ID: Final = "satellites"
OBSERVER_LAYER_ID: Final = "observer"
SATELLITE_RADIUS_M: Final = 60_000
OBSERVER_RADIUS_M: Final = 80_000


def load_basemap(path: Path) -> dict[str, Any]:
    """Read the offline country outlines: a GeoJSON FeatureCollection (ADR-002, SEC-09).

    Raises:
        ConfigError: if the file cannot be read or is not a FeatureCollection.
    """
    try:
        content = json.loads(path.read_text(encoding="utf-8-sig"))  # tolerates a BOM
    except (OSError, ValueError) as error:
        raise ConfigError(f"{path.name} cannot be read as JSON") from error
    if not isinstance(content, dict) or content.get("type") != "FeatureCollection":
        raise ConfigError(f"{path.name} must be a GeoJSON FeatureCollection")
    return content


def satellite_rows(view: LiveView) -> list[dict[str, Any]]:
    """One row per satellite, with the position as [longitude, latitude] (pydeck order)."""
    return [
        {
            "norad": item.norad,
            "name": item.name,
            "position": [item.point.longitude, item.point.latitude],
        }
        for item in view.satellites
    ]


def track_path(track: tuple[GroundPoint, ...]) -> list[list[float]]:
    """The ISS ground track as [longitude, latitude] pairs."""
    return [[point.longitude, point.latitude] for point in track]


def _background_layers(earth_image: str | None) -> list[Any]:
    """The surface under the outlines: the Earth photo when available, otherwise plain sea."""
    if earth_image is not None:
        return [
            pydeck.Layer(
                "BitmapLayer",
                id=EARTH_LAYER_ID,
                image=earth_image,
                bounds=[-180, -90, 180, 90],
                pickable=False,
            )
        ]
    return [
        pydeck.Layer(
            "GeoJsonLayer",
            id=OCEAN_LAYER_ID,
            data=OCEAN_FEATURES,
            stroked=False,
            filled=True,
            get_fill_color=[18, 58, 104],
            pickable=False,
        )
    ]


@dataclass(frozen=True, slots=True)
class SkyLayers:
    """Where the Sun and the Moon are overhead (latitude, longitude) and the night mask file."""

    sun: tuple[float, float]
    moon: tuple[float, float]
    night_image: str | None = None


def _night_layers(sky: SkyLayers | None) -> list[Any]:
    """The dark night side, drawn over the Earth photo when a mask file is available."""
    if sky is None or sky.night_image is None:
        return []
    return [
        pydeck.Layer(
            "BitmapLayer",
            id=NIGHT_LAYER_ID,
            image=sky.night_image,
            bounds=[-180, -90, 180, 90],
            pickable=False,
        )
    ]


def _sky_marker_layers(sky: SkyLayers | None) -> list[Any]:
    """Markers where the Sun and the Moon are overhead, named in the tooltip."""
    if sky is None:
        return []
    return [
        pydeck.Layer(
            "ScatterplotLayer",
            id=SUN_LAYER_ID,
            data=[{"name": "Sol", "position": [sky.sun[1], sky.sun[0]]}],
            get_position="position",
            get_fill_color=[255, 214, 90],
            get_radius=SUN_RADIUS_M,
            radius_min_pixels=9,
            pickable=True,
        ),
        pydeck.Layer(
            "ScatterplotLayer",
            id=MOON_LAYER_ID,
            data=[{"name": "Luna", "position": [sky.moon[1], sky.moon[0]]}],
            get_position="position",
            get_fill_color=[220, 220, 225],
            get_radius=MOON_RADIUS_M,
            radius_min_pixels=7,
            pickable=True,
        ),
    ]


def build_deck(
    view: LiveView,
    observer: Observer | None,
    basemap: dict[str, Any],
    earth_image: str | None = None,
    sky: SkyLayers | None = None,
) -> pydeck.Deck:
    """Build the 3D globe: offline outlines, the ISS track, the satellites and the user marker.

    Postconditions: no tile server is used (map_provider=None, ADR-002).
    The tooltip is plain text (SEC-13).
    """
    land_fill = earth_image is None
    layers: list[Any] = [
        *_background_layers(earth_image),
        *_night_layers(sky),
        pydeck.Layer(
            "GeoJsonLayer",
            id=BASEMAP_LAYER_ID,
            data=basemap,
            stroked=True,
            filled=land_fill,
            get_fill_color=[78, 124, 74],
            get_line_color=[150, 190, 140] if land_fill else [255, 255, 255, 110],
            get_line_width=1,
            line_width_min_pixels=1,
            pickable=False,
        ),
        pydeck.Layer(
            "PathLayer",
            id=TRACK_LAYER_ID,
            data=[{"path": track_path(view.iss_track)}],
            get_path="path",
            get_color=[255, 200, 0],
            width_min_pixels=2,
            pickable=False,
        ),
        pydeck.Layer(
            "ScatterplotLayer",
            id=SATELLITE_LAYER_ID,
            data=satellite_rows(view),
            get_position="position",
            get_fill_color=[0, 200, 255],
            get_radius=SATELLITE_RADIUS_M,
            radius_min_pixels=7,
            pickable=True,
            auto_highlight=True,
        ),
        *_sky_marker_layers(sky),
    ]
    if observer is not None:
        layers.append(
            pydeck.Layer(
                "ScatterplotLayer",
                id=OBSERVER_LAYER_ID,
                data=[{"position": [observer.longitude, observer.latitude]}],
                get_position="position",
                get_fill_color=[255, 60, 60],
                get_radius=OBSERVER_RADIUS_M,
                radius_min_pixels=7,
                pickable=False,
            )
        )
    return pydeck.Deck(
        layers=layers,
        views=[pydeck.View(type="_GlobeView", controller=True)],
        initial_view_state=pydeck.ViewState(latitude=0.0, longitude=0.0, zoom=1),
        map_provider=None,
        tooltip={"text": "{name}"},
    )

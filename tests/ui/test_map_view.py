"""Tests of the pure map functions: no Streamlit needed (spec 015)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orbita.app.live_view import LiveView, SatelliteView
from orbita.domain.elements import Freshness, OrbitType
from orbita.domain.errors import ConfigError
from orbita.domain.observer import GroundPoint, Observer
from orbita.ui.map_view import (
    EARTH_LAYER_ID,
    OBSERVER_LAYER_ID,
    OCEAN_LAYER_ID,
    SATELLITE_LAYER_ID,
    TRACK_LAYER_ID,
    build_deck,
    load_basemap,
    EARTH_TEXTURE_URL,
    satellite_rows,
    track_path,
)


def satellite(norad: int = 25544) -> SatelliteView:
    return SatelliteView(
        norad=norad,
        name="ISS (ZARYA)",
        point=GroundPoint(latitude=10.0, longitude=-75.0, altitude_km=420.0),
        speed_km_s=7.66,
        orbit_type=OrbitType.LOW,
        period_minutes=93,
        distance_km=None,
        owner_code=None,
        launch_date=None,
        years_in_orbit=None,
    )


def view(track: tuple[GroundPoint, ...] = ()) -> LiveView:
    return LiveView(
        freshness=Freshness.NORMAL,
        downloaded_text="2026-10-30 07:00",
        age_days=0,
        satellites=(satellite(),),
        missing_norad=(),
        iss_track=track,
    )


def test_load_basemap_accepts_a_feature_collection(tmp_path: Path) -> None:
    path = tmp_path / "countries.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8")
    assert load_basemap(path)["type"] == "FeatureCollection"


def test_load_basemap_rejects_other_json(tmp_path: Path) -> None:
    path = tmp_path / "countries.geojson"
    path.write_text(json.dumps({"type": "Feature"}), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_basemap(path)


def test_satellite_rows_put_longitude_first() -> None:
    assert satellite_rows(view())[0]["position"] == [-75.0, 10.0]


def test_track_path_has_one_pair_per_point() -> None:
    track = tuple(GroundPoint(latitude=0.0, longitude=float(index)) for index in range(91))
    path = track_path(track)
    assert len(path) == 91
    assert path[0] == [0.0, 0.0]


def test_deck_has_the_base_layers_without_an_observer() -> None:
    deck = build_deck(view(), None, {"type": "FeatureCollection", "features": []})
    assert [layer.id for layer in deck.layers] == [
        OCEAN_LAYER_ID,
        "basemap",
        TRACK_LAYER_ID,
        SATELLITE_LAYER_ID,
    ]


def test_deck_adds_the_observer_layer_when_the_location_is_known() -> None:
    deck = build_deck(
        view(),
        Observer(latitude=3.45, longitude=-76.53),
        {"type": "FeatureCollection", "features": []},
    )
    assert OBSERVER_LAYER_ID in [layer.id for layer in deck.layers]


def test_deck_tooltip_is_plain_text_and_no_tiles_are_requested() -> None:
    deck = build_deck(view(), None, {"type": "FeatureCollection", "features": []})
    serialized = deck.to_json()
    assert '"html"' not in serialized
    assert deck._tooltip == {"text": "{name}"}  # pydeck keeps the tooltip in a private attribute


def test_deck_is_a_3d_globe() -> None:
    """The map is a 3D globe (DESIGN.md §5), drawn without any tile server."""
    deck = build_deck(view(), None, {"type": "FeatureCollection", "features": []})
    assert deck.views[0].type == "_GlobeView"
    assert deck.map_provider is None


def test_load_basemap_accepts_a_byte_order_mark(tmp_path: Path) -> None:
    """Windows editors add a BOM; the outlines must still load (found when running the app)."""
    path = tmp_path / "countries.geojson"
    body = json.dumps({"type": "FeatureCollection", "features": []}).encode("utf-8")
    path.write_bytes(b"\xef\xbb\xbf" + body)
    assert load_basemap(path)["type"] == "FeatureCollection"


def test_the_bundled_countries_file_has_the_country_outlines() -> None:
    """The offline outlines must contain real countries (the file was empty once, unnoticed)."""
    path = Path(__file__).resolve().parents[2] / "assets" / "ne_110m_countries.geojson"
    features = load_basemap(path)["features"]
    assert len(features) >= 170


def test_deck_draws_the_earth_photo_under_everything_when_given() -> None:
    empty = {"type": "FeatureCollection", "features": []}
    deck = build_deck(view(), None, empty, EARTH_TEXTURE_URL)
    assert deck.layers[0].id == EARTH_LAYER_ID
    assert OCEAN_LAYER_ID not in [layer.id for layer in deck.layers]


def test_earth_texture_is_served_from_the_static_folder() -> None:
    """The photo lives in static/ so Streamlit serves it offline at EARTH_TEXTURE_URL."""
    assert EARTH_TEXTURE_URL == "/app/static/earth_texture.jpg"
    assert (Path(__file__).resolve().parents[2] / "static" / "earth_texture.jpg").is_file()


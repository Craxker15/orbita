"""Tests of the validation of downloaded data (spec 007)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from orbita.domain.elements import OrbitalElements
from orbita.domain.errors import DataValidationError
from orbita.domain.validation import (
    MAX_DOWNLOAD_BYTES,
    mean_motion_change_is_plausible,
    parse_catalog_payload,
    parse_elements_payload,
    parse_json_text,
)

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
ALLOWED = frozenset({25544, 20580})


def elements_record(**changes: object) -> dict[str, object]:
    record: dict[str, object] = {
        "NORAD_CAT_ID": 25544,
        "OBJECT_NAME": "ISS (ZARYA)",
        "EPOCH": "2026-10-30T10:00:00.000000",
        "INCLINATION": 51.6,
        "MEAN_MOTION": 15.5,
        "ECCENTRICITY": 0.0007,
        "RA_OF_ASC_NODE": 247.0,
        "ARG_OF_PERICENTER": 130.0,
        "MEAN_ANOMALY": 325.0,
        "MEAN_MOTION_DOT": 0.0001,
        "MEAN_MOTION_DDOT": 0.0,
        "BSTAR": 0.0001,
    }
    record.update(changes)
    return record


def catalog_record(**changes: object) -> dict[str, object]:
    record: dict[str, object] = {"NORAD_CAT_ID": 25544, "OWNER": "ISS", "LAUNCH_DATE": "1998-11-20"}
    record.update(changes)
    return record


def element_from(**changes: object) -> OrbitalElements:
    return parse_elements_payload([elements_record(**changes)], ALLOWED, NOW).accepted[0]


def test_parse_json_text_accepts_a_list() -> None:
    assert parse_json_text('[{"a": 1}]') == [{"a": 1}]


@pytest.mark.parametrize("text", ["[NaN]", "[Infinity]", '[{"x": -Infinity}]'])
def test_parse_json_text_rejects_nan_and_infinity(text: str) -> None:
    with pytest.raises(DataValidationError):
        parse_json_text(text)


def test_parse_json_text_rejects_text_over_5_mb() -> None:
    with pytest.raises(DataValidationError):
        parse_json_text("[" + " " * MAX_DOWNLOAD_BYTES + "]")


def test_parse_json_text_rejects_deep_nesting() -> None:
    with pytest.raises(DataValidationError):
        parse_json_text("[" * 10_000 + "]" * 10_000)


def test_parse_json_text_rejects_invalid_json() -> None:
    with pytest.raises(DataValidationError):
        parse_json_text("[{")


def test_valid_record_becomes_orbital_elements_in_utc() -> None:
    parsed = parse_elements_payload([elements_record()], ALLOWED, NOW)
    assert parsed.rejected_norad == ()
    assert parsed.accepted[0].epoch.tzinfo == UTC
    assert parsed.accepted[0].raan_deg == 247.0


def test_payload_must_be_a_list_of_at_most_50_records() -> None:
    with pytest.raises(DataValidationError):
        parse_elements_payload({"a": 1}, ALLOWED, NOW)
    with pytest.raises(DataValidationError):
        parse_elements_payload([elements_record()] * 51, ALLOWED, NOW)


@pytest.mark.parametrize(
    "change",
    [
        {"NORAD_CAT_ID": 99999},
        {"NORAD_CAT_ID": True},
        {"NORAD_CAT_ID": "25544"},
        {"OBJECT_NAME": "<script>alert(1)</script>"},
        {"OBJECT_NAME": "ISS\nFAKE LOG LINE"},
        {"OBJECT_NAME": "x" * 81},
        {"EPOCH": "2026-11-05T00:00:00"},
        {"EPOCH": "not a date"},
        {"INCLINATION": 181.0},
        {"MEAN_MOTION": 0.0},
        {"ECCENTRICITY": 1.0},
        {"RA_OF_ASC_NODE": 360.0},
        {"BSTAR": float("nan")},
    ],
)
def test_invalid_record_is_rejected(change: dict[str, object]) -> None:
    parsed = parse_elements_payload([elements_record(**change)], ALLOWED, NOW)
    assert parsed.accepted == ()


def test_record_missing_a_field_is_rejected() -> None:
    record = elements_record()
    del record["BSTAR"]
    assert parse_elements_payload([record], ALLOWED, NOW).accepted == ()


def test_epoch_up_to_one_day_in_the_future_is_accepted() -> None:
    near_future = (NOW + timedelta(hours=23)).replace(tzinfo=None).isoformat()
    assert (
        len(parse_elements_payload([elements_record(EPOCH=near_future)], ALLOWED, NOW).accepted)
        == 1
    )


def test_good_records_are_kept_when_another_record_is_bad() -> None:
    good = elements_record()
    bad = elements_record(NORAD_CAT_ID=20580, OBJECT_NAME="<b>")
    parsed = parse_elements_payload([good, bad], ALLOWED, NOW)
    assert [item.norad for item in parsed.accepted] == [25544]
    assert parsed.rejected_norad == (20580,)


def test_catalog_record_is_accepted() -> None:
    parsed = parse_catalog_payload([catalog_record()], ALLOWED, NOW)
    assert parsed.accepted[0].owner_code == "ISS"


@pytest.mark.parametrize(
    "change",
    [{"OWNER": "us"}, {"LAUNCH_DATE": "2026-13-01"}, {"NORAD_CAT_ID": 1}],
)
def test_invalid_catalog_record_is_rejected(change: dict[str, object]) -> None:
    parsed = parse_catalog_payload([catalog_record(**change)], ALLOWED, NOW)
    assert parsed.accepted == ()


def test_mean_motion_change_of_1_percent_is_plausible() -> None:
    assert mean_motion_change_is_plausible(element_from(), element_from(MEAN_MOTION=15.655))


def test_mean_motion_change_of_6_percent_is_not_plausible() -> None:
    assert not mean_motion_change_is_plausible(element_from(), element_from(MEAN_MOTION=16.43))


def test_first_download_has_no_previous_value_to_compare() -> None:
    assert mean_motion_change_is_plausible(None, element_from())


def test_orbital_elements_reject_angles_of_360_degrees() -> None:
    with pytest.raises(DataValidationError):
        OrbitalElements(
            norad=25544,
            name="ISS",
            inclination_deg=51.6,
            mean_motion_rev_day=15.5,
            eccentricity=0.0007,
            epoch=NOW,
            raan_deg=360.0,
            arg_perigee_deg=130.0,
            mean_anomaly_deg=325.0,
            mean_motion_dot=0.0,
            mean_motion_ddot=0.0,
            bstar=0.0,
        )

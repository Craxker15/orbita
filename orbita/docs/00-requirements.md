# Requirements — Orbita

> Status: Approved 2026-10-30. Amendment 1 (§7) approved 2026-10-30. Amendment 2 (§7) approved 2026-10-30.
> Source: `DESIGN.md` §1-§5 (closed design, 2026-10-30; corrections in `DESIGN.md` §9).

## 1. Scope

Web map that shows in real time the position of 20 selected satellites from several countries, the ISS ground
track, the user's location and the approximate distance from the user to each satellite. Each satellite has a card
with altitude, speed, orbit type, period, distance and, from the CelesTrak satellite catalog, country, launch date
and years in orbit. Positions are computed locally from CelesTrak's public orbital elements, which are downloaded and
saved to local files. The user's location is read from the browser and never stored.

Priorities: P1 live map with the 20 satellites, ISS ground track, one-time location and distances, satellite card,
download and local copy of the orbital elements, stale data notice; P2 catalog data (country, launch date, years in
orbit); P3 continuous location and HTTPS publication.

## 2. Out of scope

- Prediction of passes visible from the user's location (planned for v2).
- Whether a satellite is above the user's horizon and the direction to look.
- Satellites other than the 20 in `DESIGN.md` §3.1, and ground tracks other than the ISS.
- Storing the user's location or a location history.
- Notifications (email, Telegram, push).
- Native mobile app, 3D globe view and satellite imagery.
- User accounts and per-user saved data.

## 3. Functional requirements

| ID | Priority | Requirement | Measurable acceptance criterion |
|---|---|---|---|
| RF-01 | P1 | The system MUST show on a world map the current position of the 20 satellites and update it every 1 s. | With the app open for 60 s, the ISS marker changes position at least 55 times. Adapter test: two ISS positions computed 1 s apart are between 7 and 8 km apart. |
| RF-02 | P1 | The system MUST draw the ISS ground track from 45 min before to 45 min after the current time. | Test: the track has 91 points (one per minute), the first at −45 min and the last at +45 min. |
| RF-03 | P1 | The system MUST show a card for each satellite with name, altitude, speed, orbit type according to `DESIGN.md` §4.1 and period according to §4.6. | Clicking each of the 20 satellites shows the fields; altitude in km with 0 decimals, speed in km/s with 2 decimals, period in whole minutes. Domain test (inclination °, mean motion rev/day): (0.1, 1.0027) → geostationary; (98.7, 14.2) → polar; (80.0, 14.0) → polar; (79.9, 14.0) → low; (51.6, 15.5) → low; (55.0, 2.0) → other. Period: 15.5 rev/day → 93 min; 1.0027 rev/day → 1436 min. |
| RF-04 | P1 | The system MUST download the orbital elements from CelesTrak at most once every 2 h and save them to a local file. | Test with a simulated clock and a fake download: a second request 1 h 59 min after a download attempt, successful or failed, does not download; at 2 h 0 min it does. A simulated HTTP 403 is not retried. |
| RF-05 | P1 | The system MUST work without internet using the last saved files. | With the network disabled and saved files, the app starts and shows the 20 positions. |
| RF-06 | P1 | The system MUST apply the orbital data freshness rule of `DESIGN.md` §4.2. | Domain test: age 3 days → no notice; 3 days + 1 s → notice and positions; 14 days → notice and positions; 14 days + 1 s → data-too-old notice and no positions. |
| RF-07 | P1 | The system MUST reject an invalid downloaded file and keep the previous one. | Test with a simulated response that is not valid JSON or lacks fields: the saved file does not change and the error is logged. A valid file that lacks one satellite is accepted, and that satellite is reported as missing. |
| RF-08 | P1 | Without saved orbital elements and without internet, the system MUST start and show a message explaining that there is no orbital data. | With `data/` empty and the network disabled, the app opens and shows the `no_orbital_data` text from `locales/es.json`. |
| RF-09 | P1 | The system MUST show the date and time of the last successful download in Colombia time. | Domain test: `2026-10-30T03:00:00Z` → `2026-10-29 22:00`. |
| RF-10 | P1 | When the user presses "My location" and accepts the browser permission, the system MUST read the location once and show it on the map with a marker. | On `localhost`, pressing the button and accepting shows the marker and the accuracy reported by the browser. Domain test of `DESIGN.md` §4.5: (3.45, −76.53) valid; (90.0, 180.0) valid; (90.1, 0.0) invalid; (0.0, −180.1) invalid. |
| RF-11 | P1 | With a valid location, the system MUST show the approximate distance from the user to each satellite according to `DESIGN.md` §4.4. | Domain test: observer (0°, 0°), satellite (0°, 0°, 400 km) → 400 km; observer (0°, 0°), point (0°, 90°, 0 km) → shown as "≈ 9010 km". |
| RF-12 | P1 | If the location is denied, unavailable or invalid, the system MUST keep working without distances and show a message. | Denying the permission: the map shows the 20 satellites and the `location_unavailable` text from `locales/es.json` instead of the distances. |
| RF-13 | P2 | The system MUST download the CelesTrak satellite catalog at most once every 24 h, save it locally and show in the card the country, launch date and years in orbit according to `DESIGN.md` §4.6. | Test with a simulated clock: a request 23 h 59 min after a download attempt, successful or failed, does not download; at 24 h 0 min it does. Domain test: launch `2016-10-30`, current date `2026-10-30` → 10.0 years; owner code with an `owner_<CODE>` key → that text; unknown code `XYZ` → `XYZ`. |
| RF-14 | P2 | Without a saved catalog, the card fields that depend on it MUST show "—". | With no catalog file and no internet, every card shows "—" in country, launch date and years in orbit. |
| RF-15 | P3 | With the page open, the system MUST update the user's marker and the distances when the location changes. | On the published version opened on a phone, walking 100 m moves the marker on the map. |
| RF-16 | P3 | The system MUST be published at an HTTPS address. | The published URL starts with `https://`, opens on a phone and RF-10 works there. |

## 4. Non-functional requirements

| ID | Requirement | Measurable value and unit |
|---|---|---|
| RNF-01 | Time to compute the positions and distances of the 20 satellites on each refresh. | ≤ 100 ms on a laptop without a GPU, measured in the log. |
| RNF-02 | Position accuracy. | ≤ 5 km difference from the reference site (`DESIGN.md` §8) for the ISS at 3 instants, with data less than 1 day old. |
| RNF-03 | Network use. | The only network calls of the program are the CelesTrak downloads (orbital elements and catalog); 0 calls per map refresh. |
| RNF-04 | User-facing text. | 100 % of the user-facing text comes from `locales/es.json`; 0 user-facing strings in the Python code. |
| RNF-05 | Personal data. | The user's location appears in 0 files on disk and 0 log lines after a 10 min session with the location active; the program only writes in `data/` and in the log. |
| RNF-06 | Browsers and screen. | Works in the current versions of Chrome and Firefox at 1366 × 768 without horizontal scrolling. |
| RNF-07 | Mobile screen (P3). | The published version works on a phone at 390 × 844 without horizontal scrolling. |

## 5. Glossary

| Term | Definition |
|---|---|
| Orbital elements | CelesTrak data (GP format, JSON) that describe an orbit at a given moment. |
| SATCAT | CelesTrak satellite catalog: owner, launch date and object type of each satellite. |
| SGP4 | Standard model that computes a satellite's position from its orbital elements. |
| NORAD number | Unique catalog number of each satellite (for example, 25544 for the ISS). |
| Inclination | Angle between the orbit and the Earth's equator, in degrees: 0° follows the equator, 90° passes over the poles. |
| Mean motion | Number of revolutions around the Earth per day. |
| Period | Time of one revolution, in minutes. |
| Orbit type | Classification of `DESIGN.md` §4.1: geostationary, polar, low or other. |
| Observer | The user's location read from the browser; it only lives in memory. |
| Ground track | Line on the map of the points of the Earth directly below the satellite over time. |
| Data age | Time elapsed since the last successful download. |

## 6. Open questions

Pending validation (`DESIGN.md` §8); they do not change the requirements, but they do change the specs that use them:

1. Whether Streamlit with fragments can refresh 20 satellites every 1 s (RF-01, RNF-01).
2. The NORAD numbers of `DESIGN.md` §3.1, and whether FACSAT-2 is still in orbit.
3. The SATCAT owner codes needed for the 20 satellites (RF-13).
4. How to read the location continuously (RF-15, new ADR before P3).
5. Reference site for RNF-02.
6. Whether the 3 and 14 day thresholds of RF-06 are reasonable.
7. Whether the 20 satellites get the expected orbit type with their real data (RF-03).

## 7. Amendments

| # | Date | Change | Reason | Status |
|---|---|---|---|---|
| 1 | 2026-10-30 | RF-01, RF-03, RF-05, RF-07 and RNF-01, RNF-03, RNF-05 change from 6 to 20 satellites and add period, distance and the catalog; RF-07 accepts a file with one missing satellite; new RF-10 to RF-16 and RNF-07; a priority column is added. | `DESIGN.md` §9, correction of 2026-10-30: 20 satellites, user location, distances and catalog data. | Approved 2026-10-30 |
| 2 | 2026-10-30 | RF-04 and RF-13: the intervals count from the last download attempt, successful or failed, and errors are not retried. Open questions 1 and 5 resolved by ADR-003 and ADR-004. | ADR-003: CelesTrak's usage policy asks clients to stop on any non-200 response. | Approved 2026-10-30 |

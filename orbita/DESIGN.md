# Orbita: project design

> Status: Closed 2026-10-30. Changes after this date are recorded in §9.

> Notice: Orbita is an academic project. Positions and distances are approximate
> (typical error of a few kilometers for positions and a few tens of kilometers for
> distances) and must not be used for space operations.

## 1. Vision

Orbita is a web map that shows in real time where 20 selected satellites from
several countries are, where you are, and how far each satellite is from you.
Each satellite has a card with its country, launch date, years in orbit,
altitude, speed and orbit type.

Positions are computed by the program itself from CelesTrak's public orbital
elements; Orbita does not use satellite imagery. Your location is read from the
browser only while the page is open and is never stored. Predicting passes
visible from your location is planned for v2.

## 2. Users and scenarios

### 2.1 Users

- **Primary:** a student or space enthusiast who wants to see where satellites
  are right now, which country they belong to and how far they are from them.
- **Secondary:** teachers who want to show in class how satellites move and
  how the orbit types differ.

### 2.2 Scenarios

**Scenario 1: how far is the ISS from me?** Laura, an engineering student in
Cali, opens Orbita on her laptop and presses "My location". The browser asks
for permission, she accepts, and a marker appears on Cali. She clicks the ISS:
the card says it belongs to an international partnership, was launched in
1998, flies at about 420 km at about 7.66 km/s, its orbit is low and it is
≈ 2,340 km from her. Every second the point and the distance change.

**Scenario 2: a class about orbits.** A teacher projects Orbita in class. He
compares GOES-19, Himawari-9 and Meteosat-11, which barely move because they
are geostationary, with NOAA-20, which crosses from pole to pole, and with a GPS
satellite, which is in neither group. He uses the cards to show that the
satellites belong to the United States, China, Europe, Japan, India, Russia and
Colombia.

**Scenario 3: walking with the phone (P3).** Andrés opens the published version
of Orbita on his phone and walks across the campus. His marker on the map moves
with him and the distances update.

**Scenario 4: old data or no location.** Orbita has not been able to download
data for 4 days, and the user denied the location permission. The map keeps
working with the saved data, shows the notice "Orbital data from 4 days ago:
positions may be less accurate" and, instead of the distances, the text
"Allow your location to see distances".

## 3. Scope

### 3.1 Satellites

The NORAD numbers marked "to confirm" are fixed in the spec that implements the
list, after checking them on CelesTrak (§8).

| # | Satellite | NORAD number | Why it is in the list |
|---|---|---|---|
| 1 | ISS | 25544 | Crewed station, the protagonist |
| 2 | Tiangong (Tianhe module) | 48274 | Chinese crewed station |
| 3 | Hubble | 20580 | Space telescope |
| 4 | AstroSat | To confirm | Indian telescope in a near-equatorial orbit |
| 5 | One Starlink satellite | To confirm | Internet constellation |
| 6 | FACSAT-2 | To confirm | Colombian satellite (confirm it is still in orbit) |
| 7 | NOAA-20 | 43013 | US weather satellite, polar orbit |
| 8 | Terra | 25994 | NASA Earth observation |
| 9 | Landsat 9 | 49260 | Earth imagery |
| 10 | Sentinel-1A | 39634 | European radar |
| 11 | Sentinel-2A | 40697 | European optical imagery |
| 12 | Envisat | 27386 | Inactive since 2012, one of the largest objects in orbit |
| 13 | Fengyun-3D | To confirm | Chinese weather satellite |
| 14 | Meteor-M 2 | To confirm | Russian weather satellite |
| 15 | Cartosat-3 | To confirm | Indian Earth imagery |
| 16 | GOES-19 (GOES-East) | 60133 | Geostationary over the Americas |
| 17 | Himawari-9 | To confirm | Geostationary over Asia |
| 18 | Meteosat-11 | To confirm | Geostationary over Europe and Africa |
| 19 | One GPS III satellite | To confirm | Navigation (medium orbit) |
| 20 | One Galileo satellite | To confirm | European navigation (medium orbit) |

- Time shown to the user: Colombia time (UTC-5, no daylight saving time).

### 3.2 In scope for v1

Priorities: P1 first; P2 and P3 only when P1 works.

- **P1** World map with the current position of the 20 satellites, recomputed every 1 second.
- **P1** ISS ground track: the last 45 minutes and the next 45 minutes.
- **P1** "My location" button: reads the browser location once and shows it on the map.
- **P1** Approximate distance from you to each satellite (rule 4.4).
- **P1** Card for each satellite: name, altitude (km), speed (km/s), orbit type (rule 4.1),
  period (minutes) and distance to you.
- **P1** Download of the orbital elements from CelesTrak, saved to a local file;
  they are not downloaded on every map update.
- **P1** Date and time of the last download, in Colombia time, and stale data notice (rule 4.2).
- **P2** Card data from the CelesTrak satellite catalog (SATCAT): country, launch date
  and years in orbit (rule 4.6).
- **P3** Location that updates by itself while you move.
- **P3** Published version with HTTPS so it can be opened on a phone.

### 3.3 Out of scope for v1

- Prediction of passes visible from your location (planned for v2).
- Whether a satellite is above your horizon and in which direction to look.
- Searching for or adding satellites other than the 20 in section 3.1.
- Ground tracks of satellites other than the ISS.
- Storing the user's location, or a location history.
- Notifications (email, Telegram, push).
- Native mobile app (the phone uses the published web page).
- Satellite imagery or photos of the Earth.
- 3D globe view.
- User accounts or per-user saved data.

## 4. Domain rules

The rules live in `domain/` and use only the standard library. The orbital
computation (SGP4) is done by an adapter; the domain receives numbers that are
already computed or read from the downloaded data, and decides.

### 4.1 Orbit type

It is computed from two values of the orbital elements: the inclination
(degrees) and the mean motion (revolutions per day). The rules are applied in
this order and the first one that holds wins:

1. **Geostationary:** mean motion between 0.99 and 1.01 revolutions/day and
   inclination < 10°.
2. **Polar:** inclination between 80° and 100°, both included.
3. **Low:** mean motion ≥ 11.25 revolutions/day (one revolution in 128 minutes or less).
4. **Other:** any other case.

### 4.2 Data freshness

Orbital elements:
- Data age = current time − time of the last successful download.
- Age ≤ 3 days: normal.
- 3 days < age ≤ 14 days: positions are shown with the stale data notice.
- Age > 14 days: positions are not shown, because the error grows too large;
  the data-too-old notice is shown.
- Never download more than once every 2 hours, counted from the last download
  attempt, successful or not (CelesTrak policy, ADR-003). An error is not retried:
  the next attempt waits for the next interval.

Satellite catalog (SATCAT):
- Never download more than once every 24 hours, counted from the last download
  attempt: the catalog changes once or twice a day.
- If there is no saved catalog, the card fields that depend on it show "—".

### 4.3 Time

- The domain does not read the clock: it receives the current time as an
  argument (in UTC).
- Conversion to Colombia time is UTC − 5 hours, with no daylight saving time.

### 4.4 Distance to the observer

- Spherical Earth with radius R = 6371 km. A point with latitude φ, longitude λ
  and altitude h becomes x = (R + h)·cos φ·cos λ, y = (R + h)·cos φ·sin λ,
  z = (R + h)·sin φ.
- The observer has altitude h = 0. The distance is the straight line between the
  two points: √((x₁ − x₂)² + (y₁ − y₂)² + (z₁ − z₂)²).
- It is shown in km, rounded to the nearest 10 km, with the sign "≈".
- Without a valid location (rule 4.5), no distance is computed or shown.

### 4.5 Observer location

- Valid if latitude is in [−90, 90] and longitude in [−180, 180]; otherwise it
  is treated as "location unavailable".
- It only lives in memory while the page is open: it is never written to disk,
  to the log or to any service.

### 4.6 Catalog data

- Country: the SATCAT owner code is translated with the `owner_<CODE>` keys of
  `locales/es.json`; an unknown code is shown as it comes.
- Years in orbit = (current date − launch date) in days / 365.25, with 1 decimal.
- Period (minutes) = 1440 / mean motion, rounded to the nearest whole number.

## 5. Requirements (draft)

The numbered and approved version is in `docs/00-requirements.md`.

- Show the 20 satellites and update them every 1 second.
- Draw the ISS ground track (−45 min to +45 min).
- Show the user's location after pressing "My location", and the distance to each satellite.
- Show the card of each satellite (rules 4.1, 4.4 and 4.6).
- Download orbital elements at most every 2 hours and the catalog at most every 24 hours.
- Work without internet using the last saved files.
- Never store the user's location.
- All user-facing text in Spanish.

## 6. Technology

| Need | Candidate tool | Verified? | Notes |
|---|---|---|---|
| Language and environment | Python 3.12 + uv | Yes | Same as Epsilon |
| Orbital computation | Skyfield (uses SGP4) | Yes, official docs | Computes position, altitude and speed |
| Orbital data | CelesTrak GP (JSON) | Yes, free web service, no key | Saved in `data/` |
| Satellite catalog | CelesTrak SATCAT | Yes, format documented by CelesTrak | Owner, launch date, object type |
| HTTP download | httpx | To verify | |
| Web interface | Streamlit | Yes, official docs | `st.fragment(run_every=...)` reruns only one part every second |
| Map | pydeck (`st.pydeck_chart`) with an offline Natural Earth basemap | Yes, official docs; ADR-002 | No map tiles from the internet |
| Browser location | `streamlit-geolocation` | Yes, reviewed in ADR-004 | One-time reading (P1); P3 needs a new ADR |
| Publication (P3) | Streamlit Community Cloud | To verify | Gives HTTPS, required by the browser location |
| Quality | pytest, ruff, mypy, pre-commit, pip-audit, gitleaks | Yes; gitleaks in ADR-006 | Same as Epsilon plus secret scanning |

Decisions that will become an ADR in phase 4:

- Interface and map: Streamlit with fragments, and which map library.
- Data format: CelesTrak JSON instead of text TLE.
- Browser location component.
- Publication with HTTPS (P3).

## 7. Security, data and risks

### 7.1 Credentials and data

- No keys are needed: CelesTrak is public. If one is ever needed, it goes in
  `.env`, which is never committed to git.
- **The user's location is personal data.** It is read only after the user
  presses "My location" and accepts the browser permission; it lives only in
  memory, and it is never written to disk, to the log, to error messages or to
  any external service (rule 4.5).
- The browser only gives the location on HTTPS or `localhost`; this is a
  browser protection and is not bypassed.
- The files downloaded from CelesTrak are treated as untrusted input: their
  format is validated before use, and if they are invalid the previous ones are kept.
- The `data/` folder with the downloaded files is not committed to git.

### 7.2 Risks and mitigations

| Risk | Mitigation |
|---|---|
| CelesTrak down or no internet | Use the last saved files and show their age (rule 4.2) |
| CelesTrak blocks for excessive downloads | At most one download every 2 hours (elements) and every 24 hours (catalog) |
| Incomplete or corrupt downloaded file | Validate before replacing; write to a temporary file and rename |
| The map becomes slow with 20 satellites every second | Refresh only the map with fragments; if that is not enough, move to 2 seconds and record it in an ADR |
| The location leaks to a log or a file | Security rules with a check in every review; tests that search the log |
| The user denies the location, or the laptop gives an inaccurate one | The map works without it; show the accuracy reported by the browser |
| The location component is immature or stops working | Choose it in an ADR; the rest of the app does not depend on it |
| A satellite of the list is no longer in orbit | Confirm the list before implementing; a missing satellite is reported and the rest are shown |
| Wrong positions or distances | Compare the first results with a reference site and record the differences |

## 8. Pending validation

- Confirm that Streamlit with fragments can refresh 20 satellites every 1 second
  without becoming slow.
- Confirm the NORAD numbers of section 3.1 on CelesTrak, and that FACSAT-2 is still in orbit.
- Confirm the SATCAT owner codes needed for the 20 satellites.
- Choose how to read the location continuously (P3, new ADR).
- Choose the reference site to compare positions and distances.
- Check whether the 3 and 14 day thresholds of rule 4.2 are reasonable.
- Confirm that the 20 satellites get the expected orbit type with rule 4.1.

## 9. Corrections

| Date | Section | Change | Reason |
|---|---|---|---|
| 2026-10-30 | 4.2 (former) | The direction formula changes from `round(azimuth / 45)` to `floor(azimuth / 45 + 0.5)`. | Python's `round` rounds 0.5 to the even number: 22.5° gave N instead of NE. Found while writing the RF-05 criterion. |
| 2026-10-30 | 1, 2, 3, 4, 5 | Prediction of passes visible from Cali (former 4.1 and 4.2) is removed from v1 and moved to v2. Rule 4.1 orbit type is added; it was previously fixed in a table. | User decision: v1 is only the real-time map, to finish it sooner. The computed orbit type keeps the domain's own logic. |
| 2026-10-30 | 1, 2, 3, 4, 5, 6, 7, 8 | From 6 to 20 satellites of several countries; user location from the browser and distance to each satellite (rules 4.4 and 4.5); catalog data: country, launch date and years in orbit (rule 4.6); continuous location and HTTPS publication as P3. | User decision after the architecture draft: a more interactive map with location-dependent data. Ordered by priority so the project can be finished with P1 alone. |
| 2026-10-30 | 4.2, 6, 8 | Download intervals count from the last attempt, not the last success, and errors are not retried. Technology table updated with ADR-002, ADR-004 and ADR-006; resolved items removed from §8. | CelesTrak's usage policy (checked for ADR-003): clients must stop on any non-200 response. Counting from the last success would retry on every page load after a failure. |

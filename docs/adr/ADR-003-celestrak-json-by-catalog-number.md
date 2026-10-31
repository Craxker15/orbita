# ADR-003 - CelesTrak JSON (OMM) queried by catalog number, following its usage policy

- Status: Accepted (2026-10-30)

## Context

Orbita needs the orbital elements of 20 satellites and their catalog data. CelesTrak publishes GP data in several
formats. Its documentation states that the 5-digit catalog numbers ran out on 2026-07-11 and that new objects with
6-digit numbers have no GP data in TLE format; JSON and CSV follow the OMM standard and support them. Since
2026-05-09 the default `FORMAT` is CSV. The usage policy says that GP data is updated once every 2 hours, that data
should be downloaded only once per update, that machine clients must stop querying on any non-200 response, and
that ignoring errors sends the client's IP address to the firewall. SATCAT is updated once or twice a day.

## Decision

- Orbital elements: one request per satellite to `https://celestrak.org/NORAD/elements/gp.php?CATNR=<n>&FORMAT=JSON`,
  always with an explicit `FORMAT=JSON`. Skyfield builds each satellite from the OMM fields.
- Catalog: SATCAT in JSON by catalog number, at most once every 24 h; the exact URL is fixed in its spec after
  checking it.
- **The intervals count from the last download attempt, successful or not**, and are shared by all sessions
  (SEC-31). The data age for the freshness rule still counts from the last successful download.
- **No retries:** any non-200 response, timeout or connection error ends the attempt, keeps the saved data and waits
  for the next interval.

## Rejected alternatives

- **TLE text format:** it cannot represent 6-digit catalog numbers, so a satellite of the list could disappear when
  it gets new data.
- **CSV:** smaller, but the values arrive as text without types and need more validation code; JSON size for 20
  satellites is a few kilobytes.
- **One group query (for example, the "active" list):** downloads thousands of satellites to use 20, and CelesTrak
  enforces limits on large datasets.
- **Retrying on errors:** goes against the usage policy and risks a block.

## Consequences

- Correction of `DESIGN.md` §4.2 and amendment 2 of `docs/00-requirements.md` (RF-04 and RF-13 count from the last
  attempt); `security-rules.md` SEC-16 changes from "at most 1 retry" to "no retries".
- A failed download delays new data by up to 2 h; the saved data remains valid for days (`DESIGN.md` §4.2).
- 20 small requests every 2 h; if CelesTrak asks for fewer requests, a new ADR may switch to one query with several
  catalog numbers.

## Affected governing rules

`DESIGN.md` §4.2, §6; `ARCHITECTURE.md` §3, §4; `security-rules.md` SEC-10, SEC-15, SEC-16, SEC-28, SEC-31;
`docs/00-requirements.md` RF-04, RF-13.

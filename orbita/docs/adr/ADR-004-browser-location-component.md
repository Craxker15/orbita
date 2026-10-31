# ADR-004 - Browser location component: streamlit-geolocation (P1)

- Status: Accepted for P1 (2026-10-30). The continuous location of P3 needs a new ADR.

## Context

RF-10 asks for a "My location" button that reads the browser location once. Streamlit has no built-in way to call
the browser's geolocation API, so a third-party component is needed. SEC-22 requires reviewing it before choosing
it. Two candidates exist on PyPI.

Review (2026-10-30, from the repositories):

| Component | License | Popularity | What it does | Risk |
|---|---|---|---|---|
| `streamlit-geolocation` (Steffanic) | MIT | 20 stars, 3 open issues, 14 commits, early versions (0.0.x) | A button that calls `navigator.geolocation.getCurrentPosition` once and returns latitude, longitude, accuracy and more | Small and single purpose; little maintenance |
| `streamlit_js_eval` (aghasemi) | MIT | 93 stars | Evaluates arbitrary JavaScript in the browser; `get_geolocation()` is one of its helpers | Much wider power than needed: a component built to run any JavaScript |

## Decision

Use **`streamlit-geolocation`** for P1, pinned with `==`, only inside `orbita.ui`. Before pinning, its source (a small
component) is read and the exact version, its release date and its open issues are recorded in this ADR. Its output
goes through the domain rule of `DESIGN.md` §4.5 (SEC-14) before use.

## Rejected alternatives

- **`streamlit_js_eval`:** more popular, but a component whose purpose is running arbitrary JavaScript is a larger
  attack surface than a button that only reads the location (least privilege).
- **Writing our own component now:** more work in P1; it stays as the option for P3.

## Consequences

- If the component breaks or is abandoned, only `orbita.ui` changes; the rest does not know it exists (RF-12 keeps
  the page working without location).
- P3 (RF-15) needs continuous reading, which this component does not offer (`getCurrentPosition` reads once). Before
  P3, a new ADR chooses between repeated one-time reads and a minimal own component with `watchPosition`.

## Affected governing rules

`ARCHITECTURE.md` §2 (`orbita.ui`), §7.1; `security-rules.md` SEC-01, SEC-14, SEC-22, SEC-39; `docs/00-requirements.md`
RF-10, RF-12, RF-15.

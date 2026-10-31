# ADR-007 - Continuous location with a minimal own component (P3)

- Status: Accepted (2026-10-31)

## Context

RF-15 needs the user's marker and the distances to follow the user while walking. `streamlit-geolocation` (ADR-004)
calls `getCurrentPosition` once and cannot keep reading. SEC-22 requires reviewing any component before choosing it.

## Decision

Write a minimal Streamlit component of about 60 lines of HTML and JavaScript in `src/orbita/ui/static/geowatch/`.
It calls `navigator.geolocation.watchPosition` with high accuracy, sends each reading to Python with the component
protocol, and stops the watch when the component is removed (the switch turned off or the page closed). It has no
libraries, makes no network request and sends nothing except the reading.

## Rejected alternatives

- Calling `streamlit-geolocation` again on a timer: each call asks the browser for a new position and the page reruns
  every time; it is slower and noisier, and the component is not designed for it.
- `streamlit_js_eval` (ADR-004): it runs arbitrary JavaScript, which is more power than this feature needs.

## Consequences

- The only JavaScript of the project lives in one file, reviewed in the spec 020 tests (no network calls, no `eval`).
- The reading is sent with `postMessage` to the parent page; it is never sent to a server by this component.
- Battery: the watch stops when the switch is off; turning it on again asks for the permission only if the browser
  forgot it.

## Affected governing rules

`security-rules.md` SEC-01, SEC-04, SEC-14, SEC-22, SEC-39; `docs/00-requirements.md` RF-15; `ADR-004`.

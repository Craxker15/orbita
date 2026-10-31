# ADR-005 - HTTPS publication on Streamlit Community Cloud (P3)

- Status: Proposed (2026-10-30). It is accepted or replaced when P3 starts.

## Context

RF-16 asks for an HTTPS address, which the browser requires to give the location on a phone (RF-15). The project is
a free academic portfolio, published from a public GitHub repository.

## Decision (proposed)

Publish on Streamlit Community Cloud, connected to the GitHub repository, which serves the page over HTTPS. The
published version uses its own Streamlit settings: XSRF protection and CORS on, error details hidden from visitors
(SEC-33) and no usage statistics (SEC-18).

## Rejected alternatives (preliminary)

- **A rented server with its own domain and certificate:** cost and server maintenance out of scope for a student
  project.
- **Exposing the laptop with a tunnel:** the laptop would have to stay on, and it opens the developer's machine to
  the internet.

## Consequences

- On the published version the location travels from the phone to Streamlit's server and stays only in its memory;
  the `location_privacy` text says so (SEC-05).
- The settings, limits and terms of the service are checked when P3 starts, before accepting this ADR.

## Affected governing rules

`security-rules.md` SEC-05, SEC-18, SEC-33; `docs/00-requirements.md` RF-15, RF-16, RNF-07.

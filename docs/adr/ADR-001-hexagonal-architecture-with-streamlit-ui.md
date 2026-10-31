# ADR-001 - Hexagonal architecture with a Streamlit interface layer

- Status: Accepted (2026-10-30)

## Context

Orbita mixes pure rules (orbit type, freshness, distance, location validation), external services (CelesTrak), a
numeric library (Skyfield) and a web framework (Streamlit). The rules must be testable without network, browser or
real clock (`ARCHITECTURE.md` §6), and the data source, the propagator or the interface must be replaceable without
rewriting the rules. Unlike Epsilon, the application does not drive its interface: Streamlit runs the page, and the
page calls the program on every interaction and on every 1 s refresh.

## Decision

Hexagonal architecture in six layers (`orbita.domain`, `orbita.ports`, `orbita.app`, `orbita.adapters`, `orbita.ui`
and the entry layer) with the dependency rule of `ARCHITECTURE.md` §2. `orbita.ui` is a driving adapter in its own
layer: it may call `orbita.app` but never `orbita.adapters`. The object graph is built once per process in
`orbita.main` with `st.cache_resource`, the only allowed exception to "no singletons". The user's location enters
through `orbita.ui` as an argument, not through a port.

## Rejected alternatives

- **A single Streamlit script with everything inside:** the rules could not be tested without Streamlit, and a
  change of data source would touch the drawing code.
- **Putting the page in `orbita.adapters`:** it would need to import `orbita.app`, which breaks rule 4 of
  `ARCHITECTURE.md` §2 for every other adapter.
- **A `LocationProvider` port:** the use cases never ask for the location; the user gives it. A port would add an
  interface with no second implementation.

## Consequences

- The domain is tested with plain values; the use cases with fake ports (`Clock`, `SatelliteDataSource`,
  `SatelliteDataStore`, `OrbitPropagator`).
- `tests/test_architecture.py` enforces the dependency rule with `ast`.
- Objects shared through `st.cache_resource` are used by several sessions at once, so their mutable state needs a
  `Lock` (`ARCHITECTURE.md` §6, Concurrency).

## Affected governing rules

`ARCHITECTURE.md` §2, §3, §6 (Concurrency, User location); `security-rules.md` SEC-02, SEC-31.

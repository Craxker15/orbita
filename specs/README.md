# Índice de specs — Órbita

## Reglas de trabajo

1. El orden numérico es el orden de implementación. Una spec no empieza hasta que sus dependencias estén
   implementadas.
2. Una spec = una rama `feature/NNN-nombre` = un `git merge --no-ff` a `main`.
3. Una spec toca como máximo 5 archivos de código o configuración y una sola capa (los `.md` no cuentan).
4. Cada spec tiene un Definition of Done verificable con comandos. No se marca "Implementada" hasta que todas sus
   casillas pasen.
5. Antes del merge se revisa con la lista de chequeo de `security-rules.md` §9.
6. Si al implementar algo de la spec resulta incorrecto, se corrige la spec y se anota en "Correcciones" con fecha,
   cambio y motivo. Nunca se cambia el código para que "pase" sin corregir la spec.
7. Las specs se escriben en español; el código, los docstrings y los logs, en inglés (`ARCHITECTURE.md` §6).
8. Comandos para Windows (PowerShell, en la terminal de VS Code).

## Índice

| # | Spec | Depende de | Prioridad | Estado |
|---|---|---|---|---|
| 000 | [Setup de Python y herramientas de calidad](000-setup-python-calidad.md) | — | Base | Implementada 2026-10-30 |
| 001 | Pre-commit, gitleaks, Streamlit y VS Code | 000 | Base | Implementada 2026-10-30 |
| 002 | Esqueleto de capas y regla de dependencias (`test_architecture.py`) | 000 | Base | Implementada 2026-10-30 |
| 003 | Tipos del dominio y errores | 002 | P1 | Implementada 2026-10-31 |
| 004 | Reglas: tipo de órbita, periodo y tiempo | 003 | P1 | Implementada 2026-10-31 |
| 005 | Reglas: frescura e intervalos de descarga | 003 | P1 | Implementada 2026-10-31 |
| 006 | Reglas: ubicación y distancia | 003 | P1 | Implementada 2026-10-31 |
| 007 | Validación de datos descargados (SEC-10, SEC-28, SEC-29) | 003 | P1 | Lista para implementar |
| 008 | Puertos | 003 | P1 | Lista para implementar |
| 009 | Configuración (`orbita.settings`, `.env.example`) y textos (`locales/es.json`) | 002 | P1 | Lista para implementar |
| 010 | Lista de los 20 satélites con números NORAD confirmados | 003 | P1 | Lista para implementar |
| 011 | Adaptador `CelestrakSource` y batería de entradas maliciosas | 007, 008 | P1 | Lista para implementar |
| 012 | Adaptador `JsonFileStore` | 007, 008 | P1 | Lista para implementar |
| 013 | Adaptadores `SkyfieldPropagator` y `SystemClock` | 008, 010 | P1 | Lista para implementar |
| 014 | Casos de uso `RefreshSatelliteData` y `GetLiveView` | 004-008, 010 | P1 | Lista para implementar |
| 015 | Interfaz: mapa pydeck, mapa base local y fichas | 009, 014 | P1 | Lista para implementar |
| 016 | Interfaz: "Mi ubicación" | 006, 015 | P1 | Lista para implementar |
| 017 | Arranque (`orbita.main`) y prueba de punta a punta | 011-016 | P1 | Lista para implementar |
| 018 | Catálogo SATCAT: país, lanzamiento y años en órbita | 017 | P2 | Lista para implementar |
| 019 | README, SECURITY.md y publicación en GitHub | 017 | Fase 7 | Lista para implementar |
| 020 | Ubicación continua (necesita un ADR nuevo) | 019 | P3 | Lista para implementar |
| 021 | Publicación con HTTPS (ADR-005) | 020 | P3 | Lista para implementar |

## Correcciones

| Fecha | Spec | Cambio | Motivo |
|---|---|---|---|
| 2026-10-30 | 000 | `src/orbita/__init__.py` debe terminar con un salto de línea. | `ruff check` marcó W292 en la primera comprobación. |
| 2026-10-30 | 000 | Se llenó la tabla de versiones fijadas (13 paquetes). | Las versiones se fijan con `uv tree` al implementar, según el paso 6. |
| 2026-10-30 | 002 | Dos líneas del test superaban 100 caracteres; se partieron y la aserción del adaptador se escribió como la pide ruff. | `ruff check` (E501) y `ruff format --check` fallaron. |
| 2026-10-30 | 002 | El bloque Python dentro del `.md` quedó en el formato de ruff. | `ruff format --check` revisa también los bloques de código de los documentos (caso 4 de la spec 000). |
| 2026-10-31 | 002 | La tabla `ALLOWED` del test permite que cada capa importe su propio paquete (por ejemplo, `orbita.domain` dentro del dominio). | Al implementar la spec 003, el test marcó `catalog.py` por importar `elements.py`: un módulo puede depender de otro de su misma capa; la regla prohíbe otras capas y terceros. |
| 2026-10-31 | 003 | El número de tests de la spec pasa de 34 a 41: `pytest` también corre los 7 de `test_architecture.py`. | Al ejecutar el Definition of Done, `pytest` mostró 41 tests. |
| 2026-10-31 | 003 | Se añaden seis campos a `OrbitalElements` (`raan_deg`, `arg_perigee_deg`, `mean_anomaly_deg`, `mean_motion_dot`, `mean_motion_ddot`, `bstar`) con validación. | SGP4 los necesita y el modelo de la spec 003 no los tenía; se corrige en la spec 007. |
| 2026-10-31 | 008 | La spec toca el estado del dominio (`state.py`) y los puertos; se documenta como excepción explícita a la regla 3. | Puertos y estado se definen juntos para que la spec 013 compile. |
| 2026-10-31 | 009 | No se añade `python-dotenv`; `.env` se lee con una función propia. | SEC-39 limita las dependencias. `ARCHITECTURE.md` §8 menciona `python-dotenv` y debe corregirse. |
| 2026-10-31 | 010 | Spec bloqueada: no se pudo consultar CelesTrak desde el entorno de redacción; los 10 NORAD deben confirmarse en celestrak.org. | Sin confirmación, los números serían supuestos. |
| 2026-10-31 | 014 | `LiveView` gana `age_days` para rellenar `{days}` en el aviso de datos viejos. | Sin ese dato, el texto `stale_data` no puede mostrarse. |
| 2026-10-31 | 018 | Se añade `years_in_orbit` a `SatelliteView` y a la ficha; la spec toca tres capas (domain, app, ui) y es excepción documentada a la regla 3. | Las tres capas cambian juntas para mostrar un dato nuevo. |
| 2026-10-31 | 020 | La ubicación continua se decide en ADR-007 (componente propio con `watchPosition`); ADR-004 recibe un addendum. | `streamlit-geolocation` solo lee una vez. |
| 2026-10-31 | 021 | `config.toml` y la clave `location_privacy_published` quedan aplicados. Pendiente al implementar: campo `published` en `Settings`, `PageDependencies` y `main.py`, y generar `requirements.txt` con uv. | Los cambios de código de la spec 021 se describen en prosa y se aplican durante su implementación. |
| 2026-10-31 | 010 | Los 10 NORAD confirmados en SATCAT: AstroSat 40930, FACSAT-2 56205, FENGYUN 3D 43010, METEOR-M 2 40069, CARTOSAT-3 44804, HIMAWARI-9 41836, METEOSAT-11 40732, GPS III SV01 43873, GALILEO 5 40128. Starlink se sustituye por NOAA 19 (33591). | Los Starlink se reentran con frecuencia (p. ej. STARLINK-1130 en 2025); se eligió un satélite estable. |
| 2026-10-31 | 013 | `_omm_fields` incluye `OBJECT_ID` (cadena vacía). | La librería `sgp4` lee `OBJECT_ID` para el designador internacional y falla con `KeyError` si falta; la posición no lo usa. Hallazgo de `pytest` en Windows. |
| 2026-10-31 | 014 | Los archivos de `app` incluyen el campo `years_in_orbit` de la spec 018 (parche aplicado al implementar la 014). | El código ya venía con ese parche desde la rama WIP; se documenta para que la 018 no se repita. |
| 2026-10-31 | 015 | `src/orbita/ui/page.py` no entra en esta spec: importa `location.py` (spec 016). Se implementa con la 016. | Evitar traer código de la 016 a la 015; la spec 015 cubre mapa y fichas. |
| 2026-10-31 | 015 | El test del tooltip comprueba `deck.tooltip` y no el JSON de `to_json()`, que no incluye el tooltip en pydeck. | Hallazgo de `pytest` en Windows; el tooltip sí es texto plano (SEC-13). |
| 2026-10-31 | 016 | No se usa `streamlit-geolocation`: el botón usa el componente propio de ADR-007 en modo `once`. ADR-004 pasa a Superseded. | El paquete no tiene versiones desde 2023-11-18 y SEC-22 exige revisarlo; el componente propio no añade dependencias. |

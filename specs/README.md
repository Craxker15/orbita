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
| 003 | Tipos del dominio y errores | 002 | P1 | Lista para implementar |
| 004 | Reglas: tipo de órbita, periodo y tiempo | 003 | P1 | Por redactar |
| 005 | Reglas: frescura e intervalos de descarga | 003 | P1 | Por redactar |
| 006 | Reglas: ubicación y distancia | 003 | P1 | Por redactar |
| 007 | Validación de datos descargados (SEC-10, SEC-28, SEC-29) | 003 | P1 | Por redactar |
| 008 | Puertos | 003 | P1 | Por redactar |
| 009 | Configuración (`orbita.settings`, `.env.example`) y textos (`locales/es.json`) | 002 | P1 | Por redactar |
| 010 | Lista de los 20 satélites con números NORAD confirmados | 003 | P1 | Por redactar |
| 011 | Adaptador `CelestrakSource` y batería de entradas maliciosas | 007, 008 | P1 | Por redactar |
| 012 | Adaptador `JsonFileStore` | 007, 008 | P1 | Por redactar |
| 013 | Adaptadores `SkyfieldPropagator` y `SystemClock` | 008, 010 | P1 | Por redactar |
| 014 | Casos de uso `RefreshSatelliteData` y `GetLiveView` | 004-008, 010 | P1 | Por redactar |
| 015 | Interfaz: mapa pydeck, mapa base local y fichas | 009, 014 | P1 | Por redactar |
| 016 | Interfaz: "Mi ubicación" | 006, 015 | P1 | Por redactar |
| 017 | Arranque (`orbita.main`) y prueba de punta a punta | 011-016 | P1 | Por redactar |
| 018 | Catálogo SATCAT: país, lanzamiento y años en órbita | 017 | P2 | Por redactar |
| 019 | README, SECURITY.md y publicación en GitHub | 017 | Fase 7 | Por redactar |
| 020 | Ubicación continua (necesita un ADR nuevo) | 019 | P3 | Por redactar |
| 021 | Publicación con HTTPS (ADR-005) | 020 | P3 | Por redactar |

## Correcciones

| Fecha | Spec | Cambio | Motivo |
|---|---|---|---|
| 2026-10-30 | 000 | `src/orbita/__init__.py` debe terminar con un salto de línea. | `ruff check` marcó W292 en la primera comprobación. |
| 2026-10-30 | 000 | Se llenó la tabla de versiones fijadas (13 paquetes). | Las versiones se fijan con `uv tree` al implementar, según el paso 6. |
| 2026-10-30 | 002 | Dos líneas del test superaban 100 caracteres; se partieron y la aserción del adaptador se escribió como la pide ruff. | `ruff check` (E501) y `ruff format --check` fallaron. |
| 2026-10-30 | 002 | El bloque Python dentro del `.md` quedó en el formato de ruff. | `ruff format --check` revisa también los bloques de código de los documentos (caso 4 de la spec 000). |
| 2026-10-31 | 002 | La tabla `ALLOWED` del test permite que cada capa importe su propio paquete (por ejemplo, `orbita.domain` dentro del dominio). | Al implementar la spec 003, el test marcó `catalog.py` por importar `elements.py`: un módulo puede depender de otro de su misma capa; la regla prohíbe otras capas y terceros. |
| 2026-10-31 | 003 | El número de tests de la spec pasa de 34 a 41: `pytest` también corre los 7 de `test_architecture.py`. | Al ejecutar el Definition of Done, `pytest` mostró 41 tests. |

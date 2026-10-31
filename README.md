# Órbita

Mapa web que muestra en tiempo real dónde están 20 satélites, incluida la Estación Espacial Internacional, tu ubicación
(si la permites) y la distancia aproximada a cada uno.

> **Prototipo académico.** Las posiciones y las distancias son aproximadas (un error típico de unos kilómetros en la
> posición y de decenas de kilómetros en la distancia). No las uses para operaciones espaciales.

## Qué hace

- Muestra la posición de 20 satélites de varios países, actualizada cada segundo.
- Dibuja la trayectoria de la ISS desde 45 minutos antes hasta 45 minutos después.
- Con el botón "Mi ubicación" (y tu permiso), muestra tu punto y la distancia a cada satélite. Tu ubicación solo se
  usa mientras la página está abierta y nunca se guarda.
- Funciona sin internet con los últimos datos guardados, y avisa si los datos tienen más de 3 días.

## Cómo se calcula

Las posiciones se calculan en tu equipo con SGP4 (librería Skyfield) a partir de los elementos orbitales públicos de
CelesTrak. No se usan imágenes de satélite. Los detalles están en `DESIGN.md` y en `ARCHITECTURE.md`.

## Instalación y uso (Windows, PowerShell)

Requisitos: Python 3.12 gestionado con [uv](https://docs.astral.sh/uv/).

```powershell
uv sync --locked
Copy-Item .env.example .env
uv run streamlit run src\orbita\main.py
```

Se abre `http://localhost:8501`. La carpeta `data\` se crea sola al descargar los datos.

## Calidad y seguridad

- Pruebas: `uv run pytest -v`. Calidad: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`.
- Hooks de pre-commit (incluido un escáner de secretos): `uv run pre-commit run --all-files`.
- Reglas de seguridad y de privacidad: `security-rules.md`. Cómo reportar una vulnerabilidad: `SECURITY.md`.

## Documentación

- Diseño: `DESIGN.md` · Requisitos: `docs/00-requirements.md` · Arquitectura: `ARCHITECTURE.md`
- Decisiones: `docs/adr/` · Especificaciones de construcción: `specs/`

Los documentos en español (`*.es.md`) son copias de estudio; la versión oficial está en inglés.

## Licencia

Por definir antes de la publicación.

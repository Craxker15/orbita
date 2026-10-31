# 019 - README, SECURITY.md y publicación en GitHub

## Objetivo

Al terminar, el repositorio tiene su documentación pública (`README.md` con el aviso de prototipo y de aproximación, y
`SECURITY.md` con el canal privado para reportar vulnerabilidades), y la configuración del repositorio en GitHub queda
endurecida según SEC-36. La publicación ocurre al final de la fase 7, no antes: el repositorio se crea privado y se hace
público cuando el proyecto esté completo.

## Depende de

- 017 (la aplicación funciona de punta a punta).

## Archivos rectores aplicables

- `security-rules.md` SEC-23 (el aviso de aproximación debe estar en `README.md`, igual que en la página), SEC-36 (2FA,
  protección de `main`, Dependabot, escaneo de secretos y protección contra envío de secretos), SEC-37 (`SECURITY.md`).
- `DESIGN.md` §1 (el aviso de proyecto académico), `docs/00-requirements.es.md` (la lista de requisitos para el README).

## Archivos a crear

1. `README.md`
2. `SECURITY.md`

Son dos documentos; no son código, así que no cuentan para la regla 3.

## Contenido exacto de los archivos

### `README.md`

```markdown
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
```

### `SECURITY.md`

```markdown
# Política de seguridad

## Versiones admitidas

Solo la última versión de la rama `main` recibe correcciones. Órbita es un prototipo académico.

## Cómo reportar una vulnerabilidad

No abras un issue público. Usa la **notificación privada de vulnerabilidades** de GitHub: en la pestaña *Security* del
repositorio, elige *Report a vulnerability*. Incluye los pasos para reproducirla y, si puedes, el archivo o la línea afectada.

Respondemos en un plazo de 14 días. Si la vulnerabilidad se confirma, se corrige en `main` y se describe en el historial
del repositorio sin datos sensibles.

## Qué no es una vulnerabilidad

- Las posiciones o distancias aproximadas (ver el aviso del proyecto).
- Un satélite que deja de estar en la lista por haber salido de órbita.

## Datos personales

La ubicación del usuario se usa solo en memoria mientras la página está abierta y no se guarda (ver `security-rules.md`,
SEC-01 a SEC-05). Si encuentras una forma en que se guarde, en un log o en un servicio externo, repórtalo como una
vulnerabilidad.
```

## Pasos

1. **Crear la rama:** `git switch -c feature/019-readme-seguridad-publicacion`.
2. **Crear los dos archivos** con el contenido de este documento.
3. **Revisar el aviso:** el texto de `README.md` debe coincidir con el `approximate_notice` de `locales\es.json` (SEC-23).
   `Select-String -Path README.md -Pattern 'operaciones espaciales'` debe encontrar la frase.
4. **Commit y merge** con el mensaje `019: readme y politica de seguridad`.
5. **Crear el repositorio en GitHub, privado,** (no se publica todavía). Desde la carpeta `orbita`:
   ```powershell
   gh repo create orbita --private --source . --remote origin
   git push -u origin main
   ```
   Si `gh` no está instalado, se crea el repositorio en la web de GitHub, se copia su dirección y se usa
   `git remote add origin <direccion>` seguido de `git push -u origin main`.
6. **Configurar GitHub (SEC-36):** en *Settings*: activar la autenticación de dos factores de la cuenta; en *Rules*,
   crear una regla para `main` que bloquee el borrado y los envíos forzados; en *Code security*, activar Dependabot
   alerts, Secret scanning y Push protection.
7. **Hacer público el repositorio** solo cuando el proyecto esté completo (al terminar la spec 021): *Settings → Danger
   zone → Change visibility*.

## Casos borde y manejo de errores

1. Un secreto se sube por error: se revoca primero, después se borra del historial; el escáner de pre-commit lo evita
   antes de que llegue a GitHub.
2. Un fallo en la regla de `main`: el push se rechaza; no se desactiva la protección para "arreglarlo".

## Tests de aceptación

- `README.md` contiene el aviso de aproximación y la advertencia de que no sirve para operaciones espaciales.
- `SECURITY.md` explica la notificación privada de GitHub y no pide que se abra un issue público.
- En GitHub, `main` tiene la regla de protección, la autenticación de dos factores está activa, y Dependabot y el escaneo
  de secretos aparecen activados en *Code security*.

## Fuera de alcance

- La licencia: se decide antes de hacer público el repositorio (campo "Licencia" del README).
- El despliegue en la web (HTTPS): spec 021.

## Definition of Done

- [ ] `README.md` y `SECURITY.md` existen y el aviso de `README.md` coincide con `approximate_notice` de `es.json`.
- [ ] `git log --oneline -1` muestra el commit `019: readme y politica de seguridad` tras el merge.
- [ ] El repositorio en GitHub es privado y `main` tiene la regla de protección (captura o revisión manual).
- [ ] Dependabot, Secret scanning y Push protection activos.
- [ ] `git status` → `nothing to commit, working tree clean`.

# 021 - Publicación con HTTPS (P3, ADR-005)

## Objetivo

Al terminar, Órbita está publicada en una dirección HTTPS de Streamlit Community Cloud, abre en un celular, y la
ubicación del navegador funciona ahí (RF-16, RNF-07). El texto de privacidad de la versión publicada dice que la
ubicación viaja al servidor que ejecuta la página y se queda solo en su memoria (SEC-05). Los errores detallados no se
muestran al visitante (SEC-33).

## Depende de

- 020 (ubicación continua, la última función), 019 (repositorio público listo).

## Archivos rectores aplicables

- `ADR-005` (publicación en Streamlit Community Cloud; el ADR pasa de "Proposed" a "Accepted" al empezar esta spec, tras
  revisar sus límites y condiciones).
- `security-rules.md` SEC-05 (texto de privacidad distinto en la versión publicada), SEC-18 (sin estadísticas de uso),
  SEC-19 y SEC-40 (la instalación usa el lockfile), SEC-33 (sin detalles de error, texto `unexpected_error`).

## Archivos a crear o modificar

1. `.streamlit/config.toml` (modificar: añadir la sección `[client]`).
2. `locales/es.json` (modificar: clave `location_privacy_published`).
3. `src/orbita/settings.py` (modificar: variable `ORBITA_PUBLISHED`).
4. `src/orbita/ui/page.py` y `src/orbita/ui/location.py` (modificar: elegir el texto de privacidad).
5. `requirements.txt` (generado desde `uv.lock`, para la plataforma de publicación).
6. `docs/adr/ADR-005-https-publication-streamlit-community-cloud.md` (estado y límites revisados).

## Contenido exacto de los cambios

### `.streamlit/config.toml` (archivo completo)

```toml
[browser]
gatherUsageStats = false

[server]
address = "localhost"
enableXsrfProtection = true
enableCORS = true

[client]
showErrorDetails = "none"
```

Para la publicación, la plataforma usa su propio servidor; el archivo queda versionado con las mismas claves (SEC-18,
SEC-33). `address = "localhost"` solo afecta al desarrollo local.

### Cambios de código

- `locales/es.json`: se añade `"location_privacy_published": "Tu ubicación viaja al servidor que ejecuta esta página y se queda solo en su memoria. Nunca se guarda."`.
- `src/orbita/settings.py`: el dataclass `Settings` gana el campo `published: bool` después de `log_level`; `load_settings`
  lo calcula con `_flag(values.get("ORBITA_PUBLISHED", "false"))`, donde `_flag` acepta solo `true` o `false` (sin
  distinguir mayúsculas) y en otro caso lanza `ConfigError` con el nombre de la variable.
- `.env.example`: se añade `ORBITA_PUBLISHED=false`.
- `src/orbita/ui/location.py`: `location_section(texts, published: bool = False)` muestra
  `location_privacy_published` si `published` es verdadero y `location_privacy` en otro caso.
- `src/orbita/ui/page.py`: `PageDependencies` gana `published: bool`; `render_page` llama a
  `location_section(deps.texts, deps.published)`.
- `src/orbita/main.py`: `build_dependencies` recibe `published` y lo pasa a `PageDependencies`; `_cached_dependencies` y
  `main` lo propagan desde `settings.published`.

## Pasos

1. **Crear la rama:** `git switch -c feature/021-publicacion-https`.
2. **Revisar los límites de Streamlit Community Cloud** (condiciones, versión de Python, tiempo de arranque, límites de
   recursos) en su documentación oficial. Anotar la fecha y los límites en `ADR-005`, y cambiar su estado a
   `Accepted (fecha)`. Si los límites no sirven para el proyecto, se para aquí y se escribe un ADR nuevo.
3. **Aplicar los cambios** de la sección anterior y el archivo `config.toml` completo.
4. **Generar `requirements.txt` desde el lockfile** (SEC-19):
   ```powershell
   uv export --no-hashes --format requirements-txt --no-emit-project > requirements.txt
   ```
   Debe contener solo versiones con `==`. Se añade `requirements.txt` a `git`.
5. **Ejecutar los tests y los checks:** `uv run pytest -v`, `uv run ruff check .`, `uv run mypy src`,
   `uv run pre-commit run --all-files`.
6. **Commit, merge y push:**
   ```powershell
   git add .
   git commit -m "021: publicacion https y configuracion de produccion"
   git switch main
   git merge --no-ff feature/021-publicacion-https -m "Merge spec 021: publicacion https"
   git branch -d feature/021-publicacion-https
   git push
   ```
7. **Publicar en Streamlit Community Cloud** (cuenta con el mismo inicio de sesión de GitHub): *New app* → repositorio
   `orbita` → rama `main` → archivo principal `src/orbita/main.py` → versión de Python 3.12. En *Advanced settings*, no se
   guarda ningún secreto (el proyecto no lo necesita, SEC-21). Anotar la dirección `https://...`.
8. **Probar en un celular** (dirección HTTPS): abrir, pulsar "Mi ubicación", aceptar el permiso, ver el marcador y la
   precisión, y ver las distancias a 390 × 844 sin desplazamiento horizontal (RNF-07).
9. **Hacer público el repositorio** en GitHub (ver la spec 019, paso 7) si no se hizo antes.

## Casos borde y manejo de errores

1. El navegador del celular no da la ubicación fuera de HTTPS: la página lo indica con `location_unavailable`; se
   comprueba que la dirección empieza por `https://`.
2. La plataforma arranca con otra versión de Python: se fija 3.12 en la configuración de la aplicación; si no se puede,
   se para y se escribe un ADR.
3. Un error en la versión publicada: el visitante ve `unexpected_error`, y el detalle queda solo en los registros de la
   plataforma (SEC-33).
4. La primera carga descarga los datos de CelesTrak; si falla, el mapa usa el archivo que haya (si no hay, aparece
   `no_orbital_data`).

## Tests de aceptación

- `config.toml` contiene `gatherUsageStats = false` y `showErrorDetails = "none"`.
- `requirements.txt` existe y todas sus líneas tienen `==`.
- En el celular, la dirección `https://` abre, el mapa se ve sin desplazamiento horizontal y la ubicación funciona.
- El texto de privacidad de la versión publicada aparece junto al botón.

## Fuera de alcance

- Un dominio propio y un servidor propio: fuera del alcance del proyecto (ADR-005).
- Análisis de visitas: fuera del alcance (SEC-18).

## Definition of Done

- [ ] `uv run pytest -v` → todos los tests pasan.
- [ ] `Select-String -Path .streamlit\config.toml -Pattern 'gatherUsageStats = false|showErrorDetails = "none"'` → dos líneas.
- [ ] `Select-String -Path requirements.txt -Pattern '^[^#].*[^=]$'` → sin salida (todas las versiones van con `==`).
- [ ] `ADR-005` tiene estado `Accepted` con fecha y los límites de la plataforma anotados.
- [ ] La dirección `https://` abre en un celular y la ubicación funciona.
- [ ] `git status` → `nothing to commit, working tree clean` después del merge.

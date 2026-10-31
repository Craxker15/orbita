# Reglas de seguridad — Órbita

> Copia de estudio en español. El archivo rector es `security-rules.md` (inglés); si difieren, manda el inglés.
> Estado: Aprobado 2026-10-30.
> Marco: proyecto académico cuyo único dato personal es la ubicación del usuario, que nunca se guarda
> (`DESIGN.md` §7). Requisitos: RF-07, RF-10, RF-12, RF-16, RNF-03 y RNF-05 de `docs/00-requirements.md`.

## 0. Modelo de amenazas

Ningún sistema es 100 % seguro. Estas reglas protegen lo que Órbita tiene, frente a los ataques que tienen sentido
para una página web pública que descarga datos de internet. Cada amenaza apunta a las reglas que la cubren.

| Activo | Amenaza | Ejemplo | Reglas |
|---|---|---|---|
| Ubicación del usuario | Filtración | Las coordenadas terminan en un log, un archivo o una solicitud | SEC-01 a SEC-05, SEC-30 |
| Datos mostrados | Alteración en el camino | Alguien en el Wi-Fi cambia la respuesta de CelesTrak | SEC-26 |
| Datos mostrados | Datos maliciosos o corruptos | Valores absurdos, `NaN`, un archivo gigante o comprimido, un JSON muy anidado | SEC-10, SEC-27 a SEC-29, SEC-38 |
| Navegador del visitante | XSS | Un nombre de satélite que contiene `<script>` | SEC-13, SEC-32 |
| Logs | Inyección en el log | Un nombre descargado con saltos de línea que finge líneas de log | SEC-30 |
| App publicada | Abuso y denegación de servicio | Muchos visitantes hacen que la app sature a CelesTrak, o envían entradas inesperadas | SEC-31, SEC-32 |
| App publicada | Exposición de información y CSRF | Un traceback que muestra rutas y código; una solicitud falsificada | SEC-33 |
| Código y dependencias | Cadena de suministro | Un paquete malicioso o vulnerable | SEC-19, SEC-20, SEC-22, SEC-34, SEC-39, SEC-40 |
| Repositorio | Filtración de secretos o toma del repo | Una clave en un commit; alguien sube a `main` con una contraseña robada | SEC-21, SEC-35 a SEC-37 |

Fuera de alcance: un computador o navegador del usuario comprometido, un ataque a CelesTrak mismo más allá de las
comprobaciones de plausibilidad de SEC-29, y la infraestructura del servicio de publicación.

## 1. Dato personal: la ubicación del usuario

La ubicación identifica dónde está una persona. Solo se lee cuando el usuario la pide, solo vive en memoria y nunca
sale del programa, salvo para dibujar el mapa del propio usuario.

| ID | Regla |
|---|---|
| SEC-01 | La ubicación DEBE leerse solo después de que el usuario presiona "Mi ubicación" y acepta el permiso del navegador. NO DEBE leerse automáticamente al abrir la página. La ubicación continua (P3) DEBE activarla el usuario con un control visible y DEBE poder desactivarse. |
| SEC-02 | La ubicación DEBE vivir solo en `st.session_state` como un `Observer` y pasarse como argumento. NO DEBE escribirse en disco, en una caché en disco ni en ningún archivo. `orbita.adapters` NO DEBE importar ni recibir `Observer`: `grep -rn "Observer" src/orbita/adapters/` vacío. |
| SEC-03 | La ubicación NO DEBE aparecer en logs ni en mensajes de error. `Observer.__repr__` y `Observer.__str__` DEBEN devolver `Observer(<hidden>)`, y sus campos se llaman `latitude` y `longitude` para que la búsqueda de la lista de chequeo los encuentre. Un test ejecuta una vista en vivo con un `Observer` y comprueba que su latitud y su longitud no aparecen en el log capturado (RNF-05). |
| SEC-04 | La ubicación NO DEBE enviarse a ningún servicio externo. El único servidor de red del programa es `celestrak.org` (SEC-15), y ninguna solicitud a CelesTrak lleva la ubicación. El mapa no pide teselas a internet (ADR-002), así que ningún proveedor de mapas conoce la zona que se mira. |
| SEC-05 | Junto al botón "Mi ubicación", la página DEBE mostrar el texto de la clave `location_privacy` de `locales/es.json`, que dice que la ubicación solo se usa para dibujar el mapa y las distancias y nunca se guarda. En la versión publicada (P3), el texto DEBE decir además que la ubicación viaja al servidor que ejecuta la página y solo queda en su memoria. |

## 2. Servicios externos de desarrollo y datos de prueba

| ID | Regla |
|---|---|
| SEC-06 | A los servicios externos de desarrollo (incluidos los asistentes de IA) SOLO se envían documentación y código. NO DEBEN enviarse el archivo `.env`, los logs ni ubicaciones reales de personas. |
| SEC-07 | Toda fixture y todo ejemplo DEBE ser sintético, generado por código. Las ubicaciones de los tests DEBEN ser ficticias o puntos públicos de referencia (por ejemplo, latitud 0 y longitud 0, o el centro de una ciudad), nunca la casa ni la ubicación real de una persona. Las descargas reales de CelesTrak NO DEBEN versionarse como fixtures. |
| SEC-08 | Estas rutas DEBEN estar en `.gitignore`: `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.coverage`, `data/`, `*.log`, `.streamlit/secrets.toml`. |

## 3. Entradas y rutas

| ID | Regla |
|---|---|
| SEC-09 | Los archivos de configuración del proyecto (`locales/es.json`) DEBEN leerse con `json.load` y validarse (claves obligatorias y tipos) antes de usarse. Archivo inválido → `ConfigError` con la ruta y la clave que falla. |
| SEC-10 | Los archivos descargados de CelesTrak son entrada no confiable. Una respuesta de más de 5 MB DEBE rechazarse sin leerla completa. DEBE interpretarse con `json.loads` y cada campo usado DEBE validarse en el dominio antes de usarse: número NORAD en la lista de `DESIGN.md` §3.1, inclinación en [0, 180], movimiento medio en (0, 20], excentricidad en [0, 1), época como fecha UTC válida no más de 1 día en el futuro, nombre como `str` no vacío de máximo 80 caracteres. Archivo inválido → `DataValidationError`, se conserva el archivo anterior y el error queda en el log (RF-07). |
| SEC-11 | Toda ruta que el programa lea o escriba DEBE construirse a partir de `ORBITA_DATA_DIR` o de la raíz del repo con un nombre de archivo fijo del código (`orbital_elements.json`, `satcat.json`). NO DEBE derivarse de contenido descargado (por ejemplo, el nombre de un satélite). |
| SEC-12 | NO DEBEN usarse `pickle`, `eval`, `exec`, `yaml.load` ni `shell=True` en `src/`. |
| SEC-13 | El texto que viene de los datos descargados (nombres de satélites, códigos de dueño) DEBE mostrarse como texto plano. NO DEBE usarse `unsafe_allow_html=True` en `src/`, y los tooltips del mapa NO DEBEN construir HTML con datos descargados. |
| SEC-14 | La ubicación que entrega el navegador DEBE validarse con la regla del dominio de `DESIGN.md` §4.5 antes de usarse; una precisión que no sea un número finito ≥ 0 se ignora. Ubicación inválida → "ubicación no disponible" (RF-12). |

## 4. Base de datos

No aplica en este proyecto: no hay base de datos ni se guardan datos del usuario.

## 5. Red

| ID | Regla |
|---|---|
| SEC-15 | Solo `src/orbita/adapters/celestrak_source.py` DEBE abrir conexiones de red e importar `httpx`. La URL base es la constante del código `https://celestrak.org`. |
| SEC-16 | Toda llamada de red DEBE usar `https://` y un tiempo límite de 10 s, NO DEBE reintentarse (cualquier respuesta distinta de 200, tiempo agotado o error de conexión termina el intento, ADR-003), y DEBE respetar los intervalos de descarga de `DESIGN.md` §4.2 (2 h para los elementos orbitales, 24 h para el catálogo, contadas desde el último intento). |
| SEC-17 | Skyfield DEBE usar sus datos de tiempo incorporados (`load.timescale(builtin=True)`) y NO DEBE descargar archivos de efemérides ni de tiempo durante la ejecución. |
| SEC-18 | `.streamlit/config.toml` DEBE versionarse con `browser.gatherUsageStats = false` (Streamlit no envía estadísticas de uso) y, para el desarrollo local, `server.address = "localhost"` (la página no es accesible desde otros dispositivos de la misma red). La versión publicada (P3) documenta su propia configuración en su ADR. |

## 6. Dependencias y secretos

| ID | Regla |
|---|---|
| SEC-19 | Todas las dependencias DEBEN fijarse con versión exacta (`==`) en `pyproject.toml` y resolverse en un `uv.lock` versionado. La instalación DEBE usar el lockfile (`uv sync --locked`). |
| SEC-20 | `uv run pip-audit` DEBE ejecutarse en pre-commit y no reportar vulnerabilidades sin justificar (las excepciones se documentan en `docs/adr/`). |
| SEC-21 | NO DEBE haber secretos en el código ni en el repositorio. Hoy el proyecto no necesita claves; si algún día se necesita una, vive solo en `.env` (local) o en los secretos del servicio de publicación, y solo se lee en `orbita.settings`. |
| SEC-22 | Antes de elegir el componente de ubicación del navegador y la librería de mapa, DEBEN revisarse su repositorio, licencia, fecha de la última versión y problemas de seguridad abiertos, y registrarse en el ADR que los elige. |

## 7. Honestidad con el usuario

| ID | Regla |
|---|---|
| SEC-23 | La página DEBE mostrar siempre el texto de la clave `approximate_notice` de `locales/es.json` (las posiciones y distancias son aproximadas y no sirven para operaciones espaciales), y `README.md` DEBE contener el mismo aviso. |
| SEC-24 | Toda distancia mostrada DEBE llevar el signo "≈" (`DESIGN.md` §4.4), y junto al marcador del usuario DEBE mostrarse la precisión que informa el navegador. |
| SEC-25 | Con datos orbitales de más de 14 días, la página NO DEBE mostrar posiciones (`DESIGN.md` §4.2, RF-06). |

## 8. Endurecimiento contra ataques

### 8.1 Datos descargados

| ID | Regla |
|---|---|
| SEC-26 | `httpx` DEBE verificar los certificados TLS; `verify=False` NO DEBE aparecer en `src/`. NO DEBEN seguirse redirecciones (`follow_redirects=False`); una respuesta de redirección → `DownloadError`. |
| SEC-27 | El límite de 5 MB de SEC-10 DEBE contar los bytes ya descomprimidos y aplicarse mientras se lee por partes (`iter_bytes`), deteniéndose apenas se supere, para que una respuesta comprimida pequeña no se expanda hasta ser enorme. |
| SEC-28 | El JSON DEBE interpretarse con un `parse_constant` que rechace `NaN`, `Infinity` y `-Infinity` (el `json` de Python los acepta por defecto). El nivel superior DEBE ser una lista de máximo 50 objetos. `ValueError` y `RecursionError` → `DataValidationError`. |
| SEC-29 | Comprobación de plausibilidad: si el movimiento medio de un satélite difiere en más de 5 % del valor guardado, se rechazan los elementos nuevos de ese satélite, se conservan los anteriores y se registra un `WARNING` solo con el número NORAD. |

### 8.2 Logs

| ID | Regla |
|---|---|
| SEC-30 | El texto que viene de los datos descargados y del navegador NO DEBE registrarse en el log. Los logs solo contienen números NORAD, conteos, tamaños en bytes, duraciones, estados y tipos de excepción. |

### 8.3 App publicada

| ID | Regla |
|---|---|
| SEC-31 | Los intervalos de descarga son globales, no por visitante: la hora de la última descarga la comparten todas las sesiones y está protegida con un `Lock`. Ninguna acción de un visitante puede provocar una descarga fuera de los intervalos de `DESIGN.md` §4.2. |
| SEC-32 | La página NO DEBE aceptar archivos subidos ni texto libre: `st.file_uploader`, `st.text_input`, `st.text_area` y `st.chat_input` NO DEBEN aparecer en `src/`. Los únicos controles son botones, interruptores y una selección entre los 20 satélites. |
| SEC-33 | `.streamlit/config.toml` NO DEBE desactivar `server.enableXsrfProtection` ni `server.enableCORS`. La versión publicada DEBE ocultar a los visitantes los detalles de los errores (`client.showErrorDetails` con su valor más restrictivo) y mostrar en su lugar el texto `unexpected_error` de `locales/es.json`. |

### 8.4 Código, dependencias y repositorio

| ID | Regla |
|---|---|
| SEC-34 | ruff DEBE ejecutarse con las reglas `S` (flake8-bandit, análisis estático de seguridad). Todo `# noqa: S<código>` DEBE llevar un comentario que lo justifique. |
| SEC-35 | Un detector de secretos DEBE ejecutarse en pre-commit y bloquear cualquier commit que contenga un secreto. La herramienta (por ejemplo, gitleaks) se elige en un ADR según SEC-22. |
| SEC-36 | GitHub (fase 7): autenticación de dos factores en la cuenta; `main` protegida contra force push y borrado; alertas de Dependabot, secret scanning y push protection activados. |
| SEC-37 | El repositorio DEBE incluir `SECURITY.md`, que explica cómo reportar una vulnerabilidad de forma privada (private vulnerability reporting de GitHub) y qué versión tiene soporte. |
| SEC-38 | DEBE existir una batería de tests de entradas maliciosas, siempre en verde: respuesta de más de 5 MB, respuesta comprimida que se expande a más de 5 MB, `NaN` e `Infinity`, JSON anidado 10 000 niveles, nombre con `<script>`, nombre con un salto de línea, redirección a otro servidor y movimiento medio cambiado en 6 %. Cada caso termina en `DownloadError`, `DataValidationError` o un satélite rechazado, sin cambiar el archivo guardado. |
| SEC-39 | Las dependencias de ejecución son solo las de `DESIGN.md` §6. Agregar una exige un ADR con la revisión de SEC-22. |
| SEC-40 | Los hooks de pre-commit DEBEN fijarse a una versión exacta o ejecutarse con `uv run` usando las versiones de `uv.lock`. |

## 9. Lista de chequeo de seguridad (aplicar en cada implementación)

Una casilla por regla `SEC-NN`, en el mismo orden, con el comando exacto cuando lo hay.

- [ ] ¿La ubicación se lee solo después del botón y del permiso, y la ubicación continua se puede desactivar? (SEC-01)
- [ ] ¿La ubicación se escribe en algún lado o la recibe un adaptador? `grep -rn "Observer" src/orbita/adapters/` vacío (SEC-02)
- [ ] ¿Puede aparecer la ubicación en un log o en un error? Test del repr de `Observer` en verde y `grep -rniE "logger\..*(observer|latitude|longitude)" src/` vacío (SEC-03)
- [ ] ¿Se envía la ubicación a algún servicio? Revisar cada llamada de red del diff (SEC-04)
- [ ] ¿Se muestra el texto `location_privacy` junto al botón? (SEC-05)
- [ ] ¿Se adjuntaron `.env`, logs o ubicaciones reales a un servicio externo durante el desarrollo? (SEC-06)
- [ ] ¿Las fixtures son sintéticas, sin ubicaciones reales ni descargas reales de CelesTrak? `git diff --name-only <base> | grep -E "^data/"` vacío (SEC-07)
- [ ] ¿`.gitignore` contiene todas las rutas de SEC-08? (SEC-08)
- [ ] ¿`locales/es.json` se lee con `json.load` y se valida con `ConfigError`? (SEC-09)
- [ ] ¿Cada campo descargado se valida en el dominio, con el límite de 5 MB, antes de usarse? (SEC-10)
- [ ] ¿Alguna ruta se deriva de contenido descargado? (SEC-11)
- [ ] ¿Se usa `pickle`, `eval`, `exec`, `yaml.load` o `shell=True`? `grep -rnE "pickle|eval\(|exec\(|yaml\.load|shell=True" src/` vacío (SEC-12)
- [ ] ¿El texto descargado se muestra como texto plano? `grep -rn "unsafe_allow_html" src/` vacío (SEC-13)
- [ ] ¿La ubicación del navegador se valida con la regla 4.5 antes de usarse? (SEC-14)
- [ ] ¿Hay imports de red fuera del adaptador de CelesTrak? `grep -rlnE "^(import|from) (httpx|requests|urllib)" src/` devuelve solo `celestrak_source.py` (SEC-15)
- [ ] ¿Toda llamada de red usa `https://`, 10 s de tiempo límite, sin reintentos y los intervalos contados desde el último intento? (SEC-16)
- [ ] ¿Skyfield usa `load.timescale(builtin=True)` y no descarga archivos? (SEC-17)
- [ ] ¿`.streamlit/config.toml` tiene `gatherUsageStats = false` y `address = "localhost"`? (SEC-18)
- [ ] ¿Versiones fijadas con `==` y `uv.lock` actualizado? `uv lock --check` sin errores (SEC-19)
- [ ] ¿`uv run pip-audit` sin vulnerabilidades sin justificar? (SEC-20)
- [ ] ¿Hay secretos en el diff? `git diff <base> | grep -niE "api[_-]?key|token|secret|password"` revisado (SEC-21)
- [ ] ¿Cada componente nuevo de terceros se revisó y quedó en un ADR? (SEC-22)
- [ ] ¿Están `approximate_notice` en la página y el aviso en `README.md`? (SEC-23)
- [ ] ¿Toda distancia lleva "≈" y se muestra la precisión del navegador? (SEC-24)
- [ ] ¿Se ocultan las posiciones con datos de más de 14 días? (SEC-25)
- [ ] ¿Se verifica TLS y se rechazan las redirecciones? `grep -rnE "verify=False|follow_redirects=True" src/` vacío (SEC-26)
- [ ] ¿El límite de 5 MB cuenta bytes descomprimidos mientras se lee por partes? (SEC-27)
- [ ] ¿Se rechazan `NaN` e `Infinity`, con ≤ 50 objetos y `RecursionError` manejado? (SEC-28)
- [ ] ¿Se rechaza un satélite cuyo movimiento medio cambia más de 5 %? (SEC-29)
- [ ] ¿Se registra en el log algún texto descargado o del navegador? Revisar cada `logger.` del diff (SEC-30)
- [ ] ¿La hora de la última descarga la comparten todas las sesiones con un `Lock`? (SEC-31)
- [ ] ¿Hay algún control de subida de archivos o texto libre? `grep -rnE "file_uploader|text_input|text_area|chat_input" src/` vacío (SEC-32)
- [ ] ¿Siguen activas la protección XSRF y CORS, y se ocultan los detalles de error en la versión publicada? (SEC-33)
- [ ] ¿ruff se ejecuta con `S` y cada `# noqa: S` lleva justificación? `grep -rn "noqa: S" src/` revisado (SEC-34)
- [ ] ¿El detector de secretos se ejecuta en pre-commit? (SEC-35)
- [ ] ¿Están activos 2FA, la protección de `main`, Dependabot, secret scanning y push protection? (SEC-36)
- [ ] ¿Existe `SECURITY.md`? (SEC-37)
- [ ] ¿La batería de entradas maliciosas está en verde? (SEC-38)
- [ ] ¿Cada dependencia de ejecución está en `DESIGN.md` §6 o en un ADR? (SEC-39)
- [ ] ¿Los hooks de pre-commit están fijados? (SEC-40)

## 10. Cambios

| Fecha | Regla | Cambio | Motivo |
|---|---|---|---|
| 2026-10-30 | SEC-04, SEC-16 | SEC-16: sin reintentos e intervalos contados desde el último intento (antes: máximo 1 reintento). SEC-04: sin teselas de mapa desde internet. | ADR-003 (política de uso de CelesTrak) y ADR-002 (mapa base sin internet). |

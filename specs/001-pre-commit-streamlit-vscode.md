# 001 - Pre-commit, gitleaks, Streamlit y VS Code

## Objetivo

Al terminar, cada commit pasa por las mismas comprobaciones de calidad y de secretos antes de existir, la configuración
de Streamlit cumple SEC-18 y el proyecto abre en VS Code con el intérprete y el formateador correctos.

## Depende de

- 000 (el paquete `orbita`, `uv.lock` y las herramientas de desarrollo ya están instalados).

## Archivos rectores aplicables

- `security-rules.md` SEC-18 (`.streamlit/config.toml`), SEC-21 y SEC-35 (escáner de secretos antes del commit),
  SEC-22 (revisión de la herramienta), SEC-40 (versiones exactas, `rev` fijado).
- `docs/adr/ADR-006-gitleaks-secret-scanner.md` (gitleaks con el hook oficial, `rev` fijado).
- `ARCHITECTURE.md` §6 (herramientas de calidad).

## Archivos a crear

1. `.pre-commit-config.yaml`
2. `.streamlit/config.toml`
3. `.vscode/settings.json`
4. `.vscode/extensions.json`

Son cuatro archivos, dentro del límite de la regla 3 del índice. Ninguno contiene lógica de la aplicación.

## Requisitos previos

En la terminal de VS Code, desde `...\vscode\orbita`, la spec 000 está implementada y el merge se hizo:

```powershell
git status
uv run ruff --version
```

`git status` debe decir `nothing to commit, working tree clean`. `uv run ruff --version` debe mostrar `ruff 0.17.3`.

Se necesita conexión a GitHub para elegir la versión de gitleaks (paso 2).

## Contenido exacto de los archivos

### `.pre-commit-config.yaml`

En el paso 2 se reemplaza `<VERSIÓN>` por la etiqueta elegida, con el prefijo `v` (por ejemplo `v8.30.0`). No se usa
`pre-commit autoupdate`, porque cambia la versión sin revisión (SEC-40).

```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: <VERSIÓN>
    hooks:
      - id: gitleaks
  - repo: local
    hooks:
      - id: ruff-format
        name: ruff format
        entry: uv run ruff format
        language: system
        types: [python]
      - id: ruff-check
        name: ruff check
        entry: uv run ruff check
        language: system
        types: [python]
      - id: mypy
        name: mypy src
        entry: uv run mypy src
        language: system
        pass_filenames: false
        types: [python]
```

Qué hace cada hook:

| Hook | Cuándo corre | Qué detiene |
|---|---|---|
| `gitleaks` | En cada commit, sobre los archivos en el área de preparación | Claves o contraseñas (SEC-35) |
| `ruff format` | Cuando el commit incluye un `.py` | Formato; si cambia un archivo, el commit se detiene para revisarlo |
| `ruff check` | Cuando el commit incluye un `.py` | Errores de estilo y de seguridad (reglas `S`) |
| `mypy` | Cuando el commit incluye un `.py` | Tipos (`mypy --strict`) |

### `.streamlit/config.toml`

```toml
[browser]
gatherUsageStats = false

[server]
address = "localhost"
enableXsrfProtection = true
enableCORS = true
```

Motivo: SEC-18 (sin estadísticas de uso y solo accesible desde esta computadora) y SEC-33 (la protección XSRF y CORS
quedan activadas).

### `.vscode/settings.json`

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
    "files.eol": "\n",
    "files.insertFinalNewline": true,
    "files.trimTrailingWhitespace": true,
    "editor.formatOnSave": true,
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff"
    }
}
```

Motivo: el intérprete del proyecto es el de `.venv`, el final de línea es LF como exige `.gitattributes`, y guardar
formatea con ruff, igual que el hook.

### `.vscode/extensions.json`

```json
{
    "recommendations": [
        "ms-python.python",
        "charliermarsh.ruff"
    ]
}
```

VS Code muestra un aviso para instalar estas dos extensiones al abrir el proyecto.

## Pasos

1. **Crear la rama de la spec:**
   ```powershell
   git switch -c feature/001-pre-commit-streamlit-vscode
   ```
2. **Elegir la versión de gitleaks:**
   ```powershell
   git ls-remote --tags https://github.com/gitleaks/gitleaks.git
   ```
   La salida lista las etiquetas `refs/tags/vX.Y.Z`. Elegir la más alta que no tenga `-rc`, `-beta` ni `^{}` al final.
   Ojo: las etiquetas se ordenan como texto, así que `v8.9.0` aparece después de `v8.10.0`; comparar los números, no
   la posición. Anotar la versión elegida.
3. **Crear** los cuatro archivos con el contenido de arriba. En `.pre-commit-config.yaml`, reemplazar `<VERSIÓN>`
   por la etiqueta del paso 2.
4. **Instalar el hook en git:**
   ```powershell
   uv run pre-commit install
   ```
   Debe responder `pre-commit installed at .git\hooks\pre-commit`.
5. **Correr todos los hooks sobre todo el repositorio:**
   ```powershell
   uv run pre-commit run --all-files
   ```
   Cada hook debe terminar en `Passed`. Si `ruff format` dice `Failed` porque cambió un archivo, vuelve a correrlo
   (el segundo intento debe pasar) y revisa qué cambió con `git diff`.
6. **Probar que gitleaks bloquea una clave.** Crear un archivo de prueba con una clave falsa de formato AWS, prepararlo
   y tratar de confirmar:
   ```powershell
   Set-Content -Path prueba_secreto.txt -Value "AKIAABCDEFGHIJKLMNOP"
   git add prueba_secreto.txt
   git commit -m "prueba: no debe entrar"
   ```
   El commit debe fallar con `gitleaks....Failed`. Después borrar el archivo y quitarlo del área de preparación:
   ```powershell
   git restore --staged prueba_secreto.txt
   Remove-Item prueba_secreto.txt
   ```
7. **Revisar la configuración de Streamlit:**
   ```powershell
   uv run python -c "import tomllib; print(tomllib.load(open('.streamlit/config.toml','rb')))"
   ```
8. **Commit y merge:**
   ```powershell
   git add .
   git commit -m "001: pre-commit con gitleaks, configuracion de Streamlit y VS Code"
   git switch main
   git merge --no-ff feature/001-pre-commit-streamlit-vscode -m "Merge spec 001: pre-commit con gitleaks, configuracion de Streamlit y VS Code"
   git branch -d feature/001-pre-commit-streamlit-vscode
   ```

## Casos borde y manejo de errores

1. `git ls-remote` no conecta: no inventar una versión; reportar el error completo. Sin la versión, la spec no avanza.
2. `pre-commit install` dice que `core.hooksPath` está definido: pegar el mensaje completo; no borrar la configuración
   de git sin revisar qué la puso.
3. `uv run mypy src` falla en los archivos de la spec 000: no ignorar el error; reportarlo, porque significaría que la
   spec 000 no estaba realmente completa.
4. El hook de gitleaks no descarga (sin red o bloqueado por el antivirus de Windows): reportar el error; no desactivar
   el hook para que pase (SEC-35).
5. El hook de gitleaks encuentra algo en el historial de los documentos: no reescribir el historial en esta spec.
   Reportar el hallazgo con el archivo y la línea.
6. VS Code no usa el intérprete de `.venv`: revisar que aparezca `.venv` en la barra de estado. Si no, usar
   **Python: Select Interpreter** y elegir `.venv`.

## Tests de aceptación

Esta spec no crea tests de pytest. Las comprobaciones son los pasos 5 y 6 y el Definition of Done.

## Fuera de alcance

- `.env.example` y `orbita.settings` (spec 009).
- `pip-audit` como hook de pre-commit: se corre a mano con `uv run pip-audit` (DoD de la spec 000) y en la fase 7.
- Hook de `commit-msg` para bloquear atribuciones de IA: se decide aparte, con una corrección de esta spec si se
  agrega.
- `.streamlit/config.toml` para la versión publicada (SEC-18 y ADR-005, spec 021).

## Definition of Done

Todos los comandos en PowerShell, desde la carpeta `orbita`.

- [ ] `uv run pre-commit --version` → muestra la versión instalada.
- [ ] `Select-String -Path .git\hooks\pre-commit -Pattern 'pre-commit'` → encuentra la línea del hook.
- [ ] `Select-String -Path .pre-commit-config.yaml -Pattern 'rev: v\d+\.\d+\.\d+'` → encuentra la versión de gitleaks
  elegida en el paso 2 (sin `<VERSIÓN>`).
- [ ] `uv run pre-commit run --all-files` → todos los hooks en `Passed`.
- [ ] El commit de prueba del paso 6 falla con `gitleaks....Failed`, y el archivo de prueba ya no existe.
- [ ] `Select-String -Path .streamlit\config.toml -Pattern 'gatherUsageStats = false','address = "localhost"','enableXsrfProtection = true'` → encuentra las tres líneas.
- [ ] `uv run python -c "import json; json.load(open('.vscode/settings.json', encoding='utf-8')); json.load(open('.vscode/extensions.json', encoding='utf-8')); print('ok')"` → `ok`.
- [ ] `git status` antes del commit: solo aparecen los cuatro archivos nuevos.
- [ ] `git log --oneline --graph` → muestra el commit de la spec 001 y el merge.
- [ ] `git status` → `nothing to commit, working tree clean`.
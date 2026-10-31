# Órbita: diseño del proyecto

> Estado: Cerrado 2026-10-30. Los cambios posteriores se anotan en §9.

> Aviso: Órbita es un proyecto académico. Las posiciones y distancias son
> aproximadas (error típico de pocos kilómetros en las posiciones y de unas
> decenas de kilómetros en las distancias) y no sirven para operaciones espaciales.

## 1. Visión

Órbita es un mapa web que muestra en tiempo real dónde están 20 satélites
elegidos de varios países, dónde estás tú y a qué distancia está cada satélite
de ti. Cada satélite tiene una ficha con su país, fecha de lanzamiento, años en
órbita, altura, velocidad y tipo de órbita.

Las posiciones se calculan en el propio programa a partir de los elementos
orbitales públicos de CelesTrak; Órbita no usa imágenes satelitales. Tu
ubicación se lee del navegador solo mientras la página está abierta y nunca se
guarda. La predicción de pasos visibles desde tu ubicación queda para la v2.

## 2. Usuarios y escenarios

### 2.1 Usuarios

- **Principal:** estudiante o aficionado al espacio que quiere ver dónde están
  los satélites ahora, de qué país son y a qué distancia están de él.
- **Secundarios:** profesores que quieren mostrar en clase cómo se mueven los
  satélites y en qué se diferencian los tipos de órbita.

### 2.2 Escenarios

**Escenario 1: ¿a qué distancia está la ISS de mí?** Laura, estudiante de
ingeniería en Cali, abre Órbita en su portátil y presiona "Mi ubicación". El
navegador le pide permiso, ella acepta y aparece un marcador sobre Cali. Hace
clic en la ISS: la ficha dice que pertenece a una alianza internacional, que se
lanzó en 1998, que va a unos 420 km de altura y a unos 7.66 km/s, que su órbita
es baja y que está a ≈ 2340 km de ella. Cada segundo cambian el punto y la
distancia.

**Escenario 2: clase sobre órbitas.** Un profesor proyecta Órbita en clase.
Compara GOES-19, Himawari-9 y Meteosat-11, que casi no se mueven porque son
geoestacionarios, con NOAA-20, que cruza de polo a polo, y con un satélite GPS,
que no está en ninguno de esos dos grupos. Con las fichas muestra que hay
satélites de Estados Unidos, China, Europa, Japón, India, Rusia y Colombia.

**Escenario 3: caminando con el celular (P3).** Andrés abre la versión
publicada de Órbita en su celular y cruza el campus caminando. Su marcador se
mueve con él en el mapa y las distancias se actualizan.

**Escenario 4: datos viejos o sin ubicación.** Órbita lleva 4 días sin poder
descargar datos y el usuario negó el permiso de ubicación. El mapa sigue
funcionando con los datos guardados, muestra el aviso "Datos orbitales de hace
4 días: las posiciones pueden ser menos precisas" y, en lugar de las
distancias, el texto "Permite tu ubicación para ver las distancias".

## 3. Alcance

### 3.1 Satélites

Los números NORAD marcados "Por confirmar" se fijan en la spec que implemente la
lista, después de revisarlos en CelesTrak (§8).

| # | Satélite | Número NORAD | Por qué está en la lista |
|---|---|---|---|
| 1 | ISS | 25544 | Estación tripulada, la protagonista |
| 2 | Tiangong (módulo Tianhe) | 48274 | Estación tripulada china |
| 3 | Hubble | 20580 | Telescopio espacial |
| 4 | AstroSat | Por confirmar | Telescopio indio en órbita casi ecuatorial |
| 5 | Un satélite Starlink | Por confirmar | Constelación de internet |
| 6 | FACSAT-2 | Por confirmar | Satélite colombiano (confirmar que sigue en órbita) |
| 7 | NOAA-20 | 43013 | Meteorológico de EE. UU., órbita polar |
| 8 | Terra | 25994 | Observación de la Tierra de la NASA |
| 9 | Landsat 9 | 49260 | Imágenes de la Tierra |
| 10 | Sentinel-1A | 39634 | Radar europeo |
| 11 | Sentinel-2A | 40697 | Imágenes ópticas europeas |
| 12 | Envisat | 27386 | Inactivo desde 2012, uno de los objetos más grandes en órbita |
| 13 | Fengyun-3D | Por confirmar | Meteorológico chino |
| 14 | Meteor-M 2 | Por confirmar | Meteorológico ruso |
| 15 | Cartosat-3 | Por confirmar | Imágenes de la Tierra de la India |
| 16 | GOES-19 (GOES-East) | 60133 | Geoestacionario sobre América |
| 17 | Himawari-9 | Por confirmar | Geoestacionario sobre Asia |
| 18 | Meteosat-11 | Por confirmar | Geoestacionario sobre Europa y África |
| 19 | Un satélite GPS III | Por confirmar | Navegación (órbita media) |
| 20 | Un satélite Galileo | Por confirmar | Navegación europea (órbita media) |

- Hora mostrada al usuario: hora de Colombia (UTC-5, sin horario de verano).

### 3.2 Entra en la v1

Prioridades: primero P1; P2 y P3 solo cuando P1 funcione.

- **P1** Mapa mundial con la posición actual de los 20 satélites, recalculada cada 1 segundo.
- **P1** Trayectoria de la ISS: los últimos 45 minutos y los próximos 45 minutos.
- **P1** Botón "Mi ubicación": lee una vez la ubicación del navegador y la muestra en el mapa.
- **P1** Distancia aproximada de ti a cada satélite (regla 4.4).
- **P1** Ficha de cada satélite: nombre, altura (km), velocidad (km/s), tipo de órbita
  (regla 4.1), periodo (minutos) y distancia a ti.
- **P1** Descarga de los elementos orbitales de CelesTrak y guardado en un archivo local;
  no se descargan en cada actualización del mapa.
- **P1** Fecha y hora de la última descarga, en hora de Colombia, y aviso de datos
  desactualizados (regla 4.2).
- **P2** Datos de la ficha tomados del catálogo de satélites de CelesTrak (SATCAT): país,
  fecha de lanzamiento y años en órbita (regla 4.6).
- **P3** Ubicación que se actualiza sola mientras te mueves.
- **P3** Versión publicada con HTTPS para abrirla en el celular.

### 3.3 No entra en la v1

- Predicción de pasos visibles desde tu ubicación (planeada para la v2).
- Saber si un satélite está sobre tu horizonte y hacia dónde mirar.
- Buscar o agregar satélites distintos a los 20 de la sección 3.1.
- Trayectorias de satélites distintos a la ISS.
- Guardar la ubicación del usuario o un historial de ubicaciones.
- Notificaciones (correo, Telegram, push).
- App móvil nativa (el celular usa la página web publicada).
- Imágenes satelitales o fotos de la Tierra.
- Vista 3D del globo.
- Cuentas de usuario o datos guardados por usuario.

## 4. Reglas del dominio

Las reglas viven en `domain/` y solo usan la biblioteca estándar. El cálculo
orbital (SGP4) lo hace un adaptador; el dominio recibe números ya calculados o
leídos de los datos descargados, y decide.

### 4.1 Tipo de órbita

Se calcula a partir de dos valores de los elementos orbitales: la inclinación
(grados) y el movimiento medio (vueltas por día). Se aplican en este orden y
gana la primera que se cumpla:

1. **Geoestacionaria:** movimiento medio entre 0.99 y 1.01 vueltas/día e
   inclinación < 10°.
2. **Polar:** inclinación entre 80° y 100°, ambos incluidos.
3. **Baja:** movimiento medio ≥ 11.25 vueltas/día (una vuelta en 128 minutos o menos).
4. **Otra:** cualquier otro caso.

### 4.2 Frescura de los datos

Elementos orbitales:
- Edad de los datos = hora actual − hora de la última descarga correcta.
- Edad ≤ 3 días: normal.
- 3 días < edad ≤ 14 días: se muestran las posiciones con el aviso de datos
  desactualizados.
- Edad > 14 días: no se muestran posiciones, porque el error crece demasiado;
  se muestra el aviso de datos demasiado viejos.
- Nunca se descarga más de una vez cada 2 horas, contadas desde el último intento
  de descarga, haya salido bien o no (política de CelesTrak, ADR-003). Un error no
  se reintenta: el siguiente intento espera al siguiente intervalo.

Catálogo de satélites (SATCAT):
- Nunca se descarga más de una vez cada 24 horas, contadas desde el último intento
  de descarga: el catálogo cambia una o dos veces al día.
- Si no hay catálogo guardado, los campos de la ficha que dependen de él muestran "—".

### 4.3 Tiempo

- El dominio no lee el reloj: recibe la hora actual como argumento (en UTC).
- La conversión a hora de Colombia es UTC − 5 horas, sin horario de verano.

### 4.4 Distancia al observador

- Tierra esférica con radio R = 6371 km. Un punto con latitud φ, longitud λ y
  altura h se convierte en x = (R + h)·cos φ·cos λ, y = (R + h)·cos φ·sin λ,
  z = (R + h)·sin φ.
- El observador tiene altura h = 0. La distancia es la línea recta entre los
  dos puntos: √((x₁ − x₂)² + (y₁ − y₂)² + (z₁ − z₂)²).
- Se muestra en km, redondeada a la decena de km más cercana, con el signo "≈".
- Sin una ubicación válida (regla 4.5), no se calcula ni se muestra la distancia.

### 4.5 Ubicación del observador

- Es válida si la latitud está en [−90, 90] y la longitud en [−180, 180]; si no,
  se trata como "ubicación no disponible".
- Solo vive en memoria mientras la página está abierta: nunca se escribe en
  disco, en el log ni en ningún servicio.

### 4.6 Datos del catálogo

- País: el código de dueño de SATCAT se traduce con las claves `owner_<CÓDIGO>`
  de `locales/es.json`; un código desconocido se muestra tal como llega.
- Años en órbita = (fecha actual − fecha de lanzamiento) en días / 365.25, con 1 decimal.
- Periodo (minutos) = 1440 / movimiento medio, redondeado al entero más cercano.

## 5. Requisitos (borrador)

La versión numerada y aprobada está en `docs/00-requirements.md`.

- Mostrar los 20 satélites y actualizarlos cada 1 segundo.
- Dibujar la trayectoria de la ISS (−45 min a +45 min).
- Mostrar la ubicación del usuario al presionar "Mi ubicación" y la distancia a cada satélite.
- Mostrar la ficha de cada satélite (reglas 4.1, 4.4 y 4.6).
- Descargar los elementos orbitales como máximo cada 2 horas y el catálogo como máximo cada 24 horas.
- Funcionar sin internet usando los últimos archivos guardados.
- No guardar nunca la ubicación del usuario.
- Todo texto visible al usuario en español.

## 6. Tecnología

| Necesidad | Herramienta candidata | ¿Verificada? | Notas |
|---|---|---|---|
| Lenguaje y entorno | Python 3.12 + uv | Sí | Igual que Epsilon |
| Cálculo de órbitas | Skyfield (usa SGP4) | Sí, documentación oficial | Calcula posición, altura y velocidad |
| Datos orbitales | CelesTrak GP (JSON) | Sí, servicio web gratuito sin clave | Se guarda en `data/` |
| Catálogo de satélites | CelesTrak SATCAT | Sí, formato documentado por CelesTrak | Dueño, fecha de lanzamiento, tipo de objeto |
| Descarga HTTP | httpx | Por verificar | |
| Interfaz web | Streamlit | Sí, documentación oficial | `st.fragment(run_every=...)` permite refrescar solo una parte cada segundo |
| Mapa | pydeck (`st.pydeck_chart`) con mapa base de Natural Earth sin internet | Sí, documentación oficial; ADR-002 | Sin teselas de mapa desde internet |
| Ubicación del navegador | `streamlit-geolocation` | Sí, revisado en ADR-004 | Lectura única (P1); la P3 necesita un ADR nuevo |
| Publicación (P3) | Streamlit Community Cloud | Por verificar | Da HTTPS, que la ubicación del navegador exige |
| Calidad | pytest, ruff, mypy, pre-commit, pip-audit, gitleaks | Sí; gitleaks en ADR-006 | Igual que Epsilon más detección de secretos |

Decisiones que irán a un ADR en la fase 4:

- Interfaz y mapa: Streamlit con fragmentos y cuál librería de mapa.
- Formato de datos: JSON de CelesTrak en vez de TLE de texto.
- Componente de ubicación del navegador.
- Publicación con HTTPS (P3).

## 7. Seguridad, datos y riesgos

### 7.1 Credenciales y datos

- No se necesitan claves: CelesTrak es público. Si en el futuro se necesitara
  una, iría en `.env`, que nunca se sube a git.
- **La ubicación del usuario es un dato personal.** Solo se lee después de que
  el usuario presiona "Mi ubicación" y acepta el permiso del navegador; vive solo
  en memoria y nunca se escribe en disco, en el log, en mensajes de error ni en
  ningún servicio externo (regla 4.5).
- El navegador solo entrega la ubicación con HTTPS o en `localhost`; es una
  protección del navegador y no se evita.
- Los archivos descargados de CelesTrak se tratan como entrada no confiable: se
  valida su formato antes de usarlos, y si son inválidos se conservan los anteriores.
- La carpeta `data/` con los archivos descargados no se sube a git.

### 7.2 Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| CelesTrak caído o sin internet | Usar los últimos archivos guardados y mostrar su edad (regla 4.2) |
| CelesTrak bloquea por descargas excesivas | Máximo una descarga cada 2 horas (elementos) y cada 24 horas (catálogo) |
| Archivo descargado incompleto o corrupto | Validar antes de reemplazar; escribir en un archivo temporal y renombrar |
| El mapa se vuelve lento con 20 satélites cada segundo | Refrescar solo el mapa con fragmentos; si no basta, subir a 2 segundos y anotarlo en un ADR |
| La ubicación se filtra a un log o a un archivo | Reglas de seguridad revisadas en cada implementación; tests que buscan en el log |
| El usuario niega la ubicación o el portátil da una imprecisa | El mapa funciona sin ella; se muestra la precisión que informa el navegador |
| El componente de ubicación es inmaduro o deja de funcionar | Elegirlo en un ADR; el resto de la app no depende de él |
| Un satélite de la lista ya no está en órbita | Confirmar la lista antes de implementar; un satélite ausente se informa y se muestran los demás |
| Posiciones o distancias equivocadas | Comparar los primeros resultados con un sitio de referencia y anotar las diferencias |

## 8. Pendiente de validar

- Confirmar que Streamlit con fragmentos puede refrescar 20 satélites cada 1 segundo
  sin volverse lento.
- Confirmar los números NORAD de la sección 3.1 en CelesTrak, y que FACSAT-2 sigue en órbita.
- Confirmar los códigos de dueño de SATCAT que necesitan los 20 satélites.
- Elegir cómo leer la ubicación de forma continua (P3, ADR nuevo).
- Elegir el sitio de referencia para comparar posiciones y distancias.
- Revisar si los umbrales de 3 y 14 días de la regla 4.2 son razonables.
- Confirmar que los 20 satélites quedan en el tipo de órbita esperado con la regla 4.1.

## 9. Correcciones

| Fecha | Sección | Cambio | Motivo |
|---|---|---|---|
| 2026-10-30 | 4.2 (antes) | La fórmula de direcciones pasa de `round(azimut / 45)` a `floor(azimut / 45 + 0.5)`. | `round` de Python redondea 0.5 al par: 22.5° salía N en vez de NE. Hallado al escribir el criterio de RF-05. |
| 2026-10-30 | 1, 2, 3, 4, 5 | Se quita de la v1 la predicción de pasos visibles desde Cali (antes 4.1 y 4.2) y pasa a la v2. Se añade la regla 4.1 de tipo de órbita, que antes estaba fija en una tabla. | Decisión del usuario: la v1 es solo el mapa en tiempo real, para terminarla antes. El tipo de órbita calculado conserva lógica propia en el dominio. |
| 2026-10-30 | 1, 2, 3, 4, 5, 6, 7, 8 | De 6 a 20 satélites de varios países; ubicación del usuario desde el navegador y distancia a cada satélite (reglas 4.4 y 4.5); datos del catálogo: país, fecha de lanzamiento y años en órbita (regla 4.6); ubicación continua y publicación con HTTPS como P3. | Decisión del usuario tras el borrador de arquitectura: un mapa más interactivo con datos según la ubicación. Ordenado por prioridad para poder terminar el proyecto solo con la P1. |
| 2026-10-30 | 4.2, 6, 8 | Los intervalos de descarga se cuentan desde el último intento, no desde la última descarga correcta, y los errores no se reintentan. Tabla de tecnología actualizada con ADR-002, ADR-004 y ADR-006; se quitan de §8 los puntos resueltos. | Política de uso de CelesTrak (revisada para ADR-003): los clientes deben detenerse ante cualquier respuesta distinta de 200. Contar desde la última descarga correcta reintentaría en cada carga de la página tras un fallo. |

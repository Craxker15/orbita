# Requisitos — Órbita

> Estado: Aprobado 2026-10-30. Enmienda 1 (§7) aprobada 2026-10-30. Enmienda 2 (§7) aprobada 2026-10-30.
> Fuente: `DESIGN.md` §1-§5 (diseño cerrado, 2026-10-30; correcciones en `DESIGN.md` §9).

## 1. Alcance

Mapa web que muestra en tiempo real la posición de 20 satélites elegidos de varios países, la trayectoria de la
ISS, la ubicación del usuario y la distancia aproximada del usuario a cada satélite. Cada satélite tiene una ficha
con altura, velocidad, tipo de órbita, periodo, distancia y, del catálogo de satélites de CelesTrak, país, fecha de
lanzamiento y años en órbita. Las posiciones se calculan localmente a partir de los elementos orbitales públicos de
CelesTrak, que se descargan y se guardan en archivos locales. La ubicación del usuario se lee del navegador y nunca
se guarda.

Prioridades: P1 mapa en vivo con los 20 satélites, trayectoria de la ISS, ubicación de una sola lectura y
distancias, ficha de cada satélite, descarga y copia local de los elementos orbitales, aviso de datos
desactualizados; P2 datos del catálogo (país, fecha de lanzamiento, años en órbita); P3 ubicación continua y
publicación con HTTPS.

## 2. Fuera de alcance

- Predicción de pasos visibles desde la ubicación del usuario (planeada para la v2).
- Saber si un satélite está sobre el horizonte del usuario y hacia dónde mirar.
- Satélites distintos a los 20 de `DESIGN.md` §3.1, y trayectorias distintas a la de la ISS.
- Guardar la ubicación del usuario o un historial de ubicaciones.
- Notificaciones (correo, Telegram, push).
- App móvil nativa, vista 3D del globo e imágenes satelitales.
- Cuentas de usuario y datos guardados por usuario.

## 3. Requisitos funcionales

| ID | Prioridad | Requisito | Criterio de aceptación medible |
|---|---|---|---|
| RF-01 | P1 | El sistema DEBE mostrar en un mapa mundial la posición actual de los 20 satélites y actualizarla cada 1 s. | Con la app abierta 60 s, el marcador de la ISS cambia de posición al menos 55 veces. Test del adaptador: dos posiciones de la ISS calculadas con 1 s de diferencia están separadas entre 7 y 8 km. |
| RF-02 | P1 | El sistema DEBE dibujar la trayectoria de la ISS desde 45 min antes hasta 45 min después de la hora actual. | Test: la trayectoria tiene 91 puntos (uno por minuto), el primero en −45 min y el último en +45 min. |
| RF-03 | P1 | El sistema DEBE mostrar una ficha de cada satélite con nombre, altura, velocidad, tipo de órbita según `DESIGN.md` §4.1 y periodo según §4.6. | Al hacer clic en cada uno de los 20 satélites se ven los campos; altura en km con 0 decimales, velocidad en km/s con 2 decimales, periodo en minutos enteros. Test del dominio (inclinación °, movimiento medio vueltas/día): (0.1, 1.0027) → geoestacionaria; (98.7, 14.2) → polar; (80.0, 14.0) → polar; (79.9, 14.0) → baja; (51.6, 15.5) → baja; (55.0, 2.0) → otra. Periodo: 15.5 vueltas/día → 93 min; 1.0027 vueltas/día → 1436 min. |
| RF-04 | P1 | El sistema DEBE descargar los elementos orbitales de CelesTrak como máximo una vez cada 2 h y guardarlos en un archivo local. | Test con reloj simulado y descarga falsa: una segunda solicitud 1 h 59 min después de un intento de descarga, correcto o fallido, no descarga; a las 2 h 0 min sí. Un HTTP 403 simulado no se reintenta. |
| RF-05 | P1 | El sistema DEBE funcionar sin internet usando los últimos archivos guardados. | Con la red desactivada y archivos guardados, la app arranca y muestra las 20 posiciones. |
| RF-06 | P1 | El sistema DEBE aplicar la regla de frescura de los elementos orbitales de `DESIGN.md` §4.2. | Test del dominio: edad 3 días → sin aviso; 3 días + 1 s → aviso y posiciones; 14 días → aviso y posiciones; 14 días + 1 s → aviso de datos demasiado viejos y sin posiciones. |
| RF-07 | P1 | El sistema DEBE rechazar un archivo descargado inválido y conservar el anterior. | Test con una respuesta simulada que no es JSON válido o a la que le faltan campos: el archivo guardado no cambia y el error queda en el log. Un archivo válido al que le falta un satélite se acepta, y ese satélite se informa como ausente. |
| RF-08 | P1 | Sin elementos orbitales guardados y sin internet, el sistema DEBE arrancar y mostrar un mensaje que explique que no hay datos orbitales. | Con `data/` vacía y la red desactivada, la app abre y muestra el texto `no_orbital_data` de `locales/es.json`. |
| RF-09 | P1 | El sistema DEBE mostrar la fecha y hora de la última descarga correcta en hora de Colombia. | Test del dominio: `2026-10-30T03:00:00Z` → `2026-10-29 22:00`. |
| RF-10 | P1 | Cuando el usuario presiona "Mi ubicación" y acepta el permiso del navegador, el sistema DEBE leer la ubicación una vez y mostrarla en el mapa con un marcador. | En `localhost`, al presionar el botón y aceptar, aparece el marcador y la precisión que informa el navegador. Test del dominio de `DESIGN.md` §4.5: (3.45, −76.53) válida; (90.0, 180.0) válida; (90.1, 0.0) inválida; (0.0, −180.1) inválida. |
| RF-11 | P1 | Con una ubicación válida, el sistema DEBE mostrar la distancia aproximada del usuario a cada satélite según `DESIGN.md` §4.4. | Test del dominio: observador (0°, 0°), satélite (0°, 0°, 400 km) → 400 km; observador (0°, 0°), punto (0°, 90°, 0 km) → se muestra "≈ 9010 km". |
| RF-12 | P1 | Si la ubicación se niega, no está disponible o es inválida, el sistema DEBE seguir funcionando sin distancias y mostrar un mensaje. | Al negar el permiso, el mapa muestra los 20 satélites y el texto `location_unavailable` de `locales/es.json` en lugar de las distancias. |
| RF-13 | P2 | El sistema DEBE descargar el catálogo de satélites de CelesTrak como máximo una vez cada 24 h, guardarlo localmente y mostrar en la ficha el país, la fecha de lanzamiento y los años en órbita según `DESIGN.md` §4.6. | Test con reloj simulado: una solicitud 23 h 59 min después de un intento de descarga, correcto o fallido, no descarga; a las 24 h 0 min sí. Test del dominio: lanzamiento `2016-10-30`, fecha actual `2026-10-30` → 10.0 años; código de dueño con clave `owner_<CÓDIGO>` → ese texto; código desconocido `XYZ` → `XYZ`. |
| RF-14 | P2 | Sin catálogo guardado, los campos de la ficha que dependen de él DEBEN mostrar "—". | Sin archivo de catálogo y sin internet, todas las fichas muestran "—" en país, fecha de lanzamiento y años en órbita. |
| RF-15 | P3 | Con la página abierta, el sistema DEBE actualizar el marcador del usuario y las distancias cuando la ubicación cambie. | En la versión publicada abierta en un celular, caminar 100 m mueve el marcador en el mapa. |
| RF-16 | P3 | El sistema DEBE estar publicado en una dirección HTTPS. | La URL publicada empieza por `https://`, abre en un celular y RF-10 funciona ahí. |

## 4. Requisitos no funcionales

| ID | Requisito | Valor medible y unidad |
|---|---|---|
| RNF-01 | Tiempo de cálculo de las posiciones y distancias de los 20 satélites en cada refresco. | ≤ 100 ms en un portátil sin GPU, medido en el log. |
| RNF-02 | Precisión de la posición. | ≤ 5 km de diferencia con el sitio de referencia (`DESIGN.md` §8) para la ISS en 3 instantes, con datos de menos de 1 día. |
| RNF-03 | Uso de la red. | Las únicas llamadas de red del programa son las descargas de CelesTrak (elementos orbitales y catálogo); 0 llamadas por cada refresco del mapa. |
| RNF-04 | Textos al usuario. | El 100 % de los textos al usuario sale de `locales/es.json`; 0 textos al usuario escritos en el código Python. |
| RNF-05 | Datos personales. | La ubicación del usuario aparece en 0 archivos en disco y en 0 líneas del log después de una sesión de 10 min con la ubicación activa; el programa solo escribe en `data/` y en el log. |
| RNF-06 | Navegadores y pantalla. | Funciona en las versiones actuales de Chrome y Firefox a 1366 × 768 sin desplazamiento horizontal. |
| RNF-07 | Pantalla de celular (P3). | La versión publicada funciona en un celular a 390 × 844 sin desplazamiento horizontal. |

## 5. Glosario

| Término | Definición |
|---|---|
| Elementos orbitales | Datos de CelesTrak (formato GP, JSON) que describen una órbita en un momento dado. |
| SATCAT | Catálogo de satélites de CelesTrak: dueño, fecha de lanzamiento y tipo de objeto de cada satélite. |
| SGP4 | Modelo estándar que calcula la posición de un satélite a partir de sus elementos orbitales. |
| Número NORAD | Número único de catálogo de cada satélite (por ejemplo, 25544 para la ISS). |
| Inclinación | Ángulo entre la órbita y el ecuador de la Tierra, en grados: 0° sigue el ecuador, 90° pasa por los polos. |
| Movimiento medio | Número de vueltas alrededor de la Tierra por día. |
| Periodo | Tiempo de una vuelta, en minutos. |
| Tipo de órbita | Clasificación de `DESIGN.md` §4.1: geoestacionaria, polar, baja u otra. |
| Observador | La ubicación del usuario leída del navegador; solo vive en memoria. |
| Trayectoria | Línea en el mapa de los puntos de la Tierra que quedan justo debajo del satélite a lo largo del tiempo. |
| Edad de los datos | Tiempo transcurrido desde la última descarga correcta. |

## 6. Preguntas abiertas

Pendientes de validar (`DESIGN.md` §8); no cambian los requisitos, pero sí las specs que los usan:

1. Si Streamlit con fragmentos puede refrescar 20 satélites cada 1 s (RF-01, RNF-01).
2. Los números NORAD de `DESIGN.md` §3.1, y si FACSAT-2 sigue en órbita.
3. Los códigos de dueño de SATCAT que necesitan los 20 satélites (RF-13).
4. Cómo leer la ubicación de forma continua (RF-15, ADR nuevo antes de la P3).
5. Sitio de referencia para RNF-02.
6. Si los umbrales de 3 y 14 días de RF-06 son razonables.
7. Si los 20 satélites quedan en el tipo de órbita esperado con sus datos reales (RF-03).

## 7. Enmiendas

| # | Fecha | Cambio | Motivo | Estado |
|---|---|---|---|---|
| 1 | 2026-10-30 | RF-01, RF-03, RF-05, RF-07 y RNF-01, RNF-03, RNF-05 pasan de 6 a 20 satélites y agregan periodo, distancia y catálogo; RF-07 acepta un archivo al que le falta un satélite; nuevos RF-10 a RF-16 y RNF-07; se agrega una columna de prioridad. | `DESIGN.md` §9, corrección del 2026-10-30: 20 satélites, ubicación del usuario, distancias y datos del catálogo. | Aprobada 2026-10-30 |
| 2 | 2026-10-30 | RF-04 y RF-13: los intervalos se cuentan desde el último intento de descarga, correcto o fallido, y los errores no se reintentan. Preguntas abiertas 1 y 5 resueltas por ADR-003 y ADR-004. | ADR-003: la política de uso de CelesTrak pide a los clientes detenerse ante cualquier respuesta distinta de 200. | Aprobada 2026-10-30 |

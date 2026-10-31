# Decisiones de arquitectura (ADR) — resumen en español

> Copia de estudio. Los ADR oficiales están en inglés en esta misma carpeta; si difieren, manda el inglés.

Un ADR (Architecture Decision Record) deja escrita una decisión técnica **antes** de implementarla: el contexto, lo
que se decidió, qué alternativas se rechazaron y por qué, y qué consecuencias tiene.

| ADR | Estado | Decisión | Por qué |
|---|---|---|---|
| 001 | Aceptado | Arquitectura hexagonal en seis capas. `orbita.ui` es un adaptador "conductor" en su propia capa, y la ubicación entra como argumento, no como puerto. | Las reglas se prueban sin red, sin navegador y sin reloj real. Streamlit es quien llama al programa, no al revés. |
| 002 | Aceptado | Mapa con pydeck (`st.pydeck_chart`) **sin mapa base de internet**: contornos de países de Natural Earth guardados en `assets/`. | Un mapa con teselas de internet le dice al proveedor qué zona miras, y si haces zoom sobre tu marcador, revela dónde estás. Además, así la app funciona sin internet y pydeck ya viene con Streamlit. |
| 003 | Aceptado | Datos de CelesTrak en JSON, uno por satélite (`CATNR`), con `FORMAT=JSON` explícito. Los intervalos se cuentan **desde el último intento**, y los errores **no se reintentan**. | El formato TLE ya no sirve para satélites nuevos (se acabaron los números de 5 cifras). La política de CelesTrak pide detenerse ante cualquier error, y quien la ignora termina bloqueado. |
| 004 | Aceptado (P1) | `streamlit-geolocation` para el botón "Mi ubicación". | Hace solo una cosa: leer la ubicación una vez. La alternativa (`streamlit_js_eval`) es más popular, pero está hecha para ejecutar cualquier JavaScript: más poder del necesario (mínimo privilegio). |
| 005 | Propuesto (P3) | Publicar en Streamlit Community Cloud con HTTPS. | Es gratis y da HTTPS, que el celular exige para dar la ubicación. Se confirma cuando empiece la P3. |
| 006 | Aceptado | gitleaks como detector de secretos en pre-commit. | Detiene una clave **antes** del commit; GitHub solo la detecta cuando ya es pública. |

## Errores de diseño que encontraron los ADR

Al revisar la política de uso de CelesTrak para el ADR-003 aparecieron dos problemas en documentos ya aprobados:

1. **El intervalo se contaba desde la última descarga correcta.** Si CelesTrak fallaba, cada vez que alguien abriera
   la página se volvería a intentar, y eso es justo lo que lleva a un bloqueo. Ahora se cuenta desde el último
   intento.
2. **SEC-16 permitía 1 reintento.** CelesTrak pide detenerse ante cualquier respuesta distinta de 200. Ahora no hay
   reintentos.

Ambos cambios quedaron anotados en las secciones de correcciones o cambios de cada documento y en la **Enmienda 2**
de los requisitos, que está pendiente de tu aprobación.

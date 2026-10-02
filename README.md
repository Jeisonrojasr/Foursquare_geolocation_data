# FOURSQUARE GEOLOCATION DATA

En este proyecto se desarrolla una automatización en Python para obtener, almacenar y procesar datos geolocalizados provenientes de la API REST de Foursquare. El proyecto surgió de la necesidad de incorporar datos reales de movilidad y puntos de interés a un modelo computacional de epidemiología, tomando como referencia trabajos científicos previos de movilidad humana que se basaban también en información de esta plataforma.

## Motivación

El proceso original requería consultar repetidamente una API externa para distintas zonas geográficas, almacenar las respuestas y posteriormente estructurar los datos para su análisis científico. Hacer todas estas consultas y organizar los archivos manualmente no solo era poco escalable y propenso a errores humanos, sino que presentaba un problema mayor: el riesgo de superar el límite mensual de llamadas disponible en la API por un simple descuido en la ejecución.

Debido a lo anterior, se desarrolló un flujo automatizado que permitiera realizar las extracciones de manera controlada, conservar la inmutabilidad de los datos originales y transformarlos posteriormente a una estructura utilizable.

## Herramientas utilizadas

Utilicé Python para la automatización, integrando librerías como requests para las consultas HTTP y pandas para el modelado de datos. Las respuestas de la API se reciben en formato JSON y se almacenan localmente manteniendo el archivo crudo original, lo que garantiza la trazabilidad del dato.

El flujo incluye:

  -Autenticación segura mediante API key y procesamiento de respuestas JSON.
  -Automatización de consultas iterativas para múltiples zonas geográficas, generando automáticamente nombres de archivos basados en la fecha y ubicación.
  -Un contador de llamadas para controlar estrictamente el consumo de la API, apoyado por un registro de cada solicitud realizada y la capacidad de reanudar el proceso en caso de interrupción.
  -Separé intencionalmente la fase de adquisición de datos de la de procesamiento. De esta forma, los datos originales pueden reutilizarse sin necesidad de volver a consultar la API.


El flujo incluye:

- Consultas HTTP a la API REST de Foursquare, autenticación mediante API key y procesamiento de respuestas JSON.
- Automatización de consultas para múltiples zonas geográficas y generación automática de nombres de archivos con fecha y ubicación.
- Contador de llamadas para controlar el consumo de la API y registro de cada solicitud realizada.
- Modo de simulación para probar el flujo sin consumir llamadas reales.
- Capacidad de reanudar el proceso en caso de interrupción.
- Transformación posterior de los JSON a estructuras tabulares utilizando Python y Pandas.

También separé la adquisición de datos del procesamiento, de forma que los datos originales pudieran reutilizarse sin necesidad de volver a consultar la API.

## Resultados

La automatización convirtió un proceso manual y repetitivo en un pipeline reproducible de adquisición y procesamiento de datos. Permitió ejecutar consultas sobre decenas de zonas geográficas de forma automática y procesar cientos de solicitudes sin exceder nunca la cuota disponible de Foursquare. Además de reducir el riesgo de errores manuales, dejó los datos estructurados y listos para posteriores análisis científicos.

Desde una perspectiva empresarial, el proyecto es directamente trasladable a procesos de integración con servicios externos. Aplica para cualquier entorno en el que sea necesario consumir una API, procesar archivos JSON, orquestar ejecuciones controlando límites de uso y transformar la información para alimentar otros sistemas de análisis.

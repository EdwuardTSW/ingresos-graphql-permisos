# Unidad 2 - Actividad 5: Configurar permisos con GraphQL

**Alumno:** Luis Edwuard Chay Ascorra. Proyecto individual.

## Inicio

1. Copia `.env.example` como `.env` sin publicar credenciales reales.
2. Ejecuta `docker compose up --build`.
3. Abre `http://localhost:8000/graphql`.
4. Ejecuta `IdentificarDatos` de `operaciones.graphql`; en una base nueva los IDs semilla son Ana=1, CAPTURISTA=3 y permisos 3,4,5,7,8, pero confírmalos antes de evidenciar.
5. Selecciona cada operación nombrada e introduce el JSON correspondiente de `variables/`.

Para reiniciar las pruebas con una base limpia: `docker compose down -v` y después `docker compose up --build`.

## Entregables incluidos

- `investigacion.md`: investigación con fuentes oficiales.
- `operaciones.graphql` y `variables/`: operaciones reproducibles y datos de entrada.
- `configuracion_inicial.json` y `configuracion_final.json`: matrices por código.
- `comprobaciones.sql`: consultas y preparación de E06.
- `tests/test_atomicidad.py`: prueba E07. Ejecutar: `python -m unittest tests/test_atomicidad.py`.
- `evidencias.md`: guía de E01 a E10; agregar las capturas en `evidencias/` con esos nombres.

No se incluyen entornos virtuales, bases locales ni credenciales. El proyecto implementa las tres nuevas funcionalidades y conserva cuentas y movimientos para E10.

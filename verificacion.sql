-- Opcional: ejecutar en un cliente conectado a la MISMA base PostgreSQL.
-- Son consultas de lectura. No inicializan ni modifican las tablas.
SELECT current_database() AS base_actual;
SELECT 1 AS conexion_ok;
SELECT to_regclass('public.solicitudes') AS tabla_disponible;
SELECT id, solicitante, equipo, descripcion, estado, creada_en
FROM solicitudes ORDER BY id;
SELECT estado, COUNT(*) AS cantidad
FROM solicitudes GROUP BY estado ORDER BY estado;
-- Cambie los ID 1,2,3,4,5 por los cinco ID NUEVOS creados en su práctica.
SELECT estado, COUNT(*) AS cantidad
FROM solicitudes WHERE id IN (1,2,3,4,5)
GROUP BY estado ORDER BY estado;

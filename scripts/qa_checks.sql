-- Checks de QA (solo SELECT). Ejecutar con el usuario cars_qa.
-- Cada fila devuelve: check, resultado (0 = OK en los de conteo).

-- 1. Tablas esperadas (debe dar 8)
SELECT 'tablas_esperadas' AS chk, COUNT(*) AS valor FROM information_schema.tables
 WHERE table_schema = DATABASE()
   AND table_name IN ('marca','modelo','vehiculo','cliente','empleado','venta','mantenimiento','auditoria_log');

-- 2. FK existentes (debe ser >= 8)
SELECT 'foreign_keys' AS chk, COUNT(*) AS valor FROM information_schema.table_constraints
 WHERE table_schema = DATABASE() AND constraint_type = 'FOREIGN KEY'
   AND table_name IN ('modelo','vehiculo','empleado','venta','mantenimiento');

-- 3. CHECK constraints (debe ser 5)
SELECT 'check_constraints' AS chk, COUNT(*) AS valor FROM information_schema.table_constraints
 WHERE table_schema = DATABASE() AND constraint_type = 'CHECK' AND constraint_name LIKE 'ck\_%';

-- 4. Triggers append-only (debe ser 2; requiere privilegio TRIGGER: con cars_qa sale 0, verificar con admin)
SELECT 'triggers_append_only' AS chk, COUNT(*) AS valor FROM information_schema.triggers
 WHERE trigger_schema = DATABASE() AND event_object_table = 'auditoria_log';

-- 5. Duplicados (todos deben ser 0)
SELECT 'vin_duplicado' AS chk, COUNT(*) AS valor FROM (SELECT vin FROM vehiculo GROUP BY vin HAVING COUNT(*) > 1) d;
SELECT 'documento_duplicado' AS chk, COUNT(*) AS valor FROM (SELECT documento FROM cliente GROUP BY documento HAVING COUNT(*) > 1) d;

-- 6. Huerfanos (todos deben ser 0)
SELECT 'venta_sin_vehiculo' AS chk, COUNT(*) AS valor FROM venta v LEFT JOIN vehiculo x ON x.id = v.vehiculo_id WHERE x.id IS NULL;
SELECT 'venta_sin_cliente' AS chk, COUNT(*) AS valor FROM venta v LEFT JOIN cliente c ON c.id = v.cliente_id WHERE c.id IS NULL;
SELECT 'mant_sin_vehiculo' AS chk, COUNT(*) AS valor FROM mantenimiento m LEFT JOIN vehiculo x ON x.id = m.vehiculo_id WHERE x.id IS NULL;

-- 7. Coherencia estado/venta (ambos deben ser 0)
SELECT 'vendido_sin_venta' AS chk, COUNT(*) AS valor FROM vehiculo v LEFT JOIN venta s ON s.vehiculo_id = v.id WHERE v.estado = 'vendido' AND s.id IS NULL;
SELECT 'venta_con_vehiculo_no_vendido' AS chk, COUNT(*) AS valor FROM venta s JOIN vehiculo v ON v.id = s.vehiculo_id WHERE v.estado <> 'vendido';

-- 8. Formato de VIN invalido (debe ser 0)
SELECT 'vin_formato_invalido' AS chk, COUNT(*) AS valor FROM vehiculo WHERE vin NOT REGEXP '^[A-HJ-NPR-Z0-9]{17}$';

-- 9. Permisos del propio usuario (revisar manualmente: solo SELECT)
SHOW GRANTS FOR CURRENT_USER();

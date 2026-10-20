SELECT rp.id AS relacion_id, r.code AS rol, p.code AS permiso, rp.is_active AS relacion_activa, p.is_active AS permiso_activo FROM role_permissions rp JOIN roles r ON r.id=rp.role_id JOIN permissions p ON p.id=rp.permission_id ORDER BY r.code,p.code;
SELECT role_id, permission_id, COUNT(*) AS repeticiones FROM role_permissions GROUP BY role_id, permission_id HAVING COUNT(*) > 1;
-- E06, ejecutar una a la vez y restaurar: UPDATE roles SET is_active=FALSE WHERE code='CONSULTA';
-- UPDATE roles SET is_active=TRUE WHERE code='CONSULTA';
-- UPDATE permissions SET is_active=FALSE WHERE code='accounts.write';
-- UPDATE permissions SET is_active=TRUE WHERE code='accounts.write';

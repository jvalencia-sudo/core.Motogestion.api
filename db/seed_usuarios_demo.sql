-- ============================================================
-- Seed de usuarios REALES para el taller 1 (demo/plataforma).
-- Login cerrado: se pre-registran por correo (sub NULL hasta el primer login;
-- Auth0 maneja la contraseña al entrar con Google). contrasena_usu = 'auth0_managed'.
--
-- Deja SOLO estos 7 usuarios en el taller 1, reasignando las órdenes de trabajo
-- existentes a los nuevos mecánicos/recepcionistas (para no romper las FK y que la
-- agenda siga teniendo datos). Clientes, motos, productos y OT se conservan.
--
-- Idempotente: se puede correr varias veces.
-- ============================================================
SET app.tenant_id = '1';

-- 1) Nuevos usuarios (juanfelipevalencia268 ya existe como 1000000010 = super-admin)
INSERT INTO usuarios (documento_usu, nombre_usu, apellido_1_usu, apellido_2_usu, correo_usu,
                      contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, cod_prf_usu, cod_rol_prf_usu) VALUES
('1000000011','Santiago','Rincón','Quintana','santiago_rincon23212@elpoli.edu.co','auth0_managed',1,1,NULL,1,1),
('1000000012','Juan','Valencia',NULL,'juan_valencia23212@elpoli.edu.co','auth0_managed',2,1,NULL,2,2),
('1000000013','Juan Felipe','Valencia',NULL,'juanfelipevalencia2004@gmail.com','auth0_managed',2,1,NULL,2,2),
('1000000014','Wesly Andrés','Marín','Pérez','wesly_marin23212@elpoli.edu.co','auth0_managed',2,1,NULL,2,2),
('1000000015','Rogelio','Emilio',NULL,'rogelioemilioyinyin@gmail.com','auth0_managed',3,1,NULL,3,3),
('1000000016','Laura','Herrera',NULL,'yoylauraherrera@gmail.com','auth0_managed',3,1,NULL,3,3)
ON CONFLICT (cod_taller, documento_usu) DO UPDATE
  SET correo_usu = EXCLUDED.correo_usu,
      nombre_usu = EXCLUDED.nombre_usu,
      apellido_1_usu = EXCLUDED.apellido_1_usu,
      apellido_2_usu = EXCLUDED.apellido_2_usu,
      cod_prf_usu = EXCLUDED.cod_prf_usu,
      cod_rol_prf_usu = EXCLUDED.cod_rol_prf_usu;

-- Asegurar que juanfelipevalencia268 (super-admin) exista como Admin
INSERT INTO usuarios (documento_usu, nombre_usu, apellido_1_usu, correo_usu,
                      contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, cod_prf_usu, cod_rol_prf_usu)
VALUES ('1000000010','Juan Felipe','Valencia','juanfelipevalencia268@gmail.com','auth0_managed',1,1,NULL,1,1)
ON CONFLICT (cod_taller, documento_usu) DO UPDATE
  SET correo_usu = EXCLUDED.correo_usu, cod_prf_usu = 1, cod_rol_prf_usu = 1;

-- 2) Reasignar las órdenes de trabajo a los nuevos mecánicos y recepcionistas
UPDATE ordenes_trabajo SET documento_usu_mc_ot='1000000012', documento_usu_rp_ot='1000000015' WHERE consecutivo_ot=1;
UPDATE ordenes_trabajo SET documento_usu_mc_ot='1000000013', documento_usu_rp_ot='1000000016' WHERE consecutivo_ot=2;
UPDATE ordenes_trabajo SET documento_usu_mc_ot='1000000014', documento_usu_rp_ot='1000000015' WHERE consecutivo_ot=3;
UPDATE ordenes_trabajo SET documento_usu_mc_ot='1000000012', documento_usu_rp_ot='1000000016' WHERE consecutivo_ot=4;
UPDATE ordenes_trabajo SET documento_usu_mc_ot='1000000013', documento_usu_rp_ot='1000000015' WHERE consecutivo_ot=5;

-- 3) Reasignar los detalles (quién confirmó) al mecánico de su orden
UPDATE detalle_orden_trabajo SET documento_usu_deto='1000000012' WHERE consecutivo_ot_deto IN (1,4);
UPDATE detalle_orden_trabajo SET documento_usu_deto='1000000013' WHERE consecutivo_ot_deto IN (2,5);
UPDATE detalle_orden_trabajo SET documento_usu_deto='1000000014' WHERE consecutivo_ot_deto = 3;

-- 4) Eliminar los usuarios semilla viejos (ya sin referencias)
DELETE FROM usuarios WHERE documento_usu IN
  ('1000000001','1000000002','1000000003','1000000004','1000000005',
   '1000000006','1000000007','1000000008','1000000009');

-- 5) Verificación
SELECT documento_usu, correo_usu,
       CASE cod_rol_prf_usu WHEN 1 THEN 'Admin' WHEN 2 THEN 'Mecánico' WHEN 3 THEN 'Recepcionista' END AS rol
FROM usuarios ORDER BY cod_rol_prf_usu, documento_usu;

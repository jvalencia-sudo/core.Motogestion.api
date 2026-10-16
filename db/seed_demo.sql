-- ============================================================
-- Seed de DEMO (desarrollo local, CI y BD de test) -- NUNCA producción.
-- ============================================================
-- Se separó de full_schema_v2_multitenant.sql porque db/init-prod/00_init.sh
-- carga ese archivo completo en el primer arranque de producción (volumen
-- vacío): este seed trae un taller y usuarios de ejemplo, incluido un admin
-- marcado es_super_admin=true con contraseña trivial (admin@motogestion.com /
-- admin123) -- no puede quedar en ningún despliegue real.
--
-- Se carga DESPUÉS de full_schema_v2_multitenant.sql en:
--   - db/init/01_load.sql (BD de desarrollo local)
--   - db/init/02_load_test.sql (BD de test local)
--   - .github/workflows/ci.yml (BD de desarrollo y de test en CI)
-- db/init-prod/00_init.sh NO lo carga -- debe seguir así.
--
-- tests/superadmin_test.py reutiliza a este admin demo (sub-1000000001) como
-- fixture de super-admin: si se deja de cargar en test, ese archivo falla.

-- ---- TALLER #1 (migración de los datos actuales) ----
INSERT INTO talleres (cod_taller, nombre_tal, nit_tal, correo_tal, estado_tal, plan_tal)
VALUES (nextval('seq_talleres'), 'MotoGestión Demo', '900000000-1', 'demo@motogestion.com', 'activo', 'Taller');

-- A partir de aquí, todo lo POR TALLER se asigna al taller actual:
SET app.tenant_id = '1';

-- Perfiles y permisos del taller 1 (Admin=cod_prf 1, Mecánico=2, Recepcionista=3,
-- pues seq_perfiles arranca en 1). Cada taller tiene los suyos.
SELECT fn_seed_perfiles_taller(1);

-- Impuestos
INSERT INTO impuestos (cod_imp, nombre_imp, porcentaje_imp) VALUES
(nextval('seq_impuestos'),'IVA',19.00),
(nextval('seq_impuestos'),'IVA Reducido',5.00),
(nextval('seq_impuestos'),'Impuesto al Consumo',8.00),
(nextval('seq_impuestos'),'ICA',1.00),
(nextval('seq_impuestos'),'Excluido',0.00);

-- Productos
INSERT INTO productos (cod_pro, nombre_pro, descripcion_pro, stock_pro, stock_pro_min, cod_est_pro, precio_pro) VALUES
(nextval('seq_productos'),'Aceite Motor 4T 20W50','Aceite lubricante sintético para motores de 4 tiempos, 1 litro',50,10,1,35000),
(nextval('seq_productos'),'Filtro de Aceite Universal','Filtro de aceite compatible 125cc a 200cc',80,15,1,18000),
(nextval('seq_productos'),'Pastillas de Freno Delanteras','Juego de pastillas de freno para disco delantero',60,12,1,45000),
(nextval('seq_productos'),'Llanta Delantera 100/90-18','Llanta tubeless 100/90-18',25,5,1,180000),
(nextval('seq_productos'),'Llanta Trasera 110/90-16','Llanta tubeless 110/90-16',20,5,1,195000),
(nextval('seq_productos'),'Kit de Arrastre Completo','Piñón 14T, corona 42T y cadena 428H-120L',30,8,1,220000),
(nextval('seq_productos'),'Bujía NGK CPR8E','Bujía de encendido resistiva 125cc-200cc',100,20,1,12000),
(nextval('seq_productos'),'Batería 12V 7Ah Libre Mantenimiento','Batería sellada gel 12V 7Ah',35,8,1,95000),
(nextval('seq_productos'),'Mano de Obra - Mantenimiento General','Servicio de mantenimiento general',999,1,1,80000),
(nextval('seq_productos'),'Guaya de Freno Delantera','Cable de freno delantero reforzado',70,15,1,22000);

-- La mano de obra es un SERVICIO: no maneja stock (se cobra por horas/valor).
UPDATE productos SET tipo_pro = 'SERVICIO', stock_pro = NULL, stock_pro_min = NULL
 WHERE nombre_pro = 'Mano de Obra - Mantenimiento General';

-- Productos-Impuestos
INSERT INTO productos_impuestos (cod_pro_imp, cod_imp_pro_imp, cod_pro_pro_imp, porcentaje_pro_imp) VALUES
(nextval('seq_productos_impuestos'),1,1,19.00),
(nextval('seq_productos_impuestos'),1,2,19.00),
(nextval('seq_productos_impuestos'),1,3,19.00),
(nextval('seq_productos_impuestos'),1,4,19.00),
(nextval('seq_productos_impuestos'),1,5,19.00),
(nextval('seq_productos_impuestos'),1,6,19.00),
(nextval('seq_productos_impuestos'),2,7,5.00),
(nextval('seq_productos_impuestos'),1,8,19.00),
(nextval('seq_productos_impuestos'),2,9,5.00),
(nextval('seq_productos_impuestos'),1,10,19.00);

-- Clientes
INSERT INTO clientes (documento_cli, nombre_cli, apellido_1_cli, apellido_2_cli, telefono_cli, correo_cli, direccion_cli) VALUES
('1234567890','Juan','Pérez','García','3001234567','juan.perez@email.com','Calle 45 #23-15, Medellín'),
('9876543210','María','González','López','3109876543','maria.gonzalez@email.com','Carrera 70 #50-30, Medellín'),
('1122334455','Carlos','Ramírez','Martínez','3201122334','carlos.ramirez@email.com','Avenida 80 #32-45, Bello'),
('5544332211','Ana','Torres','Sánchez','3155544332','ana.torres@email.com','Calle 10 #15-20, Envigado'),
('6677889900','Luis','Hernández',NULL,'3006677889','luis.hernandez@email.com','Carrera 43A #5-90, Medellín'),
('2233445566','Andrea','Moreno','Castro','3142233445','andrea.moreno@email.com','Calle 33 #55-12, Itagüí'),
('7788990011','Pedro','Jiménez','Vargas','3187788990','pedro.jimenez@email.com','Carrera 52 #28-40, Medellín'),
('3344556677','Laura','Díaz','Rojas','3003344556','laura.diaz@email.com','Calle 67 #48-25, Sabaneta'),
('8899001122','Diego','Muñoz',NULL,'3108899001','diego.munoz@email.com','Avenida El Poblado #10-50, Medellín'),
('4455667788','Carolina','Ruiz','Fernández','3204455667','carolina.ruiz@email.com','Calle 30 #44-18, La Estrella');

-- Marcas
INSERT INTO marcas (cod_mar, nombre_mar) VALUES
(nextval('seq_marcas'),'Yamaha'),(nextval('seq_marcas'),'Honda'),(nextval('seq_marcas'),'Suzuki'),
(nextval('seq_marcas'),'Kawasaki'),(nextval('seq_marcas'),'Bajaj'),(nextval('seq_marcas'),'AKT'),
(nextval('seq_marcas'),'BMW'),(nextval('seq_marcas'),'Ducati'),(nextval('seq_marcas'),'KTM'),
(nextval('seq_marcas'),'Auteco');

-- Motos
INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot) VALUES
('ABC123',2020,'Negro',150,'1234567890',1),
('DEF456',2018,'Rojo',125,'1234567890',2),
('GHI789',2021,'Azul',200,'9876543210',3),
('JKL012',2019,'Blanco',180,'1122334455',4),
('MNO345',2022,'Verde',250,'1122334455',4),
('PQR678',2020,'Gris',110,'5544332211',5),
('STU901',2021,'Negro',125,'6677889900',6),
('VWX234',2023,'Rojo',300,'2233445566',7),
('YZA567',2022,'Amarillo',160,'7788990011',1),
('BCD890',2019,'Naranja',200,'7788990011',9),
('EFG123',2020,'Morado',150,'3344556677',10),
('HIJ456',2021,'Negro',650,'8899001122',8),
('KLM789',2023,'Blanco',125,'4455667788',2),
('NOP012',2022,'Azul',150,'4455667788',1),
('QRS345',2018,'Plateado',180,'9876543210',3),
('TUV678',2020,'Negro Mate',200,'1234567890',4);

-- Usuarios
INSERT INTO usuarios (documento_usu, nombre_usu, apellido_1_usu, apellido_2_usu, correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, cod_prf_usu, cod_rol_prf_usu) VALUES
('1000000001','Admin','Sistema',NULL,'admin@motogestion.com','admin123',1,1,'sub-1000000001',1,1),
('1000000002','Sofia','Martínez','Restrepo','sofia.martinez@motogestion.com','recep123',2,1,'sub-1000000002',3,3),
('1000000003','Valentina','López','García','valentina.lopez@motogestion.com','recep123',2,1,'sub-1000000003',3,3),
('1000000004','Camila','Rodríguez','Pérez','camila.rodriguez@motogestion.com','recep123',2,1,'sub-1000000004',3,3),
('1000000005','Isabella','Gómez','Moreno','isabella.gomez@motogestion.com','recep123',2,1,'sub-1000000005',3,3),
('1000000006','Miguel','Hernández','Torres','miguel.hernandez@motogestion.com','meca123',2,1,'sub-1000000006',2,2),
('1000000007','Andrés','Ramírez','Castro','andres.ramirez@motogestion.com','meca123',2,1,'sub-1000000007',2,2),
('1000000008','Santiago','Vargas','Muñoz','santiago.vargas@motogestion.com','meca123',2,1,'sub-1000000008',2,2),
('1000000009','Sebastián','Jiménez','Ruiz','sebastian.jimenez@motogestion.com','meca123',2,1,'sub-1000000009',2,2);

-- F0-14: el admin demo es el super-admin de plataforma (seed/CI/local).
UPDATE usuarios SET es_super_admin = true WHERE documento_usu = '1000000001';

-- Órdenes de trabajo (consecutivo explícito por taller)
INSERT INTO ordenes_trabajo (consecutivo_ot, fecha_elaboracion_ot, placa_mot_ot, kilometraje_ingreso_ot, documento_usu_rp_ot, documento_usu_mc_ot, observacion_cli_ot, observacion_ot, cod_ot_est_ot) VALUES
(1, DATE '2025-11-20','ABC123',15000,'1000000002','1000000006','La moto hace ruido al frenar','Revisar frenos',1);
INSERT INTO ordenes_trabajo (consecutivo_ot, fecha_elaboracion_ot, fecha_entrega_ot, placa_mot_ot, kilometraje_ingreso_ot, documento_usu_rp_ot, documento_usu_mc_ot, observacion_cli_ot, observacion_ot, cod_ot_est_ot) VALUES
(2, DATE '2025-11-21', DATE '2025-11-23','GHI789',28000,'1000000003','1000000007','Llantas desgastadas','Instalar y balancear',2),
(3, DATE '2025-11-19', DATE '2025-11-22','JKL012',42000,'1000000004','1000000008','Cadena desgastada','Listo para entrega',3);
INSERT INTO ordenes_trabajo (consecutivo_ot, fecha_elaboracion_ot, fecha_entrega_ot, placa_mot_ot, kilometraje_ingreso_ot, documento_usu_rp_ot, documento_usu_mc_ot, observacion_cli_ot, observacion_ot, fecha_fin_garantia_ot, cod_ot_est_ot) VALUES
(4, DATE '2025-11-15', DATE '2025-11-16','PQR678',8500,'1000000005','1000000009','No enciende','Batería reemplazada', DATE '2025-12-16',4);
INSERT INTO ordenes_trabajo (consecutivo_ot, fecha_elaboracion_ot, fecha_entrega_ot, placa_mot_ot, kilometraje_ingreso_ot, documento_usu_rp_ot, documento_usu_mc_ot, observacion_cli_ot, observacion_ot, cod_ot_est_ot) VALUES
(5, DATE '2025-11-23', DATE '2025-11-25','VWX234',35000,'1000000002','1000000006','Mantenimiento 35.000 km','Pendiente aprobación',1);

-- Detalles de OT
INSERT INTO detalle_orden_trabajo (consecutivo_ot_deto, cod_pro_deto, cantidad_deto, valor_unitario_deto, documento_usu_deto, fecha_confirmacion_deto) VALUES
(1,1,2,35000,'1000000006', DATE '2025-11-20'),
(1,2,-1,18000,'1000000006', DATE '2025-11-20'),
(1,3,1,45000,'1000000006', DATE '2025-11-20'),
(1,9,1,80000,'1000000006', DATE '2025-11-20'),
(2,4,1,180000,'1000000007', DATE '2025-11-21'),
(2,5,1,195000,'1000000007', DATE '2025-11-21'),
(2,9,1,80000,'1000000007', DATE '2025-11-21'),
(3,6,1,220000,'1000000008', DATE '2025-11-19'),
(3,1,1,35000,'1000000008', DATE '2025-11-19'),
(3,9,2,80000,'1000000008', DATE '2025-11-19'),
(4,8,1,95000,'1000000009', DATE '2025-11-15'),
(4,7,-1,12000,'1000000009', DATE '2025-11-15'),
(4,9,1,80000,'1000000009', DATE '2025-11-15'),
(5,1,3,35000,'1000000006', DATE '2025-11-23'),
(5,2,1,18000,'1000000006', DATE '2025-11-23'),
(5,7,-2,12000,'1000000006', DATE '2025-11-23'),
(5,10,1,22000,'1000000006', DATE '2025-11-23'),
(5,3,1,45000,'1000000006', DATE '2025-11-23'),
(5,9,3,80000,'1000000006', DATE '2025-11-23');

-- Avanzar secuencias de surrogates al máximo insertado (por si se insertan más luego)
SELECT setval('seq_marcas',    (SELECT MAX(cod_mar) FROM marcas));
SELECT setval('seq_productos', (SELECT MAX(cod_pro) FROM productos));
SELECT setval('seq_impuestos', (SELECT MAX(cod_imp) FROM impuestos));
SELECT setval('seq_productos_impuestos', (SELECT MAX(cod_pro_imp) FROM productos_impuestos));

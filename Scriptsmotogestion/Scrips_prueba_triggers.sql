--------------------------------------------------------------------------------
-- SCRIPT DE PRUEBAS PARA TRIGGERS MOTOGESTION
-- Usa la estructura real que compartiste (CREATES + ALTER)
-- No crea tablas ni constraints, solo inserta y prueba reglas.
--------------------------------------------------------------------------------

PROMPT =============================================
PROMPT = INICIO DE PRUEBAS DE TRIGGERS MOTOGESTIÓN =
PROMPT =============================================

--------------------------------------------------------------------------------
-- 0. DATOS BASE MÍNIMOS (ESTADOS, ROLES, PERFILES, CLIENTES, MARCAS)
--------------------------------------------------------------------------------

PROMPT ---- Insertando ESTADOS base ----

INSERT INTO estados (cod_est, nombre_est)
VALUES (1, 'ACTIVO');

INSERT INTO estados (cod_est, nombre_est)
VALUES (2, 'INACTIVO');

PROMPT ---- Insertando ROLES base ----

INSERT INTO roles (cod_rol, nombre_rol, descripcion_rol)
VALUES (1, 'ADMIN', 'Rol administrador base');

PROMPT ---- Insertando PERFILES base ----

INSERT INTO perfiles (cod_prf, nombre_prf, descripcion_prf, cod_est_prf, cod_rol_prf)
VALUES (1, 'Perfil Admin', 'Perfil administrador general', 1, 1);

PROMPT ---- Insertando CLIENTES base ----

INSERT INTO clientes (documento_cli, nombre_cli, apellido_1_cli, apellido_2_cli, telefono_cli, correo_cli, direccion_cli)
VALUES ('1001', 'Juan', 'Pérez', 'Gómez', '3001234567', 'juan.perez@example.com', 'Dirección 1');

INSERT INTO clientes (documento_cli, nombre_cli, apellido_1_cli, apellido_2_cli, telefono_cli, correo_cli, direccion_cli)
VALUES ('1003', 'Carlos', 'Jiménez', 'López', '3109876543', 'carlos@example.com', 'Dirección 2');

PROMPT ---- Insertando MARCAS base ----

INSERT INTO marcas (cod_mar, nombre_mar)
VALUES (1, 'Yamaha');

--------------------------------------------------------------------------------
-- 1. PRUEBAS CLIENTES (tg_val_correo_cli, tg_val_telefono_cli)
--------------------------------------------------------------------------------

PROMPT ---- PRUEBA: Correo inválido (debe fallar ORA-20001) ----

BEGIN
    INSERT INTO clientes (documento_cli, nombre_cli, apellido_1_cli, apellido_2_cli, telefono_cli, correo_cli, direccion_cli)
    VALUES ('1002', 'Ana', 'López', 'Martínez', '3001234567', 'correo_malo', 'Dirección X');
END;
/

PROMPT ---- PRUEBA: Teléfono inválido (debe fallar ORA-20002) ----

BEGIN
    INSERT INTO clientes (documento_cli, nombre_cli, apellido_1_cli, apellido_2_cli, telefono_cli, correo_cli, direccion_cli)
    VALUES ('1004', 'Laura', 'Martínez', 'Rojas', '31A987654', 'laura@example.com', 'Dirección Y');
END;
/

COMMIT;

--------------------------------------------------------------------------------
-- 2. MOTOS + OT_ESTADOS + USUARIOS (para probar motos y ordenes_trabajo)
--------------------------------------------------------------------------------

PROMPT ---- Insertando MOTO base válida ----

INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
VALUES ('ABC123', 2020, 'Negro', 150, '1001', 1);

PROMPT ---- Insertando ESTADOS de OT ----

INSERT INTO ot_estados (cod_ot_est, nombre_ot_est)
VALUES (1, 'Completada');

INSERT INTO ot_estados (cod_ot_est, nombre_ot_est)
VALUES (2, 'En proceso');

PROMPT ---- Insertando USUARIOS base ----

INSERT INTO usuarios (
    documento_usu, nombre_usu, apellido_1_usu, apellido_2_usu,
    correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu,
    sub_id_usu, cod_prf_usu, cod_rol_prf_usu
) VALUES (
    '9001', 'Pedro', 'Ramírez', 'Gómez',
    'pedro@example.com', 'pass123', 1, 1,
    'sub-9001', 1, 1
);

INSERT INTO usuarios (
    documento_usu, nombre_usu, apellido_1_usu, apellido_2_usu,
    correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu,
    sub_id_usu, cod_prf_usu, cod_rol_prf_usu
) VALUES (
    '9002', 'Luis', 'Torres', 'López',
    'luis@example.com', 'pass123', 1, 1,
    'sub-9002', 1, 1
);

COMMIT;

--------------------------------------------------------------------------------
-- 3. PRODUCTOS (para detalle_orden_trabajo y triggers de productos)
--------------------------------------------------------------------------------

PROMPT ---- Insertando PRODUCTO base (stock suficiente) ----

INSERT INTO productos (
    cod_pro, nombre_pro, descripcion_pro,
    stock_pro, stock_pro_min, cod_est_pro, precio_pro
) VALUES (
    1, 'Aceite 4T', 'Aceite de motor 4 tiempos',
    10, 2, 1, 35000
);

COMMIT;

--------------------------------------------------------------------------------
-- 4. ORDENES_TRABAJO base (para probar TG de OT y detalle)
--------------------------------------------------------------------------------

PROMPT ---- Insertando ORDENES_TRABAJO base ----

-- OT 1: Completada, datos válidos
INSERT INTO ordenes_trabajo (
    consecutivo_ot, fecha_elaboracion_ot, fecha_entrega_ot,
    kilometraje_ingreso_ot, kilometreje_salida_ot,
    observacion_cli_ot, observacion_ot,
    placa_mot_ot, documento_usu_rp_ot, documento_usu_mc_ot,
    cod_ot_est_ot, fecha_fin_garantia_ot
) VALUES (
    1, SYSDATE - 1, SYSDATE,
    5000, NULL,
    'Cliente satisfecho', 'Sin novedades',
    'ABC123', '9001', '9002',
    1, NULL
);

-- OT 2: En proceso, misma moto
INSERT INTO ordenes_trabajo (
    consecutivo_ot, fecha_elaboracion_ot, fecha_entrega_ot,
    kilometraje_ingreso_ot, kilometreje_salida_ot,
    observacion_cli_ot, observacion_ot,
    placa_mot_ot, documento_usu_rp_ot, documento_usu_mc_ot,
    cod_ot_est_ot, fecha_fin_garantia_ot
) VALUES (
    2, SYSDATE - 1, SYSDATE,
    8000, NULL,
    'Cliente reporta ruido', 'Revisión en curso',
    'ABC123', '9001', '9002',
    2, NULL
);

-- OT 3: Para pruebas de detalle adicionales
INSERT INTO ordenes_trabajo (
    consecutivo_ot, fecha_elaboracion_ot, fecha_entrega_ot,
    kilometraje_ingreso_ot, kilometreje_salida_ot,
    observacion_cli_ot, observacion_ot,
    placa_mot_ot, documento_usu_rp_ot, documento_usu_mc_ot,
    cod_ot_est_ot, fecha_fin_garantia_ot
) VALUES (
    3, SYSDATE - 2, SYSDATE - 1,
    6000, NULL,
    'OT para pruebas', 'OT prueba',
    'ABC123', '9001', '9002',
    2, NULL
);

COMMIT;

--------------------------------------------------------------------------------
-- 5. PRUEBAS DETALLE_ORDEN_TRABAJO
--    tg_val_cantidad_deto, tg_val_stock_disponible, tg_actualizar_stock
--------------------------------------------------------------------------------

PROMPT ---- PRUEBA: Detalle válido (debe descontar stock) ----

INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto, cod_pro_deto,
    fecha_confirmacion_deto, valor_unitario_deto,
    cantidad_deto, documento_usu_deto
) VALUES (
    1, 1,
    SYSDATE, 35000,
    2, '9001'
);
-- stock_pro pasa de 10 a 8

PROMPT ---- PRUEBA: Cantidad inválida (ORA-20003) ----

BEGIN
    INSERT INTO detalle_orden_trabajo (
        consecutivo_ot_deto, cod_pro_deto,
        fecha_confirmacion_deto, valor_unitario_deto,
        cantidad_deto, documento_usu_deto
    ) VALUES (
        2, 1,
        SYSDATE, 35000,
        0, '9001'
    );
END;
/

PROMPT ---- PRUEBA: Stock insuficiente (ORA-20004) ----

BEGIN
    INSERT INTO detalle_orden_trabajo (
        consecutivo_ot_deto, cod_pro_deto,
        fecha_confirmacion_deto, valor_unitario_deto,
        cantidad_deto, documento_usu_deto
    ) VALUES (
        3, 1,
        SYSDATE, 3500,
        99, '9001'
    );
END;
/

COMMIT;

--------------------------------------------------------------------------------
-- 6. PRUEBAS MOTOS (tg_val_placa_mot, tg_val_modelo_mot, tg_val_cilindraje_mot)
--------------------------------------------------------------------------------

PROMPT ---- PRUEBA: Placa inválida (ORA-20006) ----

BEGIN
    INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
    VALUES ('A1', 2020, 'Rojo', 150, '1001', 1);
END;
/

PROMPT ---- PRUEBA: Modelo inválido (ORA-20007) ----

BEGIN
    INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
    VALUES ('DEF456', 1800, 'Azul', 150, '1001', 1);
END;
/

PROMPT ---- PRUEBA: Cilindraje inválido (ORA-20008) ----

BEGIN
    INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
    VALUES ('GHI789', 2020, 'Blanco', -1, '1001', 1);
END;
/

COMMIT;

--------------------------------------------------------------------------------
-- 7. PRUEBAS ORDENES_TRABAJO (tg_val_fechas_ot, tg_val_kilometraje_ot, tg_val_usuarios_ot)
--------------------------------------------------------------------------------

PROMPT ---- PRUEBA: Fechas inválidas (ORA-20009) ----

BEGIN
    INSERT INTO ordenes_trabajo (
        consecutivo_ot, fecha_elaboracion_ot, fecha_entrega_ot,
        kilometraje_ingreso_ot, kilometreje_salida_ot,
        observacion_cli_ot, observacion_ot,
        placa_mot_ot, documento_usu_rp_ot, documento_usu_mc_ot,
        cod_ot_est_ot, fecha_fin_garantia_ot
    ) VALUES (
        4, SYSDATE, SYSDATE - 1,
        7000, NULL,
        'Fechas mal', 'Prueba fechas',
        'ABC123', '9001', '9002',
        2, NULL
    );
END;
/

PROMPT ---- PRUEBA: Kilometraje inválido (ORA-20010) ----

BEGIN
    UPDATE ordenes_trabajo
       SET kilometraje_ingreso_ot = -10
     WHERE consecutivo_ot = 1;
END;
/

PROMPT ---- PRUEBA: Usuarios iguales (ORA-20011) ----

BEGIN
    INSERT INTO ordenes_trabajo (
        consecutivo_ot, fecha_elaboracion_ot, fecha_entrega_ot,
        kilometraje_ingreso_ot, kilometreje_salida_ot,
        observacion_cli_ot, observacion_ot,
        placa_mot_ot, documento_usu_rp_ot, documento_usu_mc_ot,
        cod_ot_est_ot, fecha_fin_garantia_ot
    ) VALUES (
        5, SYSDATE - 1, SYSDATE,
        9000, NULL,
        'Usuarios iguales', 'Prueba usuarios',
        'ABC123', '9001', '9001',
        2, NULL
    );
END;
/

COMMIT;

--------------------------------------------------------------------------------
-- 8. PRUEBAS RECLAMOS (tg_val_ot_completada)
--------------------------------------------------------------------------------

PROMPT ---- PRUEBA: Reclamo válido (OT 1 Completada) ----

INSERT INTO reclamos (cod_rec, descripcion_rec, consecutivo_ot_rec)
VALUES (1, 'Problema posterior con el servicio', 1);

PROMPT ---- PRUEBA: Reclamo inválido (ORA-20016, OT 2 En proceso) ----

BEGIN
    INSERT INTO reclamos (cod_rec, descripcion_rec, consecutivo_ot_rec)
    VALUES (2, 'Reclamo sobre OT no completada', 2);
END;
/

COMMIT;

--------------------------------------------------------------------------------
-- FIN DEL SCRIPT
--------------------------------------------------------------------------------

PROMPT ============================================
PROMPT =  FIN DE PRUEBAS: REVISA LOS RESULTADOS   =
PROMPT ============================================

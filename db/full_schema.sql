-- ============================================================
-- MotoGestion - Esquema completo (generado para carga en pgAdmin)
-- Ejecutar sobre la base 'motogestion' YA creada.
-- Orden: sequences -> tables -> views -> triggers -> audit -> seed
-- ============================================================


-- ========================================================
-- >>> 01_sequences.sql
-- ========================================================

-- ============================================================
-- 01_sequences.sql
-- Secuencias (migradas de Oracle ScriptSequencias.sql)
-- En Postgres alimentan el DEFAULT de cada PK autogenerada.
-- ============================================================

CREATE SEQUENCE seq_impuestos            START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_marcas               START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_perfiles             START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_permisos             START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_productos            START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_productos_impuestos  START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_reclamos             START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_roles                START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;


-- ========================================================
-- >>> 02_tables.sql
-- ========================================================

-- ============================================================
-- 02_tables.sql
-- Tablas (migradas de Oracle Scriptsparacreartablas.sql)
-- Cambios respecto a Oracle:
--   * VARCHAR2(n BYTE) -> VARCHAR(n)
--   * NUMBER(p)        -> INTEGER ; NUMBER(p,s) -> NUMERIC(p,s)
--   * Se elimina TABLESPACE ts_ppi
--   * Se AGREGAN llaves primarias (PK) y foraneas (FK) -- en Oracle no existian
--   * Las PK autogeneradas usan DEFAULT nextval('seq_*') (ver 01_sequences.sql)
-- El orden de creacion respeta las dependencias de FK.
-- ============================================================

-- ----- Catalogos base -----

CREATE TABLE estados (
    cod_est    INTEGER       NOT NULL,
    nombre_est VARCHAR(50),
    CONSTRAINT pk_estados PRIMARY KEY (cod_est)
);

CREATE TABLE roles (
    cod_rol         INTEGER       NOT NULL DEFAULT nextval('seq_roles'),
    nombre_rol      VARCHAR(250),
    descripcion_rol VARCHAR(500),
    CONSTRAINT pk_roles PRIMARY KEY (cod_rol)
);

CREATE TABLE vistas (
    ruta_vis   VARCHAR(500) NOT NULL,
    nombre_vis VARCHAR(50),
    CONSTRAINT pk_vistas PRIMARY KEY (ruta_vis)
);

CREATE TABLE permisos (
    cod_prm         INTEGER       NOT NULL DEFAULT nextval('seq_permisos'),
    nombre_prm      VARCHAR(250),
    descripcion_prm VARCHAR(500),
    ruta_vis_prm    VARCHAR(500),
    CONSTRAINT pk_permisos PRIMARY KEY (cod_prm),
    CONSTRAINT fk_permisos_vista FOREIGN KEY (ruta_vis_prm) REFERENCES vistas (ruta_vis)
);

CREATE TABLE perfiles (
    cod_prf         INTEGER       NOT NULL DEFAULT nextval('seq_perfiles'),
    nombre_prf      VARCHAR(250),
    descripcion_prf VARCHAR(500),
    cod_est_prf     INTEGER,
    cod_rol_prf     INTEGER       NOT NULL,
    CONSTRAINT pk_perfiles PRIMARY KEY (cod_prf, cod_rol_prf),
    CONSTRAINT fk_perfiles_estado FOREIGN KEY (cod_est_prf) REFERENCES estados (cod_est),
    CONSTRAINT fk_perfiles_rol    FOREIGN KEY (cod_rol_prf) REFERENCES roles (cod_rol)
);

CREATE TABLE perfiles_permisos (
    cod_prm_pp     INTEGER NOT NULL,
    cod_prf_pp     INTEGER NOT NULL,
    cod_rol_prf_pp INTEGER NOT NULL,
    cod_est_pp     INTEGER,
    CONSTRAINT pk_perfiles_permisos PRIMARY KEY (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp),
    CONSTRAINT fk_pp_permiso FOREIGN KEY (cod_prm_pp) REFERENCES permisos (cod_prm),
    CONSTRAINT fk_pp_perfil  FOREIGN KEY (cod_prf_pp, cod_rol_prf_pp) REFERENCES perfiles (cod_prf, cod_rol_prf),
    CONSTRAINT fk_pp_estado  FOREIGN KEY (cod_est_pp) REFERENCES estados (cod_est)
);

CREATE TABLE usuarios (
    documento_usu   VARCHAR(11) NOT NULL,
    nombre_usu      VARCHAR(50),
    apellido_1_usu  VARCHAR(50),
    apellido_2_usu  VARCHAR(50),
    correo_usu      VARCHAR(50),
    contrasena_usu  VARCHAR(50),
    cod_tipo_usu    INTEGER,
    cod_est_usu     INTEGER,
    sub_id_usu      VARCHAR(250),
    cod_prf_usu     INTEGER,
    cod_rol_prf_usu INTEGER,
    CONSTRAINT pk_usuarios PRIMARY KEY (documento_usu),
    CONSTRAINT fk_usuarios_estado FOREIGN KEY (cod_est_usu) REFERENCES estados (cod_est),
    CONSTRAINT fk_usuarios_perfil FOREIGN KEY (cod_prf_usu, cod_rol_prf_usu) REFERENCES perfiles (cod_prf, cod_rol_prf)
);

-- ----- Dominio clientes / motos -----

CREATE TABLE clientes (
    documento_cli  VARCHAR(11) NOT NULL,
    nombre_cli     VARCHAR(50),
    apellido_1_cli VARCHAR(50),
    apellido_2_cli VARCHAR(50),
    telefono_cli   VARCHAR(15),
    correo_cli     VARCHAR(50),
    direccion_cli  VARCHAR(500),
    CONSTRAINT pk_clientes PRIMARY KEY (documento_cli)
);

CREATE TABLE marcas (
    cod_mar    INTEGER NOT NULL DEFAULT nextval('seq_marcas'),
    nombre_mar VARCHAR(50),
    CONSTRAINT pk_marcas PRIMARY KEY (cod_mar)
);

CREATE TABLE motos (
    placa_mot         VARCHAR(6) NOT NULL,
    modelo_mot        INTEGER,
    color_mot         VARCHAR(50),
    cilindraje_mot    INTEGER,
    documento_cli_mot VARCHAR(11),
    cod_marca_mot     INTEGER,
    CONSTRAINT pk_motos PRIMARY KEY (placa_mot),
    CONSTRAINT fk_motos_cliente FOREIGN KEY (documento_cli_mot) REFERENCES clientes (documento_cli),
    CONSTRAINT fk_motos_marca   FOREIGN KEY (cod_marca_mot)     REFERENCES marcas (cod_mar)
);

-- ----- Dominio productos / impuestos -----

CREATE TABLE impuestos (
    cod_imp        INTEGER NOT NULL DEFAULT nextval('seq_impuestos'),
    nombre_imp     VARCHAR(50),
    porcentaje_imp NUMERIC(5, 2),
    CONSTRAINT pk_impuestos PRIMARY KEY (cod_imp)
);

CREATE TABLE productos (
    cod_pro         INTEGER NOT NULL DEFAULT nextval('seq_productos'),
    nombre_pro      VARCHAR(70),
    descripcion_pro VARCHAR(500),
    stock_pro       INTEGER,
    stock_pro_min   INTEGER,
    cod_est_pro     INTEGER,
    precio_pro      INTEGER,
    CONSTRAINT pk_productos PRIMARY KEY (cod_pro),
    CONSTRAINT fk_productos_estado FOREIGN KEY (cod_est_pro) REFERENCES estados (cod_est)
);

CREATE TABLE productos_impuestos (
    cod_pro_imp        INTEGER NOT NULL DEFAULT nextval('seq_productos_impuestos'),
    cod_imp_pro_imp    INTEGER,
    cod_pro_pro_imp    INTEGER,
    porcentaje_pro_imp NUMERIC(5, 2),
    CONSTRAINT pk_productos_impuestos PRIMARY KEY (cod_pro_imp),
    CONSTRAINT fk_pi_impuesto FOREIGN KEY (cod_imp_pro_imp) REFERENCES impuestos (cod_imp),
    CONSTRAINT fk_pi_producto FOREIGN KEY (cod_pro_pro_imp) REFERENCES productos (cod_pro)
);

-- ----- Dominio ordenes de trabajo -----

CREATE TABLE ot_estados (
    cod_ot_est    INTEGER NOT NULL,
    nombre_ot_est VARCHAR(50),
    CONSTRAINT pk_ot_estados PRIMARY KEY (cod_ot_est)
);

CREATE TABLE ordenes_trabajo (
    consecutivo_ot         INTEGER NOT NULL,
    fecha_elaboracion_ot   DATE,
    fecha_entrega_ot       DATE,
    kilometraje_ingreso_ot INTEGER,
    kilometreje_salida_ot  DATE,      -- (typo heredado de Oracle: declarado DATE)
    observacion_cli_ot     VARCHAR(500),
    observacion_ot         VARCHAR(500),
    placa_mot_ot           VARCHAR(6),
    documento_usu_rp_ot    VARCHAR(11),
    documento_usu_mc_ot    VARCHAR(11),
    cod_ot_est_ot          INTEGER,
    fecha_fin_garantia_ot  DATE,
    CONSTRAINT pk_ordenes_trabajo PRIMARY KEY (consecutivo_ot),
    CONSTRAINT fk_ot_moto        FOREIGN KEY (placa_mot_ot)        REFERENCES motos (placa_mot),
    CONSTRAINT fk_ot_recep       FOREIGN KEY (documento_usu_rp_ot) REFERENCES usuarios (documento_usu),
    CONSTRAINT fk_ot_mecanico    FOREIGN KEY (documento_usu_mc_ot) REFERENCES usuarios (documento_usu),
    CONSTRAINT fk_ot_estado      FOREIGN KEY (cod_ot_est_ot)       REFERENCES ot_estados (cod_ot_est)
);

CREATE TABLE detalle_orden_trabajo (
    -- Oracle no definia PK; se agrega una surrogate IDENTITY porque la
    -- combinacion (orden, producto) puede repetirse (linea facturable + cortesia).
    id_deto                 BIGINT GENERATED ALWAYS AS IDENTITY,
    consecutivo_ot_deto     INTEGER NOT NULL,
    cod_pro_deto            INTEGER NOT NULL,
    fecha_confirmacion_deto DATE,
    valor_unitario_deto     INTEGER,
    cantidad_deto           INTEGER,
    documento_usu_deto      VARCHAR(11),
    CONSTRAINT pk_detalle_ot PRIMARY KEY (id_deto),
    CONSTRAINT fk_deto_orden    FOREIGN KEY (consecutivo_ot_deto) REFERENCES ordenes_trabajo (consecutivo_ot),
    CONSTRAINT fk_deto_producto FOREIGN KEY (cod_pro_deto)        REFERENCES productos (cod_pro),
    CONSTRAINT fk_deto_usuario  FOREIGN KEY (documento_usu_deto)  REFERENCES usuarios (documento_usu)
);

CREATE TABLE reclamos (
    cod_rec            INTEGER NOT NULL DEFAULT nextval('seq_reclamos'),
    descripcion_rec    VARCHAR(500),
    consecutivo_ot_rec INTEGER,
    CONSTRAINT pk_reclamos PRIMARY KEY (cod_rec),
    CONSTRAINT fk_reclamos_orden FOREIGN KEY (consecutivo_ot_rec) REFERENCES ordenes_trabajo (consecutivo_ot)
);


-- ========================================================
-- >>> 03_views.sql
-- ========================================================

-- ============================================================
-- 03_views.sql
-- Vistas (migradas de Oracle ScripVistas.sql)
-- Cambios Oracle -> Postgres:
--   * SYSDATE                 -> CURRENT_DATE
--   * TRUNC(SYSDATE - fecha)  -> (CURRENT_DATE - fecha)   [resta de date da entero de dias]
--   * Se omite la vista duplicada Oracle "US_PPI"."VW_PRODUCTOS_CON_IMPUESTOS"
--   * || (concatenacion), COALESCE, ROUND, ABS, CASE: validos en Postgres tal cual
-- ============================================================

-- ----- Ordenes de trabajo -----

CREATE OR REPLACE VIEW vw_ordenes_trabajo_completa AS
SELECT
    ot.consecutivo_ot,
    ot.fecha_elaboracion_ot,
    ot.fecha_entrega_ot,
    ot.kilometraje_ingreso_ot,
    ot.observacion_cli_ot,
    ot.observacion_ot,
    ot.fecha_fin_garantia_ot,
    m.placa_mot,
    m.modelo_mot,
    m.color_mot,
    m.cilindraje_mot,
    mar.nombre_mar AS marca_moto,
    c.documento_cli,
    c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo_cliente,
    c.telefono_cli,
    c.correo_cli,
    c.direccion_cli,
    urp.documento_usu AS documento_recepcionista,
    urp.nombre_usu || ' ' || urp.apellido_1_usu AS recepcionista,
    umc.documento_usu AS documento_mecanico,
    umc.nombre_usu || ' ' || umc.apellido_1_usu AS mecanico,
    ote.nombre_ot_est AS estado_ot,
    ot.cod_ot_est_ot
FROM ordenes_trabajo ot
INNER JOIN motos m       ON ot.placa_mot_ot = m.placa_mot
INNER JOIN clientes c    ON m.documento_cli_mot = c.documento_cli
INNER JOIN marcas mar    ON m.cod_marca_mot = mar.cod_mar
INNER JOIN usuarios urp  ON ot.documento_usu_rp_ot = urp.documento_usu
INNER JOIN usuarios umc  ON ot.documento_usu_mc_ot = umc.documento_usu
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est;

CREATE OR REPLACE VIEW vw_detalle_ot_productos AS
SELECT
    dot.consecutivo_ot_deto,
    dot.cod_pro_deto,
    p.nombre_pro,
    p.descripcion_pro,
    dot.cantidad_deto,
    dot.valor_unitario_deto,
    (ABS(dot.cantidad_deto) * dot.valor_unitario_deto) AS subtotal,
    dot.fecha_confirmacion_deto,
    u.nombre_usu || ' ' || u.apellido_1_usu AS usuario_confirmacion,
    e.nombre_est AS estado_producto
FROM detalle_orden_trabajo dot
INNER JOIN productos p ON dot.cod_pro_deto = p.cod_pro
INNER JOIN usuarios u  ON dot.documento_usu_deto = u.documento_usu
INNER JOIN estados e   ON p.cod_est_pro = e.cod_est;

CREATE OR REPLACE VIEW vw_resumen_financiero_ot AS
SELECT
    ot.consecutivo_ot,
    ot.fecha_elaboracion_ot,
    c.nombre_cli || ' ' || c.apellido_1_cli AS cliente,
    m.placa_mot,
    COUNT(CASE WHEN dot.cantidad_deto > 0 THEN dot.cod_pro_deto END) AS total_items,
    SUM(CASE WHEN dot.cantidad_deto > 0 THEN dot.cantidad_deto * dot.valor_unitario_deto ELSE 0 END) AS subtotal_productos,
    0 AS total_impuestos,
    SUM(CASE WHEN dot.cantidad_deto > 0 THEN dot.cantidad_deto * dot.valor_unitario_deto ELSE 0 END) AS total_ot
FROM ordenes_trabajo ot
INNER JOIN detalle_orden_trabajo dot ON ot.consecutivo_ot = dot.consecutivo_ot_deto
INNER JOIN motos m    ON ot.placa_mot_ot = m.placa_mot
INNER JOIN clientes c ON m.documento_cli_mot = c.documento_cli
GROUP BY ot.consecutivo_ot, ot.fecha_elaboracion_ot, c.nombre_cli, c.apellido_1_cli, m.placa_mot;

CREATE OR REPLACE VIEW vw_ot_pendientes AS
SELECT
    ot.consecutivo_ot,
    ot.fecha_elaboracion_ot,
    (CURRENT_DATE - ot.fecha_elaboracion_ot) AS dias_pendiente,
    c.nombre_cli || ' ' || c.apellido_1_cli AS cliente,
    c.telefono_cli,
    m.placa_mot,
    mar.nombre_mar || ' ' || m.modelo_mot AS moto,
    umc.nombre_usu || ' ' || umc.apellido_1_usu AS mecanico_asignado,
    ote.nombre_ot_est AS estado
FROM ordenes_trabajo ot
INNER JOIN motos m        ON ot.placa_mot_ot = m.placa_mot
INNER JOIN marcas mar     ON m.cod_marca_mot = mar.cod_mar
INNER JOIN clientes c     ON m.documento_cli_mot = c.documento_cli
INNER JOIN usuarios umc   ON ot.documento_usu_mc_ot = umc.documento_usu
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est
WHERE ot.fecha_entrega_ot IS NULL
ORDER BY ot.fecha_elaboracion_ot;

CREATE OR REPLACE VIEW vw_reclamos_completo AS
SELECT
    rec.cod_rec,
    rec.descripcion_rec,
    rec.consecutivo_ot_rec,
    ot.fecha_elaboracion_ot,
    ot.fecha_entrega_ot,
    ot.kilometraje_ingreso_ot,
    ot.observacion_cli_ot,
    ot.observacion_ot,
    ot.fecha_fin_garantia_ot,
    ote.nombre_ot_est AS estado_ot,
    m.placa_mot,
    m.modelo_mot,
    m.color_mot,
    m.cilindraje_mot,
    mar.nombre_mar AS marca_moto,
    mar.nombre_mar || ' ' || m.modelo_mot || ' (' || m.placa_mot || ')' AS moto_completa,
    c.documento_cli,
    c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo_cliente,
    c.telefono_cli,
    c.correo_cli,
    c.direccion_cli,
    urp.documento_usu AS documento_recepcionista,
    urp.nombre_usu || ' ' || urp.apellido_1_usu AS recepcionista,
    umc.documento_usu AS documento_mecanico,
    umc.nombre_usu || ' ' || umc.apellido_1_usu AS mecanico,
    CASE
        WHEN ot.fecha_fin_garantia_ot >= CURRENT_DATE THEN 'VIGENTE'
        WHEN ot.fecha_fin_garantia_ot <  CURRENT_DATE THEN 'VENCIDA'
        ELSE 'SIN INFORMACIÓN'
    END AS estado_garantia,
    CASE
        WHEN ot.fecha_fin_garantia_ot >= CURRENT_DATE
        THEN (ot.fecha_fin_garantia_ot - CURRENT_DATE)
        ELSE NULL
    END AS dias_garantia_restantes
FROM reclamos rec
INNER JOIN ordenes_trabajo ot ON rec.consecutivo_ot_rec = ot.consecutivo_ot
INNER JOIN motos m       ON ot.placa_mot_ot = m.placa_mot
INNER JOIN clientes c    ON m.documento_cli_mot = c.documento_cli
INNER JOIN marcas mar    ON m.cod_marca_mot = mar.cod_mar
INNER JOIN usuarios urp  ON ot.documento_usu_rp_ot = urp.documento_usu
INNER JOIN usuarios umc  ON ot.documento_usu_mc_ot = umc.documento_usu
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est;

CREATE OR REPLACE VIEW vw_reclamos_detalle AS
SELECT
    rec.cod_rec,
    rec.descripcion_rec,
    ot.consecutivo_ot,
    ot.fecha_elaboracion_ot,
    ot.fecha_entrega_ot,
    m.placa_mot,
    c.nombre_cli || ' ' || c.apellido_1_cli AS cliente,
    c.telefono_cli,
    ote.nombre_ot_est AS estado_ot
FROM reclamos rec
INNER JOIN ordenes_trabajo ot ON rec.consecutivo_ot_rec = ot.consecutivo_ot
INNER JOIN motos m       ON ot.placa_mot_ot = m.placa_mot
INNER JOIN clientes c    ON m.documento_cli_mot = c.documento_cli
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est;

-- ----- Productos / impuestos -----

CREATE OR REPLACE VIEW vw_productos AS
SELECT
    p.cod_pro, p.nombre_pro, p.descripcion_pro, p.precio_pro,
    p.stock_pro, p.stock_pro_min, p.cod_est_pro,
    e.nombre_est AS estado_producto
FROM productos p
INNER JOIN estados e ON p.cod_est_pro = e.cod_est;

CREATE OR REPLACE VIEW vw_productos_activos AS
SELECT
    p.cod_pro, p.nombre_pro, p.descripcion_pro, p.precio_pro,
    p.stock_pro, p.stock_pro_min, p.cod_est_pro,
    e.nombre_est AS estado_producto
FROM productos p
INNER JOIN estados e ON p.cod_est_pro = e.cod_est
WHERE p.cod_est_pro = 1;

CREATE OR REPLACE VIEW vw_productos_impuestos AS
SELECT
    pi.cod_pro_imp, pi.cod_imp_pro_imp, pi.cod_pro_pro_imp, pi.porcentaje_pro_imp,
    i.cod_imp, i.nombre_imp, i.porcentaje_imp
FROM productos_impuestos pi
INNER JOIN impuestos i ON pi.cod_imp_pro_imp = i.cod_imp;

CREATE OR REPLACE VIEW vw_productos_con_impuestos AS
SELECT
    p.cod_pro, p.nombre_pro, p.descripcion_pro, p.precio_pro,
    p.stock_pro, p.stock_pro_min,
    e.nombre_est AS estado_producto,
    pi.cod_pro_imp, i.nombre_imp, pi.porcentaje_pro_imp,
    ROUND(p.precio_pro * (pi.porcentaje_pro_imp / 100), 2) AS valor_impuesto,
    ROUND(p.precio_pro + (p.precio_pro * (pi.porcentaje_pro_imp / 100)), 2) AS precio_con_impuesto
FROM productos p
INNER JOIN estados e ON p.cod_est_pro = e.cod_est
LEFT JOIN productos_impuestos pi ON p.cod_pro = pi.cod_pro_pro_imp
LEFT JOIN impuestos i ON pi.cod_imp_pro_imp = i.cod_imp;

CREATE OR REPLACE VIEW vw_inventario_alertas AS
SELECT
    p.cod_pro, p.nombre_pro, p.descripcion_pro,
    p.stock_pro, p.stock_pro_min, p.precio_pro,
    e.nombre_est AS estado,
    CASE
        WHEN p.stock_pro = 0 THEN 'SIN STOCK'
        WHEN p.stock_pro <= p.stock_pro_min THEN 'STOCK BAJO'
        WHEN p.stock_pro > p.stock_pro_min AND p.stock_pro <= (p.stock_pro_min * 2) THEN 'STOCK MEDIO'
        ELSE 'STOCK NORMAL'
    END AS nivel_alerta,
    (p.stock_pro_min - p.stock_pro) AS cantidad_a_pedir
FROM productos p
INNER JOIN estados e ON p.cod_est_pro = e.cod_est;

-- ----- Clientes -----

CREATE OR REPLACE VIEW vw_clientes AS
SELECT
    c.documento_cli, c.nombre_cli, c.apellido_1_cli, c.apellido_2_cli,
    c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo,
    c.telefono_cli, c.correo_cli, c.direccion_cli
FROM clientes c;

CREATE OR REPLACE VIEW vw_clientes_resumen AS
SELECT
    c.documento_cli,
    c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo,
    c.telefono_cli, c.correo_cli, c.direccion_cli,
    COUNT(m.placa_mot) AS total_motos
FROM clientes c
LEFT JOIN motos m ON c.documento_cli = m.documento_cli_mot
GROUP BY c.documento_cli, c.nombre_cli, c.apellido_1_cli, c.apellido_2_cli,
         c.telefono_cli, c.correo_cli, c.direccion_cli;

CREATE OR REPLACE VIEW vw_clientes_motos AS
SELECT
    c.documento_cli,
    c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo,
    c.telefono_cli, c.correo_cli, c.direccion_cli,
    m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot,
    mar.nombre_mar AS marca
FROM clientes c
INNER JOIN motos m   ON c.documento_cli = m.documento_cli_mot
INNER JOIN marcas mar ON m.cod_marca_mot = mar.cod_mar;

-- ----- Motos -----

CREATE OR REPLACE VIEW vw_motos AS
SELECT m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot,
       m.documento_cli_mot, m.cod_marca_mot
FROM motos m;

CREATE OR REPLACE VIEW vw_motos_marcas AS
SELECT m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot,
       m.documento_cli_mot, m.cod_marca_mot,
       mar.nombre_mar AS marca
FROM motos m
INNER JOIN marcas mar ON m.cod_marca_mot = mar.cod_mar;

CREATE OR REPLACE VIEW vw_motos_detalle AS
SELECT
    m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot,
    mar.nombre_mar AS marca,
    c.documento_cli,
    c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo_cliente,
    c.telefono_cli, c.correo_cli
FROM motos m
INNER JOIN marcas mar ON m.cod_marca_mot = mar.cod_mar
INNER JOIN clientes c ON m.documento_cli_mot = c.documento_cli;

-- ----- Marcas -----

CREATE OR REPLACE VIEW vw_marcas AS
SELECT mar.cod_mar, mar.nombre_mar FROM marcas mar;

CREATE OR REPLACE VIEW vw_marcas_resumen AS
SELECT mar.cod_mar, mar.nombre_mar, COUNT(m.placa_mot) AS total_motos
FROM marcas mar
LEFT JOIN motos m ON mar.cod_mar = m.cod_marca_mot
GROUP BY mar.cod_mar, mar.nombre_mar;

CREATE OR REPLACE VIEW vw_marcas_motos AS
SELECT mar.cod_mar, mar.nombre_mar,
       m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot
FROM marcas mar
LEFT JOIN motos m ON mar.cod_mar = m.cod_marca_mot;

-- ----- Auth: usuarios / perfiles / permisos -----

CREATE OR REPLACE VIEW vw_usuarios_perfiles AS
SELECT
    u.documento_usu,
    u.nombre_usu || ' ' || u.apellido_1_usu || ' ' || COALESCE(u.apellido_2_usu, '') AS nombre_completo,
    u.correo_usu,
    u.cod_tipo_usu,
    e.nombre_est AS estado_usuario,
    p.nombre_prf AS perfil,
    p.descripcion_prf AS descripcion_perfil,
    r.nombre_rol AS rol,
    r.descripcion_rol AS descripcion_rol
FROM usuarios u
INNER JOIN estados e  ON u.cod_est_usu = e.cod_est
INNER JOIN perfiles p ON u.cod_prf_usu = p.cod_prf AND u.cod_rol_prf_usu = p.cod_rol_prf
INNER JOIN roles r    ON p.cod_rol_prf = r.cod_rol;

CREATE OR REPLACE VIEW vw_perfiles AS
SELECT
    p.cod_prf, p.nombre_prf, p.descripcion_prf,
    e.nombre_est AS nombre_est_prf,
    r.nombre_rol AS nombre_rol_prf
FROM perfiles p
INNER JOIN estados e ON p.cod_est_prf = e.cod_est
INNER JOIN roles r   ON p.cod_rol_prf = r.cod_rol
ORDER BY p.cod_prf;

CREATE OR REPLACE VIEW vw_perfiles_permisos_detalle AS
SELECT
    pf.cod_prf, pf.nombre_prf, r.nombre_rol,
    pm.cod_prm, pm.nombre_prm, pm.descripcion_prm,
    v.nombre_vis, v.ruta_vis,
    e.nombre_est AS estado_permiso
FROM perfiles_permisos pp
INNER JOIN perfiles pf ON pp.cod_prf_pp = pf.cod_prf AND pp.cod_rol_prf_pp = pf.cod_rol_prf
INNER JOIN roles r     ON pf.cod_rol_prf = r.cod_rol
INNER JOIN permisos pm ON pp.cod_prm_pp = pm.cod_prm
INNER JOIN vistas v    ON pm.ruta_vis_prm = v.ruta_vis
INNER JOIN estados e   ON pp.cod_est_pp = e.cod_est;

-- vw_permisos: no existia en los scripts Oracle y el repo la ordena por una
-- columna inexistente (cod_rol_prm). Se crea una version best-effort para que
-- el endpoint no falle: lista los permisos con una columna cod_rol_prm nula.
CREATE OR REPLACE VIEW vw_permisos AS
SELECT
    p.cod_prm, p.nombre_prm, p.descripcion_prm, p.ruta_vis_prm,
    NULL::INTEGER AS cod_rol_prm
FROM permisos p;


-- ========================================================
-- >>> 04_triggers.sql
-- ========================================================

-- ============================================================
-- 04_triggers.sql
-- Triggers FUNCIONALES migrados de Oracle Scriptstriggers.sql a PL/pgSQL.
-- Se portan SOLO los que afectan datos (decision de alcance):
--   * tg_actualizar_stock     -> descuenta stock al insertar un detalle
--   * tg_gen_consecutivo_ot   -> genera consecutivo_ot = MAX+1 si viene NULL
--   * tg_calc_fecha_garantia  -> calcula fecha_fin_garantia_ot (1 mes) si estado=4
-- Se OMITEN las validaciones de formato (email/placa/telefono/rangos) y
-- tg_alerta_stock_bajo (lanzaba error en UPDATE, bloqueante).
-- ============================================================

-- ----- Descontar stock al confirmar un detalle de OT -----
CREATE OR REPLACE FUNCTION fn_actualizar_stock()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE productos
       SET stock_pro = stock_pro - NEW.cantidad_deto
     WHERE cod_pro = NEW.cod_pro_deto;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_actualizar_stock
AFTER INSERT ON detalle_orden_trabajo
FOR EACH ROW
EXECUTE FUNCTION fn_actualizar_stock();

-- ----- Generar consecutivo de la orden de trabajo (MAX+1) -----
CREATE OR REPLACE FUNCTION fn_gen_consecutivo_ot()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.consecutivo_ot IS NULL THEN
        SELECT COALESCE(MAX(consecutivo_ot), 0) + 1
          INTO NEW.consecutivo_ot
          FROM ordenes_trabajo;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_gen_consecutivo_ot
BEFORE INSERT ON ordenes_trabajo
FOR EACH ROW
EXECUTE FUNCTION fn_gen_consecutivo_ot();

-- ----- Calcular fecha fin de garantia (1 mes desde entrega si estado = 4) -----
CREATE OR REPLACE FUNCTION fn_calc_fecha_garantia()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.cod_ot_est_ot = 4 THEN
        IF NEW.fecha_entrega_ot IS NOT NULL THEN
            NEW.fecha_fin_garantia_ot := (NEW.fecha_entrega_ot + INTERVAL '1 month')::date;
        END IF;
    ELSE
        NEW.fecha_fin_garantia_ot := NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_calc_fecha_garantia
BEFORE INSERT OR UPDATE ON ordenes_trabajo
FOR EACH ROW
EXECUTE FUNCTION fn_calc_fecha_garantia();


-- ========================================================
-- >>> 05_audit.sql
-- ========================================================

-- ============================================================
-- 05_audit.sql
-- Auditoria en Postgres. Reemplaza el paquete Oracle PKG_AUDITORIA +
-- UTL_FILE (que escribia a archivos .txt) por una TABLA audit_log poblada
-- por una funcion trigger generica.
-- ============================================================

CREATE TABLE audit_log (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fecha           TIMESTAMP    NOT NULL DEFAULT now(),
    usuario         VARCHAR(100) DEFAULT session_user,
    tabla           VARCHAR(100),
    evento          CHAR(1),          -- I = insert, U = update, D = delete
    valor_anterior  JSONB,
    valor_nuevo     JSONB
);

CREATE OR REPLACE FUNCTION fn_audit()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (tabla, evento, valor_nuevo)
        VALUES (TG_TABLE_NAME, 'I', to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (tabla, evento, valor_anterior, valor_nuevo)
        VALUES (TG_TABLE_NAME, 'U', to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (tabla, evento, valor_anterior)
        VALUES (TG_TABLE_NAME, 'D', to_jsonb(OLD));
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Triggers de auditoria sobre las tablas clave del negocio
CREATE TRIGGER tg_audit_clientes
AFTER INSERT OR UPDATE OR DELETE ON clientes
FOR EACH ROW EXECUTE FUNCTION fn_audit();

CREATE TRIGGER tg_audit_productos
AFTER INSERT OR UPDATE OR DELETE ON productos
FOR EACH ROW EXECUTE FUNCTION fn_audit();

CREATE TRIGGER tg_audit_ordenes_trabajo
AFTER INSERT OR UPDATE OR DELETE ON ordenes_trabajo
FOR EACH ROW EXECUTE FUNCTION fn_audit();

CREATE TRIGGER tg_audit_detalle_orden_trabajo
AFTER INSERT OR UPDATE OR DELETE ON detalle_orden_trabajo
FOR EACH ROW EXECUTE FUNCTION fn_audit();

CREATE TRIGGER tg_audit_usuarios
AFTER INSERT OR UPDATE OR DELETE ON usuarios
FOR EACH ROW EXECUTE FUNCTION fn_audit();


-- ========================================================
-- >>> 06_seed.sql
-- ========================================================

-- ============================================================
-- 06_seed.sql
-- Datos semilla (migrados de Oracle Scriptsregistros.sql).
-- Unica traduccion necesaria: seq_X.NEXTVAL -> nextval('seq_X').
-- TO_DATE(...) y COMMIT son validos en Postgres tal cual.
-- El orden respeta las FK (padres antes que hijos).
-- ============================================================

-- ======================
-- 1. ESTADOS
-- ======================
INSERT INTO estados (cod_est, nombre_est) VALUES (1, 'Activo');
INSERT INTO estados (cod_est, nombre_est) VALUES (2, 'Inactivo');

-- ============================================
-- TABLA: ROLES
-- ============================================
INSERT INTO roles (cod_rol, nombre_rol, descripcion_rol) VALUES
(nextval('seq_roles'), 'Administrador', 'Acceso total al sistema');

INSERT INTO roles (cod_rol, nombre_rol, descripcion_rol) VALUES
(nextval('seq_roles'), 'Mecánico', 'Acceso para mecánicos - gestión de órdenes de trabajo');

INSERT INTO roles (cod_rol, nombre_rol, descripcion_rol) VALUES
(nextval('seq_roles'), 'Recepcionista', 'Acceso para recepcionistas - gestión de clientes, motos y órdenes');

COMMIT;

-- ============================================
-- TABLA: VISTAS
-- ============================================
INSERT INTO vistas (ruta_vis, nombre_vis) VALUES
('/admin', 'Administración');

INSERT INTO vistas (ruta_vis, nombre_vis) VALUES
('/ordenes', 'Órdenes de Trabajo');

INSERT INTO vistas (ruta_vis, nombre_vis) VALUES
('/productos', 'Inventario de Productos');

INSERT INTO vistas (ruta_vis, nombre_vis) VALUES
('/marcas', 'Marcas');

INSERT INTO vistas (ruta_vis, nombre_vis) VALUES
('/clientes', 'Clientes');

INSERT INTO vistas (ruta_vis, nombre_vis) VALUES
('/motos', 'Motos');

INSERT INTO vistas (ruta_vis, nombre_vis) VALUES
('/reclamos', 'Reclamos');

COMMIT;

-- ============================================
-- TABLA: PERMISOS
-- ============================================
-- Permisos para CLIENTES
INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'leer:clientes', 'Permite ver clientes', '/clientes');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'crear:clientes', 'Permite crear clientes', '/clientes');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'actualizar:clientes', 'Permite actualizar clientes', '/clientes');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'eliminar:clientes', 'Permite eliminar - desactivar clientes', '/clientes');

-- Permisos para MARCAS
INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'leer:marcas', 'Permite ver marcas', '/marcas');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'crear:marcas', 'Permite crear marcas', '/marcas');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'actualizar:marcas', 'Permite actualizar marcas', '/marcas');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'eliminar:marcas', 'Permite eliminar - desactivar marcas', '/marcas');

-- Permisos para MOTOS
INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'leer:motos', 'Permite ver motos', '/motos');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'crear:motos', 'Permite crear motos', '/motos');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'actualizar:motos', 'Permite actualizar motos', '/motos');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'eliminar:motos', 'Permite eliminar - desactivar motos', '/motos');

-- Permisos para OPERATIONS
INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'leer:operations', 'Permite ver operaciones', '/admin');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'crear:operations', 'Permite crear operaciones', '/admin');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'actualizar:operations', 'Permite actualizar operaciones', '/admin');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'eliminar:operations', 'Permite eliminar - desactivar operaciones', '/admin');

-- Permisos para ÓRDENES DE TRABAJO
INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'leer:ordenes-trabajo', 'Permite ver órdenes de trabajo', '/ordenes');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'crear:ordenes-trabajo', 'Permite crear órdenes de trabajo', '/ordenes');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'actualizar:ordenes-trabajo', 'Permite actualizar órdenes de trabajo', '/ordenes');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'eliminar:ordenes-trabajo', 'Permite eliminar - desactivar órdenes de trabajo', '/ordenes');

-- Permisos para ORDERS
INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'leer:orders', 'Permite ver pedidos', '/productos');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'crear:orders', 'Permite crear pedidos', '/productos');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'actualizar:orders', 'Permite actualizar pedidos', '/productos');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'eliminar:orders', 'Permite eliminar - desactivar pedidos', '/productos');

-- Permisos para PERFILES Y PERMISOS
INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'leer:perfiles-permisos', 'Permite ver perfiles de permisos', '/admin');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'crear:perfiles-permisos', 'Permite crear perfiles de permisos', '/admin');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'actualizar:perfiles-permisos', 'Permite actualizar perfiles de permisos', '/admin');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'eliminar:perfiles-permisos', 'Permite eliminar - desactivar perfiles de permisos', '/admin');

-- Permisos para PRODUCTOS
INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'leer:productos', 'Permite ver productos', '/productos');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'crear:productos', 'Permite crear productos', '/productos');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'actualizar:productos', 'Permite actualizar productos', '/productos');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'eliminar:productos', 'Permite eliminar - desactivar productos', '/productos');

-- Permisos para ROLES
INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'leer:roles', 'Permite ver roles', '/admin');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'crear:roles', 'Permite crear roles', '/admin');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'actualizar:roles', 'Permite actualizar roles', '/admin');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'eliminar:roles', 'Permite eliminar - desactivar roles', '/admin');

-- Permisos para USERS
INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'leer:users', 'Permite ver usuarios', '/admin');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'crear:users', 'Permite crear usuarios', '/admin');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'actualizar:users', 'Permite actualizar usuarios', '/admin');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'eliminar:users', 'Permite eliminar - desactivar usuarios', '/admin');

-- Permisos para VISTAS
INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'leer:vistas', 'Permite ver vistas', '/admin');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'crear:vistas', 'Permite crear vistas', '/admin');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'actualizar:vistas', 'Permite actualizar vistas', '/admin');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'eliminar:vistas', 'Permite eliminar - desactivar vistas', '/admin');

-- Permisos para RECLAMOS
INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'leer:reclamos', 'Permite ver reclamos', '/reclamos');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'crear:reclamos', 'Permite crear reclamos', '/reclamos');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'actualizar:reclamos', 'Permite actualizar reclamos', '/reclamos');

INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'), 'eliminar:reclamos', 'Permite eliminar - desactivar reclamos', '/reclamos');

COMMIT;

-- ============================================
-- TABLA: PERFILES
-- (Nota: cod_est_prf = 1 asume que existe en tabla estados)
-- ============================================
INSERT INTO perfiles (cod_prf, nombre_prf, descripcion_prf, cod_est_prf, cod_rol_prf) VALUES
(nextval('seq_perfiles'), 'Administrador Total', 'Perfil con acceso completo', 1, 1);

INSERT INTO perfiles (cod_prf, nombre_prf, descripcion_prf, cod_est_prf, cod_rol_prf) VALUES
(nextval('seq_perfiles'), 'Mecánico', 'Perfil para mecánicos del taller', 1, 2);

INSERT INTO perfiles (cod_prf, nombre_prf, descripcion_prf, cod_est_prf, cod_rol_prf) VALUES
(nextval('seq_perfiles'), 'Recepcionista', 'Perfil para recepcionistas del taller', 1, 3);

COMMIT;

-- ============================================
-- TABLA: PERFILES_PERMISOS
-- ============================================
-- Nota: Los códigos de permisos (cod_prm) van del 1 al 48 en el orden insertado
-- Perfil 1 = Administrador (Rol 1) - TODOS LOS PERMISOS
-- Perfil 2 = Mecánico (Rol 2) - Permisos limitados
-- Perfil 3 = Recepcionista (Rol 3) - Permisos de gestión básica

-- ADMINISTRADOR (Perfil 1, Rol 1) - Acceso Total (todos los permisos del 1 al 48)
-- Permisos de Clientes (1-4)
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (1, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (2, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (3, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (4, 1, 1, 1);

-- Permisos de Marcas (5-8)
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (5, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (6, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (7, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (8, 1, 1, 1);

-- Permisos de Motos (9-12)
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (9, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (10, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (11, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (12, 1, 1, 1);

-- Permisos de Operations (13-16)
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (13, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (14, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (15, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (16, 1, 1, 1);

-- Permisos de Órdenes de Trabajo (17-20)
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (17, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (18, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (19, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (20, 1, 1, 1);

-- Permisos de Orders (21-24)
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (21, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (22, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (23, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (24, 1, 1, 1);

-- Permisos de Perfiles-Permisos (25-28)
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (25, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (26, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (27, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (28, 1, 1, 1);

-- Permisos de Productos (29-32)
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (29, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (30, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (31, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (32, 1, 1, 1);

-- Permisos de Roles (33-36)
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (33, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (34, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (35, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (36, 1, 1, 1);

-- Permisos de Users (37-40)
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (37, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (38, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (39, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (40, 1, 1, 1);

-- Permisos de Vistas (41-44)
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (41, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (42, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (43, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (44, 1, 1, 1);

-- Permisos de Reclamos (45-48)
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (45, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (46, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (47, 1, 1, 1);
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (48, 1, 1, 1);

-- MECÁNICO (Perfil 2, Rol 2) - Permisos para gestión de órdenes de trabajo
-- Leer clientes, marcas, motos (para consultar información)
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (1, 2, 2, 1);  -- leer:clientes
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (5, 2, 2, 1);  -- leer:marcas
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (9, 2, 2, 1);  -- leer:motos

-- Permisos completos de órdenes de trabajo
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (17, 2, 2, 1); -- leer:ordenes-trabajo
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (18, 2, 2, 1); -- crear:ordenes-trabajo
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (19, 2, 2, 1); -- actualizar:ordenes-trabajo

-- Leer productos (para consultar inventario)
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (29, 2, 2, 1); -- leer:productos

-- Permisos completos de reclamos (para gestionar reclamos de órdenes de trabajo)
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (45, 2, 2, 1); -- leer:reclamos
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (46, 2, 2, 1); -- crear:reclamos
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (47, 2, 2, 1); -- actualizar:reclamos

-- RECEPCIONISTA (Perfil 3, Rol 3) - Permisos de gestión de clientes, motos y órdenes
-- Permisos completos de clientes
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (1, 3, 3, 1);  -- leer:clientes
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (2, 3, 3, 1);  -- crear:clientes
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (3, 3, 3, 1);  -- actualizar:clientes

-- Leer marcas
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (5, 3, 3, 1);  -- leer:marcas

-- Permisos completos de motos
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (9, 3, 3, 1);  -- leer:motos
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (10, 3, 3, 1); -- crear:motos
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (11, 3, 3, 1); -- actualizar:motos

-- Permisos completos de órdenes de trabajo
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (17, 3, 3, 1); -- leer:ordenes-trabajo
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (18, 3, 3, 1); -- crear:ordenes-trabajo
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (19, 3, 3, 1); -- actualizar:ordenes-trabajo

-- Leer productos
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (29, 3, 3, 1); -- leer:productos

-- Permisos completos de reclamos
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (45, 3, 3, 1); -- leer:reclamos
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (46, 3, 3, 1); -- crear:reclamos
INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) VALUES (47, 3, 3, 1); -- actualizar:reclamos

COMMIT;

-- ========================================
-- INSERTS PARA IMPUESTOS
-- ========================================
INSERT INTO impuestos (cod_imp, nombre_imp, porcentaje_imp) VALUES (nextval('seq_impuestos'), 'IVA', 19.00);
INSERT INTO impuestos (cod_imp, nombre_imp, porcentaje_imp) VALUES (nextval('seq_impuestos'), 'IVA Reducido', 5.00);
INSERT INTO impuestos (cod_imp, nombre_imp, porcentaje_imp) VALUES (nextval('seq_impuestos'), 'Impuesto al Consumo', 8.00);
INSERT INTO impuestos (cod_imp, nombre_imp, porcentaje_imp) VALUES (nextval('seq_impuestos'), 'ICA', 1.00);
INSERT INTO impuestos (cod_imp, nombre_imp, porcentaje_imp) VALUES (nextval('seq_impuestos'), 'Excluido', 0.00);
COMMIT;

-- ========================================
-- INSERTS PARA PRODUCTOS
-- ========================================
-- Productos típicos de un taller de motos

-- Producto 1: Aceite Motor 4T 20W50 - con IVA (19%)
INSERT INTO productos (cod_pro, nombre_pro, descripcion_pro, stock_pro, stock_pro_min, cod_est_pro, precio_pro)
VALUES (nextval('seq_productos'), 'Aceite Motor 4T 20W50', 'Aceite lubricante sintético para motores de 4 tiempos, presentación 1 litro', 50, 10, 1, 35000);

-- Producto 2: Filtro de Aceite - con IVA (19%)
INSERT INTO productos (cod_pro, nombre_pro, descripcion_pro, stock_pro, stock_pro_min, cod_est_pro, precio_pro)
VALUES (nextval('seq_productos'), 'Filtro de Aceite Universal', 'Filtro de aceite compatible con motos 125cc a 200cc', 80, 15, 1, 18000);

-- Producto 3: Pastillas de Freno - con IVA (19%)
INSERT INTO productos (cod_pro, nombre_pro, descripcion_pro, stock_pro, stock_pro_min, cod_est_pro, precio_pro)
VALUES (nextval('seq_productos'), 'Pastillas de Freno Delanteras', 'Juego de pastillas de freno para disco delantero, alta durabilidad', 60, 12, 1, 45000);

-- Producto 4: Llanta Delantera 100/90-18 - con IVA (19%)
INSERT INTO productos (cod_pro, nombre_pro, descripcion_pro, stock_pro, stock_pro_min, cod_est_pro, precio_pro)
VALUES (nextval('seq_productos'), 'Llanta Delantera 100/90-18', 'Llanta tubeless para moto, medida estándar 100/90-18', 25, 5, 1, 180000);

-- Producto 5: Llanta Trasera 110/90-16 - con IVA (19%)
INSERT INTO productos (cod_pro, nombre_pro, descripcion_pro, stock_pro, stock_pro_min, cod_est_pro, precio_pro)
VALUES (nextval('seq_productos'), 'Llanta Trasera 110/90-16', 'Llanta tubeless para moto, medida estándar 110/90-16', 20, 5, 1, 195000);

-- Producto 6: Kit Arrastre (Piñón, Corona, Cadena) - con IVA (19%)
INSERT INTO productos (cod_pro, nombre_pro, descripcion_pro, stock_pro, stock_pro_min, cod_est_pro, precio_pro)
VALUES (nextval('seq_productos'), 'Kit de Arrastre Completo', 'Kit completo: piñón 14T, corona 42T y cadena 428H-120L', 30, 8, 1, 220000);

-- Producto 7: Bujía NGK - con IVA Reducido (5%)
INSERT INTO productos (cod_pro, nombre_pro, descripcion_pro, stock_pro, stock_pro_min, cod_est_pro, precio_pro)
VALUES (nextval('seq_productos'), 'Bujía NGK CPR8E', 'Bujía de encendido resistiva, compatible con motos 125cc-200cc', 100, 20, 1, 12000);

-- Producto 8: Batería 12V 7Ah - con IVA (19%)
INSERT INTO productos (cod_pro, nombre_pro, descripcion_pro, stock_pro, stock_pro_min, cod_est_pro, precio_pro)
VALUES (nextval('seq_productos'), 'Batería 12V 7Ah Libre Mantenimiento', 'Batería sellada gel 12V 7Ah para motos con encendido eléctrico', 35, 8, 1, 95000);

-- Producto 9: Mano de Obra Mecánica - con IVA Reducido (5%)
INSERT INTO productos (cod_pro, nombre_pro, descripcion_pro, stock_pro, stock_pro_min, cod_est_pro, precio_pro)
VALUES (nextval('seq_productos'), 'Mano de Obra - Mantenimiento General', 'Servicio de mantenimiento general: cambio aceite, ajustes, revisión completa', 999, 1, 1, 80000);

-- Producto 10: Guaya de Freno Delantera - con IVA (19%)
INSERT INTO productos (cod_pro, nombre_pro, descripcion_pro, stock_pro, stock_pro_min, cod_est_pro, precio_pro)
VALUES (nextval('seq_productos'), 'Guaya de Freno Delantera', 'Cable de freno delantero reforzado en acero inoxidable, longitud universal', 70, 15, 1, 22000);

COMMIT;

-- ========================================
-- INSERTS PARA PRODUCTOS_IMPUESTOS
-- ========================================
-- Asociar los productos con sus impuestos correspondientes
-- NOTA: Los cod_pro se generan automáticamente usando secuencias

-- Producto 1: Aceite Motor - IVA 19%
INSERT INTO productos_impuestos (cod_pro_imp, cod_imp_pro_imp, cod_pro_pro_imp, porcentaje_pro_imp)
VALUES (nextval('seq_productos_impuestos'), 1, 1, 19.00);

-- Producto 2: Filtro de Aceite - IVA 19%
INSERT INTO productos_impuestos (cod_pro_imp, cod_imp_pro_imp, cod_pro_pro_imp, porcentaje_pro_imp)
VALUES (nextval('seq_productos_impuestos'), 1, 2, 19.00);

-- Producto 3: Pastillas de Freno - IVA 19%
INSERT INTO productos_impuestos (cod_pro_imp, cod_imp_pro_imp, cod_pro_pro_imp, porcentaje_pro_imp)
VALUES (nextval('seq_productos_impuestos'), 1, 3, 19.00);

-- Producto 4: Llanta Delantera - IVA 19%
INSERT INTO productos_impuestos (cod_pro_imp, cod_imp_pro_imp, cod_pro_pro_imp, porcentaje_pro_imp)
VALUES (nextval('seq_productos_impuestos'), 1, 4, 19.00);

-- Producto 5: Llanta Trasera - IVA 19%
INSERT INTO productos_impuestos (cod_pro_imp, cod_imp_pro_imp, cod_pro_pro_imp, porcentaje_pro_imp)
VALUES (nextval('seq_productos_impuestos'), 1, 5, 19.00);

-- Producto 6: Kit Arrastre - IVA 19%
INSERT INTO productos_impuestos (cod_pro_imp, cod_imp_pro_imp, cod_pro_pro_imp, porcentaje_pro_imp)
VALUES (nextval('seq_productos_impuestos'), 1, 6, 19.00);

-- Producto 7: Bujía - IVA Reducido 5%
INSERT INTO productos_impuestos (cod_pro_imp, cod_imp_pro_imp, cod_pro_pro_imp, porcentaje_pro_imp)
VALUES (nextval('seq_productos_impuestos'), 2, 7, 5.00);

-- Producto 8: Batería - IVA 19%
INSERT INTO productos_impuestos (cod_pro_imp, cod_imp_pro_imp, cod_pro_pro_imp, porcentaje_pro_imp)
VALUES (nextval('seq_productos_impuestos'), 1, 8, 19.00);

-- Producto 9: Mano de Obra - IVA Reducido 5%
INSERT INTO productos_impuestos (cod_pro_imp, cod_imp_pro_imp, cod_pro_pro_imp, porcentaje_pro_imp)
VALUES (nextval('seq_productos_impuestos'), 2, 9, 5.00);

-- Producto 10: Guaya de Freno - IVA 19%
INSERT INTO productos_impuestos (cod_pro_imp, cod_imp_pro_imp, cod_pro_pro_imp, porcentaje_pro_imp)
VALUES (nextval('seq_productos_impuestos'), 1, 10, 19.00);

COMMIT;

-- ========================================
-- INSERTS PARA CLIENTES
-- ========================================

-- Cliente 1
INSERT INTO clientes (documento_cli, nombre_cli, apellido_1_cli, apellido_2_cli, telefono_cli, correo_cli, direccion_cli)
VALUES ('1234567890', 'Juan', 'Pérez', 'García', '3001234567', 'juan.perez@email.com', 'Calle 45 #23-15, Medellín');

-- Cliente 2
INSERT INTO clientes (documento_cli, nombre_cli, apellido_1_cli, apellido_2_cli, telefono_cli, correo_cli, direccion_cli)
VALUES ('9876543210', 'María', 'González', 'López', '3109876543', 'maria.gonzalez@email.com', 'Carrera 70 #50-30, Medellín');

-- Cliente 3
INSERT INTO clientes (documento_cli, nombre_cli, apellido_1_cli, apellido_2_cli, telefono_cli, correo_cli, direccion_cli)
VALUES ('1122334455', 'Carlos', 'Ramírez', 'Martínez', '3201122334', 'carlos.ramirez@email.com', 'Avenida 80 #32-45, Bello');

-- Cliente 4
INSERT INTO clientes (documento_cli, nombre_cli, apellido_1_cli, apellido_2_cli, telefono_cli, correo_cli, direccion_cli)
VALUES ('5544332211', 'Ana', 'Torres', 'Sánchez', '3155544332', 'ana.torres@email.com', 'Calle 10 #15-20, Envigado');

-- Cliente 5
INSERT INTO clientes (documento_cli, nombre_cli, apellido_1_cli, apellido_2_cli, telefono_cli, correo_cli, direccion_cli)
VALUES ('6677889900', 'Luis', 'Hernández', NULL, '3006677889', 'luis.hernandez@email.com', 'Carrera 43A #5-90, Medellín');

-- Cliente 6
INSERT INTO clientes (documento_cli, nombre_cli, apellido_1_cli, apellido_2_cli, telefono_cli, correo_cli, direccion_cli)
VALUES ('2233445566', 'Andrea', 'Moreno', 'Castro', '3142233445', 'andrea.moreno@email.com', 'Calle 33 #55-12, Itagüí');

-- Cliente 7
INSERT INTO clientes (documento_cli, nombre_cli, apellido_1_cli, apellido_2_cli, telefono_cli, correo_cli, direccion_cli)
VALUES ('7788990011', 'Pedro', 'Jiménez', 'Vargas', '3187788990', 'pedro.jimenez@email.com', 'Carrera 52 #28-40, Medellín');

-- Cliente 8
INSERT INTO clientes (documento_cli, nombre_cli, apellido_1_cli, apellido_2_cli, telefono_cli, correo_cli, direccion_cli)
VALUES ('3344556677', 'Laura', 'Díaz', 'Rojas', '3003344556', 'laura.diaz@email.com', 'Calle 67 #48-25, Sabaneta');

-- Cliente 9
INSERT INTO clientes (documento_cli, nombre_cli, apellido_1_cli, apellido_2_cli, telefono_cli, correo_cli, direccion_cli)
VALUES ('8899001122', 'Diego', 'Muñoz', NULL, '3108899001', 'diego.munoz@email.com', 'Avenida El Poblado #10-50, Medellín');

-- Cliente 10
INSERT INTO clientes (documento_cli, nombre_cli, apellido_1_cli, apellido_2_cli, telefono_cli, correo_cli, direccion_cli)
VALUES ('4455667788', 'Carolina', 'Ruiz', 'Fernández', '3204455667', 'carolina.ruiz@email.com', 'Calle 30 #44-18, La Estrella');

-- ========================================
-- INSERTS PARA MARCAS (necesarios antes de insertar motos)
-- ========================================

INSERT INTO marcas (cod_mar, nombre_mar) VALUES (nextval('seq_marcas'), 'Yamaha');
INSERT INTO marcas (cod_mar, nombre_mar) VALUES (nextval('seq_marcas'), 'Honda');
INSERT INTO marcas (cod_mar, nombre_mar) VALUES (nextval('seq_marcas'), 'Suzuki');
INSERT INTO marcas (cod_mar, nombre_mar) VALUES (nextval('seq_marcas'), 'Kawasaki');
INSERT INTO marcas (cod_mar, nombre_mar) VALUES (nextval('seq_marcas'), 'Bajaj');
INSERT INTO marcas (cod_mar, nombre_mar) VALUES (nextval('seq_marcas'), 'AKT');
INSERT INTO marcas (cod_mar, nombre_mar) VALUES (nextval('seq_marcas'), 'BMW');
INSERT INTO marcas (cod_mar, nombre_mar) VALUES (nextval('seq_marcas'), 'Ducati');
INSERT INTO marcas (cod_mar, nombre_mar) VALUES (nextval('seq_marcas'), 'KTM');
INSERT INTO marcas (cod_mar, nombre_mar) VALUES (nextval('seq_marcas'), 'Auteco');

-- ========================================
-- INSERTS PARA MOTOS
-- ========================================

-- Motos para Cliente 1 (Juan Pérez)
INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
VALUES ('ABC123', 2020, 'Negro', 150, '1234567890', 1); -- Yamaha

INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
VALUES ('DEF456', 2018, 'Rojo', 125, '1234567890', 2); -- Honda

-- Motos para Cliente 2 (María González)
INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
VALUES ('GHI789', 2021, 'Azul', 200, '9876543210', 3); -- Suzuki

-- Motos para Cliente 3 (Carlos Ramírez)
INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
VALUES ('JKL012', 2019, 'Blanco', 180, '1122334455', 4); -- Kawasaki

INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
VALUES ('MNO345', 2022, 'Verde', 250, '1122334455', 4); -- Kawasaki

-- Motos para Cliente 4 (Ana Torres)
INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
VALUES ('PQR678', 2020, 'Gris', 110, '5544332211', 5); -- Bajaj

-- Motos para Cliente 5 (Luis Hernández)
INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
VALUES ('STU901', 2021, 'Negro', 125, '6677889900', 6); -- AKT

-- Motos para Cliente 6 (Andrea Moreno)
INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
VALUES ('VWX234', 2023, 'Rojo', 300, '2233445566', 7); -- BMW

-- Motos para Cliente 7 (Pedro Jiménez)
INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
VALUES ('YZA567', 2022, 'Amarillo', 160, '7788990011', 1); -- Yamaha

INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
VALUES ('BCD890', 2019, 'Naranja', 200, '7788990011', 9); -- KTM

-- Motos para Cliente 8 (Laura Díaz)
INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
VALUES ('EFG123', 2020, 'Morado', 150, '3344556677', 10); -- Auteco

-- Motos para Cliente 9 (Diego Muñoz)
INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
VALUES ('HIJ456', 2021, 'Negro', 650, '8899001122', 8); -- Ducati

-- Motos para Cliente 10 (Carolina Ruiz)
INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
VALUES ('KLM789', 2023, 'Blanco', 125, '4455667788', 2); -- Honda

INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
VALUES ('NOP012', 2022, 'Azul', 150, '4455667788', 1); -- Yamaha

-- Motos adicionales para variedad
INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
VALUES ('QRS345', 2018, 'Plateado', 180, '9876543210', 3); -- Suzuki (segundo para María)

INSERT INTO motos (placa_mot, modelo_mot, color_mot, cilindraje_mot, documento_cli_mot, cod_marca_mot)
VALUES ('TUV678', 2020, 'Negro Mate', 200, '1234567890', 4); -- Kawasaki (tercero para Juan)

-- Confirmar los cambios
COMMIT;


-- ========================================
-- ESTADOS DE ÓRDENES DE TRABAJO
-- ========================================

INSERT INTO ot_estados (cod_ot_est, nombre_ot_est) VALUES (1, 'Pendiente');
INSERT INTO ot_estados (cod_ot_est, nombre_ot_est) VALUES (2, 'En Proceso');
INSERT INTO ot_estados (cod_ot_est, nombre_ot_est) VALUES (3, 'Completada');
INSERT INTO ot_estados (cod_ot_est, nombre_ot_est) VALUES (4, 'Entregada');
INSERT INTO ot_estados (cod_ot_est, nombre_ot_est) VALUES (5, 'Cancelada');
INSERT INTO ot_estados (cod_ot_est, nombre_ot_est) VALUES (6, 'Garantía');

COMMIT;

-- ========================================
-- INSERTS PARA USUARIOS
-- ========================================
-- NOTA: Las contraseñas están en texto plano por simplicidad.
-- En producción deberían estar hasheadas.

-- ============================================
-- USUARIO ADMINISTRADOR
-- ============================================
INSERT INTO usuarios (documento_usu, nombre_usu, apellido_1_usu, apellido_2_usu, correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, cod_prf_usu, cod_rol_prf_usu)
VALUES ('1000000001', 'Admin', 'Sistema', NULL, 'admin@motogestion.com', 'admin123', 1, 1, 'sub-1000000001', 1, 1);

-- ============================================
-- RECEPCIONISTAS (4 usuarios)
-- ============================================

-- Recepcionista 1
INSERT INTO usuarios (documento_usu, nombre_usu, apellido_1_usu, apellido_2_usu, correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, cod_prf_usu, cod_rol_prf_usu)
VALUES ('1000000002', 'Sofia', 'Martínez', 'Restrepo', 'sofia.martinez@motogestion.com', 'recep123', 2, 1, 'sub-1000000002', 3, 3);

-- Recepcionista 2
INSERT INTO usuarios (documento_usu, nombre_usu, apellido_1_usu, apellido_2_usu, correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, cod_prf_usu, cod_rol_prf_usu)
VALUES ('1000000003', 'Valentina', 'López', 'García', 'valentina.lopez@motogestion.com', 'recep123', 2, 1, 'sub-1000000003', 3, 3);

-- Recepcionista 3
INSERT INTO usuarios (documento_usu, nombre_usu, apellido_1_usu, apellido_2_usu, correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, cod_prf_usu, cod_rol_prf_usu)
VALUES ('1000000004', 'Camila', 'Rodríguez', 'Pérez', 'camila.rodriguez@motogestion.com', 'recep123', 2, 1, 'sub-1000000004', 3, 3);

-- Recepcionista 4
INSERT INTO usuarios (documento_usu, nombre_usu, apellido_1_usu, apellido_2_usu, correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, cod_prf_usu, cod_rol_prf_usu)
VALUES ('1000000005', 'Isabella', 'Gómez', 'Moreno', 'isabella.gomez@motogestion.com', 'recep123', 2, 1, 'sub-1000000005', 3, 3);

-- ============================================
-- MECÁNICOS (4 usuarios)
-- ============================================

-- Mecánico 1
INSERT INTO usuarios (documento_usu, nombre_usu, apellido_1_usu, apellido_2_usu, correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, cod_prf_usu, cod_rol_prf_usu)
VALUES ('1000000006', 'Miguel', 'Hernández', 'Torres', 'miguel.hernandez@motogestion.com', 'meca123', 2, 1, 'sub-1000000006', 2, 2);

-- Mecánico 2
INSERT INTO usuarios (documento_usu, nombre_usu, apellido_1_usu, apellido_2_usu, correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, cod_prf_usu, cod_rol_prf_usu)
VALUES ('1000000007', 'Andrés', 'Ramírez', 'Castro', 'andres.ramirez@motogestion.com', 'meca123', 2, 1, 'sub-1000000007', 2, 2);

-- Mecánico 3
INSERT INTO usuarios (documento_usu, nombre_usu, apellido_1_usu, apellido_2_usu, correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, cod_prf_usu, cod_rol_prf_usu)
VALUES ('1000000008', 'Santiago', 'Vargas', 'Muñoz', 'santiago.vargas@motogestion.com', 'meca123', 2, 1, 'sub-1000000008', 2, 2);

-- Mecánico 4
INSERT INTO usuarios (documento_usu, nombre_usu, apellido_1_usu, apellido_2_usu, correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, cod_prf_usu, cod_rol_prf_usu)
VALUES ('1000000009', 'Sebastián', 'Jiménez', 'Ruiz', 'sebastian.jimenez@motogestion.com', 'meca123', 2, 1, 'sub-1000000009', 2, 2);

COMMIT;

-- ========================================
-- INSERTS PARA ÓRDENES DE TRABAJO
-- ========================================
-- 5 órdenes de trabajo con diferentes escenarios:
-- 1. Orden Pendiente con productos facturables y no facturables
-- 2. Orden En Proceso con solo productos facturables
-- 3. Orden Completada lista para entregar
-- 4. Orden Entregada con garantía
-- 5. Orden Pendiente con múltiples productos mixtos

-- ========================================
-- ORDEN 1: Mantenimiento General - PENDIENTE
-- Cliente: Juan Pérez (1234567890) - Moto ABC123 (Yamaha)
-- Recepcionista: Sofia Martínez - Mecánico: Miguel Hernández
-- ========================================
INSERT INTO ordenes_trabajo (
    consecutivo_ot,
    fecha_elaboracion_ot,
    placa_mot_ot,
    kilometraje_ingreso_ot,
    documento_usu_rp_ot,
    documento_usu_mc_ot,
    observacion_cli_ot,
    observacion_ot,
    cod_ot_est_ot
) VALUES (
    1,
    TO_DATE('2025-11-20', 'YYYY-MM-DD'),
    'ABC123',
    15000,
    '1000000002', -- Sofia (Recepcionista)
    '1000000006', -- Miguel (Mecánico)
    'La moto hace ruido extraño al frenar',
    'Revisar sistema de frenos completo',
    1 -- Pendiente
);

-- Detalles Orden 1 (Productos facturables y no facturables)
-- Producto facturable: Aceite Motor
INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto,
    cod_pro_deto,
    cantidad_deto,
    valor_unitario_deto,
    documento_usu_deto,
    fecha_confirmacion_deto
) VALUES (
    1, -- consecutivo de la orden
    1, -- Aceite Motor 4T 20W50
    2, -- Cantidad POSITIVA = SE FACTURA
    35000,
    '1000000006', -- Miguel confirmó
    TO_DATE('2025-11-20', 'YYYY-MM-DD')
);

-- Producto no facturable: Filtro de aceite (cortesía)
INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto,
    cod_pro_deto,
    cantidad_deto,
    valor_unitario_deto,
    documento_usu_deto,
    fecha_confirmacion_deto
) VALUES (
    1,
    2, -- Filtro de Aceite
    -1, -- Cantidad NEGATIVA = NO SE FACTURA
    18000,
    '1000000006',
    TO_DATE('2025-11-20', 'YYYY-MM-DD')
);

-- Producto facturable: Pastillas de freno
INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto,
    cod_pro_deto,
    cantidad_deto,
    valor_unitario_deto,
    documento_usu_deto,
    fecha_confirmacion_deto
) VALUES (
    1,
    3, -- Pastillas de Freno
    1, -- SE FACTURA
    45000,
    '1000000006',
    TO_DATE('2025-11-20', 'YYYY-MM-DD')
);

-- Producto facturable: Mano de obra
INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto,
    cod_pro_deto,
    cantidad_deto,
    valor_unitario_deto,
    documento_usu_deto,
    fecha_confirmacion_deto
) VALUES (
    1,
    9, -- Mano de Obra
    1, -- SE FACTURA
    80000,
    '1000000006',
    TO_DATE('2025-11-20', 'YYYY-MM-DD')
);

-- ========================================
-- ORDEN 2: Cambio de Llantas - EN PROCESO
-- Cliente: María González (9876543210) - Moto GHI789 (Suzuki)
-- Recepcionista: Valentina López - Mecánico: Andrés Ramírez
-- ========================================
INSERT INTO ordenes_trabajo (
    consecutivo_ot,
    fecha_elaboracion_ot,
    fecha_entrega_ot,
    placa_mot_ot,
    kilometraje_ingreso_ot,
    documento_usu_rp_ot,
    documento_usu_mc_ot,
    observacion_cli_ot,
    observacion_ot,
    cod_ot_est_ot
) VALUES (
    2,
    TO_DATE('2025-11-21', 'YYYY-MM-DD'),
    TO_DATE('2025-11-23', 'YYYY-MM-DD'), -- Fecha entrega estimada
    'GHI789',
    28000,
    '1000000003', -- Valentina
    '1000000007', -- Andrés
    'Llantas desgastadas, necesitan cambio urgente',
    'Instalar llantas nuevas y balancear',
    2 -- En Proceso
);

-- Detalles Orden 2 (Solo productos facturables)
INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto,
    cod_pro_deto,
    cantidad_deto,
    valor_unitario_deto,
    documento_usu_deto,
    fecha_confirmacion_deto
) VALUES (
    2,
    4, -- Llanta Delantera
    1, -- SE FACTURA
    180000,
    '1000000007',
    TO_DATE('2025-11-21', 'YYYY-MM-DD')
);

INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto,
    cod_pro_deto,
    cantidad_deto,
    valor_unitario_deto,
    documento_usu_deto,
    fecha_confirmacion_deto
) VALUES (
    2,
    5, -- Llanta Trasera
    1, -- SE FACTURA
    195000,
    '1000000007',
    TO_DATE('2025-11-21', 'YYYY-MM-DD')
);

INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto,
    cod_pro_deto,
    cantidad_deto,
    valor_unitario_deto,
    documento_usu_deto,
    fecha_confirmacion_deto
) VALUES (
    2,
    9, -- Mano de Obra
    1, -- SE FACTURA
    80000,
    '1000000007',
    TO_DATE('2025-11-21', 'YYYY-MM-DD')
);

-- ========================================
-- ORDEN 3: Cambio de Kit de Arrastre - COMPLETADA
-- Cliente: Carlos Ramírez (1122334455) - Moto JKL012 (Kawasaki)
-- Recepcionista: Camila Rodríguez - Mecánico: Santiago Vargas
-- ========================================
INSERT INTO ordenes_trabajo (
    consecutivo_ot,
    fecha_elaboracion_ot,
    fecha_entrega_ot,
    placa_mot_ot,
    kilometraje_ingreso_ot,
    documento_usu_rp_ot,
    documento_usu_mc_ot,
    observacion_cli_ot,
    observacion_ot,
    cod_ot_est_ot
) VALUES (
    3,
    TO_DATE('2025-11-19', 'YYYY-MM-DD'),
    TO_DATE('2025-11-22', 'YYYY-MM-DD'),
    'JKL012',
    42000,
    '1000000004', -- Camila
    '1000000008', -- Santiago
    'Cadena muy desgastada, saltan los dientes',
    'Trabajo completado. Listo para entrega',
    3 -- Completada
);

-- Detalles Orden 3
INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto,
    cod_pro_deto,
    cantidad_deto,
    valor_unitario_deto,
    documento_usu_deto,
    fecha_confirmacion_deto
) VALUES (
    3,
    6, -- Kit de Arrastre
    1, -- SE FACTURA
    220000,
    '1000000008',
    TO_DATE('2025-11-19', 'YYYY-MM-DD')
);

INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto,
    cod_pro_deto,
    cantidad_deto,
    valor_unitario_deto,
    documento_usu_deto,
    fecha_confirmacion_deto
) VALUES (
    3,
    1, -- Aceite Motor
    1, -- SE FACTURA
    35000,
    '1000000008',
    TO_DATE('2025-11-19', 'YYYY-MM-DD')
);

INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto,
    cod_pro_deto,
    cantidad_deto,
    valor_unitario_deto,
    documento_usu_deto,
    fecha_confirmacion_deto
) VALUES (
    3,
    9, -- Mano de Obra
    2, -- SE FACTURA (2 horas)
    80000,
    '1000000008',
    TO_DATE('2025-11-19', 'YYYY-MM-DD')
);

-- ========================================
-- ORDEN 4: Cambio de Batería - ENTREGADA
-- Cliente: Ana Torres (5544332211) - Moto PQR678 (Bajaj)
-- Recepcionista: Isabella Gómez - Mecánico: Sebastián Jiménez
-- ========================================
INSERT INTO ordenes_trabajo (
    consecutivo_ot,
    fecha_elaboracion_ot,
    fecha_entrega_ot,
    placa_mot_ot,
    kilometraje_ingreso_ot,
    documento_usu_rp_ot,
    documento_usu_mc_ot,
    observacion_cli_ot,
    observacion_ot,
    fecha_fin_garantia_ot,
    cod_ot_est_ot
) VALUES (
    4,
    TO_DATE('2025-11-15', 'YYYY-MM-DD'),
    TO_DATE('2025-11-16', 'YYYY-MM-DD'),
    'PQR678',
    8500,
    '1000000005', -- Isabella
    '1000000009', -- Sebastián
    'La moto no enciende, batería descargada',
    'Batería reemplazada. Garantía de 30 días',
    TO_DATE('2025-12-16', 'YYYY-MM-DD'), -- 30 días de garantía
    4 -- Entregada
);

-- Detalles Orden 4
INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto,
    cod_pro_deto,
    cantidad_deto,
    valor_unitario_deto,
    documento_usu_deto,
    fecha_confirmacion_deto
) VALUES (
    4,
    8, -- Batería
    1, -- SE FACTURA
    95000,
    '1000000009',
    TO_DATE('2025-11-15', 'YYYY-MM-DD')
);

INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto,
    cod_pro_deto,
    cantidad_deto,
    valor_unitario_deto,
    documento_usu_deto,
    fecha_confirmacion_deto
) VALUES (
    4,
    7, -- Bujía (cortesía)
    -1, -- NO SE FACTURA
    12000,
    '1000000009',
    TO_DATE('2025-11-15', 'YYYY-MM-DD')
);

INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto,
    cod_pro_deto,
    cantidad_deto,
    valor_unitario_deto,
    documento_usu_deto,
    fecha_confirmacion_deto
) VALUES (
    4,
    9, -- Mano de Obra
    1, -- SE FACTURA
    80000,
    '1000000009',
    TO_DATE('2025-11-15', 'YYYY-MM-DD')
);

-- ========================================
-- ORDEN 5: Mantenimiento Completo - PENDIENTE
-- Cliente: Andrea Moreno (2233445566) - Moto VWX234 (BMW)
-- Recepcionista: Sofia Martínez - Mecánico: Miguel Hernández
-- ========================================
INSERT INTO ordenes_trabajo (
    consecutivo_ot,
    fecha_elaboracion_ot,
    fecha_entrega_ot,
    placa_mot_ot,
    kilometraje_ingreso_ot,
    documento_usu_rp_ot,
    documento_usu_mc_ot,
    observacion_cli_ot,
    observacion_ot,
    cod_ot_est_ot
) VALUES (
    5,
    TO_DATE('2025-11-23', 'YYYY-MM-DD'),
    TO_DATE('2025-11-25', 'YYYY-MM-DD'),
    'VWX234',
    35000,
    '1000000002', -- Sofia
    '1000000006', -- Miguel
    'Mantenimiento de los 35,000 km. Revisar todo el sistema',
    'Pendiente de aprobación del cliente para cambios adicionales',
    1 -- Pendiente
);

-- Detalles Orden 5 (Mix de facturables y no facturables)
INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto,
    cod_pro_deto,
    cantidad_deto,
    valor_unitario_deto,
    documento_usu_deto,
    fecha_confirmacion_deto
) VALUES (
    5,
    1, -- Aceite Motor
    3, -- SE FACTURA (3 litros)
    35000,
    '1000000006',
    TO_DATE('2025-11-23', 'YYYY-MM-DD')
);

INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto,
    cod_pro_deto,
    cantidad_deto,
    valor_unitario_deto,
    documento_usu_deto,
    fecha_confirmacion_deto
) VALUES (
    5,
    2, -- Filtro de Aceite
    1, -- SE FACTURA
    18000,
    '1000000006',
    TO_DATE('2025-11-23', 'YYYY-MM-DD')
);

INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto,
    cod_pro_deto,
    cantidad_deto,
    valor_unitario_deto,
    documento_usu_deto,
    fecha_confirmacion_deto
) VALUES (
    5,
    7, -- Bujía (cortesía)
    -2, -- NO SE FACTURA (2 bujías de cortesía)
    12000,
    '1000000006',
    TO_DATE('2025-11-23', 'YYYY-MM-DD')
);

INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto,
    cod_pro_deto,
    cantidad_deto,
    valor_unitario_deto,
    documento_usu_deto,
    fecha_confirmacion_deto
) VALUES (
    5,
    10, -- Guaya de Freno
    1, -- SE FACTURA
    22000,
    '1000000006',
    TO_DATE('2025-11-23', 'YYYY-MM-DD')
);

INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto,
    cod_pro_deto,
    cantidad_deto,
    valor_unitario_deto,
    documento_usu_deto,
    fecha_confirmacion_deto
) VALUES (
    5,
    3, -- Pastillas de Freno
    1, -- SE FACTURA
    45000,
    '1000000006',
    TO_DATE('2025-11-23', 'YYYY-MM-DD')
);

INSERT INTO detalle_orden_trabajo (
    consecutivo_ot_deto,
    cod_pro_deto,
    cantidad_deto,
    valor_unitario_deto,
    documento_usu_deto,
    fecha_confirmacion_deto
) VALUES (
    5,
    9, -- Mano de Obra
    3, -- SE FACTURA (3 horas)
    80000,
    '1000000006',
    TO_DATE('2025-11-23', 'YYYY-MM-DD')
);

COMMIT;

-- ========================================
-- RESUMEN DE ÓRDENES CREADAS
-- ========================================
-- Orden 1: Juan Pérez - ABC123 (Yamaha) - PENDIENTE
--   Total Facturable: 160,000 (Aceite x2: 70,000 + Pastillas: 45,000 + Mano Obra: 80,000 + Filtro cortesía)
--
-- Orden 2: María González - GHI789 (Suzuki) - EN PROCESO
--   Total Facturable: 455,000 (Llanta D: 180,000 + Llanta T: 195,000 + Mano Obra: 80,000)
--
-- Orden 3: Carlos Ramírez - JKL012 (Kawasaki) - COMPLETADA
--   Total Facturable: 395,000 (Kit Arrastre: 220,000 + Aceite: 35,000 + Mano Obra x2: 160,000)
--
-- Orden 4: Ana Torres - PQR678 (Bajaj) - ENTREGADA
--   Total Facturable: 175,000 (Batería: 95,000 + Mano Obra: 80,000 + Bujía cortesía)
--
-- Orden 5: Andrea Moreno - VWX234 (BMW) - PENDIENTE
--   Total Facturable: 410,000 (Aceite x3: 105,000 + Filtro: 18,000 + Guaya: 22,000 + Pastillas: 45,000 + Mano Obra x3: 240,000 + Bujías cortesía)


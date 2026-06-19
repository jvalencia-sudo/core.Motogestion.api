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

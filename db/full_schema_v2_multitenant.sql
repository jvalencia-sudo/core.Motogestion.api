-- ============================================================
-- MotoGestion - Esquema MULTI-TENANT (v2) - REFACTOR
-- Copia de full_schema.sql adaptada a multi-taller (SaaS).
-- Estrategia: esquema compartido + columna cod_taller + RLS de Postgres.
--   * Tablas POR TALLER: cod_taller con DEFAULT current_setting('app.tenant_id').
--     PK compuestas con cod_taller en las llaves naturales (documento/placa/consecutivo).
--     RLS + FORCE ROW LEVEL SECURITY para aislar cada taller.
--   * Tablas GLOBALES (catálogos y permisos): se comparten entre todos los talleres.
--   * El backend hará SET app.tenant_id=<id> por request; el DEFAULT y el RLS hacen el resto.
-- El original single-tenant (full_schema.sql) se borró: sin security_invoker en sus
-- vistas y sin referencias en el repo, era solo confusión al lado de este esquema.
-- ============================================================

-- ============================================================
-- 0. TENANT: talleres
-- ============================================================
CREATE SEQUENCE seq_talleres START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;

CREATE TABLE talleres (
    cod_taller            INTEGER       NOT NULL DEFAULT nextval('seq_talleres'),
    nombre_tal            VARCHAR(150)  NOT NULL,
    nit_tal               VARCHAR(20),
    correo_tal            VARCHAR(100),
    telefono_tal          VARCHAR(20),
    estado_tal            VARCHAR(20)   NOT NULL DEFAULT 'prueba', -- prueba | activo | suspendido
    plan_tal              VARCHAR(50),                              -- para Wompi/suscripciones (luego)
    fecha_creacion_tal    TIMESTAMP     NOT NULL DEFAULT now(),
    fecha_fin_susc_tal    DATE,
    modo_mano_obra        VARCHAR(10)   NOT NULL DEFAULT 'HORAS',    -- HORAS | LIBRE
    tarifa_hora_pred      INTEGER       NOT NULL DEFAULT 0,          -- tarifa/hora por defecto (modo HORAS)
    precio_susc_tal       INTEGER,                                   -- precio pactado (congelado) con este taller
    direccion_tal         VARCHAR(200),
    texto_pie_comprobante VARCHAR(300),
    -- F1-09: personalización visual de la orden (carta + tirilla).
    nombre_comercial_tal          VARCHAR(150),
    whatsapp_tal                  VARCHAR(20),
    color_principal_tal           VARCHAR(7)  NOT NULL DEFAULT '#00B06E',
    texto_condiciones_tal         VARCHAR(1500),
    texto_pie_tal                 VARCHAR(200),
    mostrar_precios_unitarios_tal BOOLEAN     NOT NULL DEFAULT true,
    mostrar_mecanico_tal          BOOLEAN     NOT NULL DEFAULT true,
    mostrar_firma_cliente_tal     BOOLEAN     NOT NULL DEFAULT false,
    CONSTRAINT pk_talleres PRIMARY KEY (cod_taller),
    CONSTRAINT chk_taller_modo_mo CHECK (modo_mano_obra IN ('HORAS', 'LIBRE')),
    CONSTRAINT chk_taller_color_principal CHECK (color_principal_tal ~ '^#[0-9A-Fa-f]{6}$')
);

-- Anti-abuso del trial: un correo = un taller.
CREATE UNIQUE INDEX ux_talleres_correo ON talleres (lower(correo_tal));

-- F1-09: logo del taller, en tabla aparte -- ver 011_personalizacion_pdf.sql
-- (evita que el SELECT * genérico de BaseRepository arrastre el BYTEA en
-- cada fila/llamada que no lo necesita).
CREATE TABLE taller_logo (
    cod_taller     INTEGER      NOT NULL,
    logo           BYTEA        NOT NULL,
    content_type   VARCHAR(20)  NOT NULL,
    actualizado_en TIMESTAMP    NOT NULL DEFAULT now(),
    CONSTRAINT pk_taller_logo PRIMARY KEY (cod_taller),
    CONSTRAINT fk_taller_logo_taller FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller)
);

-- Catálogo GLOBAL de planes (sin RLS). talleres.plan_tal referencia nombre_plan.
CREATE SEQUENCE seq_planes START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE TABLE planes (
    cod_plan     INTEGER      NOT NULL DEFAULT nextval('seq_planes'),
    nombre_plan  VARCHAR(50)  NOT NULL,
    precio_plan  INTEGER      NOT NULL DEFAULT 0,
    max_usuarios INTEGER,
    max_motos    INTEGER,
    features     JSONB        NOT NULL DEFAULT '{}',
    orden        INTEGER      NOT NULL DEFAULT 0,
    activo       BOOLEAN      NOT NULL DEFAULT true,   -- false = fuera de catálogo (no se borra: pagos lo referencian)
    CONSTRAINT pk_planes PRIMARY KEY (cod_plan),
    CONSTRAINT ux_planes_nombre UNIQUE (nombre_plan)
);
INSERT INTO planes (nombre_plan, precio_plan, max_usuarios, max_motos, features, orden, activo) VALUES
    ('Prueba',   0,     NULL, NULL, '{"reportes": true}', 1, true),
    ('Taller',   69000, NULL, NULL, '{"reportes": true}', 2, true),
    ('Premium',  99000, NULL, NULL, '{"reportes": true, "multi_sucursal": true}', 3, false);

-- Pagos / suscripciones (billing de plataforma, SIN RLS: el webhook llega sin sesión).
CREATE SEQUENCE seq_pagos START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE TABLE pagos (
    cod_pago             INTEGER      NOT NULL DEFAULT nextval('seq_pagos'),
    cod_taller           INTEGER      NOT NULL,
    nombre_plan          VARCHAR(50)  NOT NULL,
    monto                INTEGER      NOT NULL,
    referencia           VARCHAR(80)  NOT NULL,
    estado               VARCHAR(20)  NOT NULL DEFAULT 'PENDING',
    wompi_transaction_id VARCHAR(80),
    fecha                TIMESTAMP    NOT NULL DEFAULT now(),
    medio                VARCHAR(10)  NOT NULL DEFAULT 'WOMPI',  -- WOMPI | MANUAL (F0-14)
    detalle_medio        VARCHAR(50),                           -- "Efectivo"/"Transferencia"/"Nequi" si medio=MANUAL
    CONSTRAINT pk_pagos PRIMARY KEY (cod_pago),
    CONSTRAINT ux_pagos_referencia UNIQUE (referencia),
    CONSTRAINT fk_pagos_taller FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT chk_pagos_estado CHECK (estado IN ('PENDING', 'APPROVED', 'DECLINED')),
    CONSTRAINT chk_pagos_medio CHECK (medio IN ('WOMPI', 'MANUAL'))
);

-- ============================================================
-- 1. SECUENCIAS (surrogates; siguen siendo únicas globalmente)
-- ============================================================
CREATE SEQUENCE seq_impuestos            START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_marcas               START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_perfiles             START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_permisos             START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_productos            START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_productos_impuestos  START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_reclamos             START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_movimientos_inventario START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_paquete_componentes  START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;
CREATE SEQUENCE seq_pagos_orden          START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;

-- ============================================================
-- 2. TABLAS GLOBALES (compartidas por todos los talleres)
-- ============================================================
CREATE TABLE estados (
    cod_est    INTEGER NOT NULL,
    nombre_est VARCHAR(50),
    CONSTRAINT pk_estados PRIMARY KEY (cod_est)
);

CREATE TABLE ot_estados (
    cod_ot_est    INTEGER NOT NULL,
    nombre_ot_est VARCHAR(50),
    CONSTRAINT pk_ot_estados PRIMARY KEY (cod_ot_est)
);

CREATE TABLE permisos (
    cod_prm         INTEGER NOT NULL DEFAULT nextval('seq_permisos'),
    nombre_prm      VARCHAR(250),
    descripcion_prm VARCHAR(500),
    CONSTRAINT pk_permisos PRIMARY KEY (cod_prm)
);

-- ============================================================
-- 2b. PERFILES Y SUS PERMISOS — POR TALLER (cod_taller + RLS)
--    Cada taller personaliza sus propios perfiles sin afectar a otros.
--    permisos sigue siendo el catálogo GLOBAL compartido. F1-12: perfil y
--    rol se fusionaron -- un perfil es admin o no (es_admin), sin tabla
--    global de roles ni "vistas" (ninguna de las dos aportaba enforcement
--    real, eran metadata decorativa para la UI).
-- ============================================================
CREATE TABLE perfiles (
    cod_taller      INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    cod_prf         INTEGER NOT NULL DEFAULT nextval('seq_perfiles'),
    nombre_prf      VARCHAR(250),
    descripcion_prf VARCHAR(500),
    cod_est_prf     INTEGER,
    es_admin        BOOLEAN NOT NULL DEFAULT false,
    CONSTRAINT pk_perfiles PRIMARY KEY (cod_taller, cod_prf),
    CONSTRAINT fk_perfiles_taller FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_perfiles_estado FOREIGN KEY (cod_est_prf) REFERENCES estados (cod_est)
);
-- cod_prf es único globalmente (seq) pero el PK incluye cod_taller para el aislamiento.

CREATE TABLE perfiles_permisos (
    cod_taller     INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    cod_prm_pp     INTEGER NOT NULL,
    cod_prf_pp     INTEGER NOT NULL,
    cod_est_pp     INTEGER,
    CONSTRAINT pk_perfiles_permisos PRIMARY KEY (cod_taller, cod_prm_pp, cod_prf_pp),
    CONSTRAINT fk_pp_taller  FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_pp_permiso FOREIGN KEY (cod_prm_pp) REFERENCES permisos (cod_prm),
    CONSTRAINT fk_pp_perfil  FOREIGN KEY (cod_taller, cod_prf_pp) REFERENCES perfiles (cod_taller, cod_prf),
    CONSTRAINT fk_pp_estado  FOREIGN KEY (cod_est_pp) REFERENCES estados (cod_est)
);

-- ============================================================
-- 3. TABLAS POR TALLER (cod_taller + RLS)
--    cod_taller toma su valor del DEFAULT (app.tenant_id) si no se indica.
-- ============================================================

CREATE TABLE usuarios (
    cod_taller      INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
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
    es_super_admin  BOOLEAN NOT NULL DEFAULT false,  -- F0-14: super-admin de plataforma, independiente de taller/rol
    ultimo_ingreso_usu TIMESTAMP,                    -- F0-14: se actualiza en cada login, para el panel de super-admin
    es_admin_usu    BOOLEAN NOT NULL DEFAULT false,  -- F1-12: denormalizado desde el perfil (fusión perfil+rol);
                                                      -- al final de la tabla porque la migración 007 lo agrega con
                                                      -- ALTER TABLE ADD COLUMN sobre una BD ya existente (Postgres
                                                      -- siempre añade al final, nunca reordena columnas físicas) --
                                                      -- aquí también al final para que el diff de la 007 contra
                                                      -- este archivo coincida columna por columna.
    CONSTRAINT pk_usuarios PRIMARY KEY (cod_taller, documento_usu),
    CONSTRAINT fk_usuarios_taller FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_usuarios_estado FOREIGN KEY (cod_est_usu) REFERENCES estados (cod_est),
    CONSTRAINT fk_usuarios_perfil FOREIGN KEY (cod_taller, cod_prf_usu) REFERENCES perfiles (cod_taller, cod_prf)
);
-- sub_id_usu identifica al usuario en Auth0; debe ser único globalmente para el login.
CREATE UNIQUE INDEX ux_usuarios_sub_id ON usuarios (sub_id_usu) WHERE sub_id_usu IS NOT NULL;

CREATE TABLE clientes (
    cod_taller     INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    documento_cli  VARCHAR(11) NOT NULL,
    nombre_cli     VARCHAR(50),
    apellido_1_cli VARCHAR(50),
    apellido_2_cli VARCHAR(50),
    telefono_cli   VARCHAR(15),
    correo_cli     VARCHAR(50),
    direccion_cli  VARCHAR(500),
    CONSTRAINT pk_clientes PRIMARY KEY (cod_taller, documento_cli),
    CONSTRAINT fk_clientes_taller FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller)
);

CREATE TABLE marcas (
    cod_taller INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    cod_mar    INTEGER NOT NULL DEFAULT nextval('seq_marcas'),
    nombre_mar VARCHAR(50),
    CONSTRAINT pk_marcas PRIMARY KEY (cod_taller, cod_mar),
    CONSTRAINT fk_marcas_taller FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller)
);

CREATE TABLE motos (
    cod_taller        INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    placa_mot         VARCHAR(6) NOT NULL,
    modelo_mot        INTEGER,
    color_mot         VARCHAR(50),
    cilindraje_mot    INTEGER,
    documento_cli_mot VARCHAR(11),
    cod_marca_mot     INTEGER,
    CONSTRAINT pk_motos PRIMARY KEY (cod_taller, placa_mot),
    CONSTRAINT fk_motos_taller  FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_motos_cliente FOREIGN KEY (cod_taller, documento_cli_mot) REFERENCES clientes (cod_taller, documento_cli),
    CONSTRAINT fk_motos_marca   FOREIGN KEY (cod_taller, cod_marca_mot)     REFERENCES marcas (cod_taller, cod_mar)
);

CREATE TABLE impuestos (
    cod_taller     INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    cod_imp        INTEGER NOT NULL DEFAULT nextval('seq_impuestos'),
    nombre_imp     VARCHAR(50),
    porcentaje_imp NUMERIC(5, 2),
    CONSTRAINT pk_impuestos PRIMARY KEY (cod_taller, cod_imp),
    CONSTRAINT fk_impuestos_taller FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller)
);

CREATE TABLE productos (
    cod_taller      INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    cod_pro         INTEGER NOT NULL DEFAULT nextval('seq_productos'),
    nombre_pro      VARCHAR(70),
    descripcion_pro VARCHAR(500),
    stock_pro       NUMERIC(12, 3),                                 -- NULL para SERVICIO/PAQUETE
    stock_pro_min   NUMERIC(12, 3),
    cod_est_pro     INTEGER,
    precio_pro      INTEGER,
    tipo_pro        VARCHAR(10) NOT NULL DEFAULT 'BIEN',            -- BIEN | SERVICIO | PAQUETE
    unidad_pro      VARCHAR(10) NOT NULL DEFAULT 'unidad',          -- unidad | litro | galon | metro
    dias_garantia_pro INTEGER   NOT NULL DEFAULT 0,                 -- F1-04: 0 = sin garantía
    CONSTRAINT pk_productos PRIMARY KEY (cod_taller, cod_pro),
    CONSTRAINT fk_productos_taller FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_productos_estado FOREIGN KEY (cod_est_pro) REFERENCES estados (cod_est),
    CONSTRAINT chk_producto_tipo CHECK (tipo_pro IN ('BIEN', 'SERVICIO', 'PAQUETE')),
    CONSTRAINT chk_producto_unidad CHECK (unidad_pro IN ('unidad', 'litro', 'galon', 'metro'))
);

CREATE TABLE productos_impuestos (
    cod_taller         INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    cod_pro_imp        INTEGER NOT NULL DEFAULT nextval('seq_productos_impuestos'),
    cod_imp_pro_imp    INTEGER,
    cod_pro_pro_imp    INTEGER,
    porcentaje_pro_imp NUMERIC(5, 2),
    CONSTRAINT pk_productos_impuestos PRIMARY KEY (cod_taller, cod_pro_imp),
    CONSTRAINT fk_pi_taller   FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_pi_impuesto FOREIGN KEY (cod_taller, cod_imp_pro_imp) REFERENCES impuestos (cod_taller, cod_imp),
    CONSTRAINT fk_pi_producto FOREIGN KEY (cod_taller, cod_pro_pro_imp) REFERENCES productos (cod_taller, cod_pro)
);

CREATE TABLE ordenes_trabajo (
    cod_taller             INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    consecutivo_ot         INTEGER NOT NULL,
    fecha_elaboracion_ot   DATE,
    fecha_entrega_ot       DATE,
    kilometraje_ingreso_ot INTEGER,
    observacion_cli_ot     VARCHAR(500),
    observacion_ot         VARCHAR(500),
    placa_mot_ot           VARCHAR(6),
    documento_usu_rp_ot    VARCHAR(11),
    documento_usu_mc_ot    VARCHAR(11),
    cod_ot_est_ot          INTEGER,
    fecha_fin_garantia_ot  DATE,
    kilometraje_salida_ot  INTEGER,
    motivo_anulacion_ot        VARCHAR(500),
    fecha_anulacion_ot         TIMESTAMP,
    documento_usu_anulacion_ot VARCHAR(11),
    CONSTRAINT pk_ordenes_trabajo PRIMARY KEY (cod_taller, consecutivo_ot),
    CONSTRAINT fk_ot_taller   FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_ot_moto     FOREIGN KEY (cod_taller, placa_mot_ot)        REFERENCES motos (cod_taller, placa_mot),
    CONSTRAINT fk_ot_recep    FOREIGN KEY (cod_taller, documento_usu_rp_ot) REFERENCES usuarios (cod_taller, documento_usu),
    CONSTRAINT fk_ot_mecanico FOREIGN KEY (cod_taller, documento_usu_mc_ot) REFERENCES usuarios (cod_taller, documento_usu),
    CONSTRAINT fk_ot_estado   FOREIGN KEY (cod_ot_est_ot)                   REFERENCES ot_estados (cod_ot_est),
    CONSTRAINT fk_ot_anulacion FOREIGN KEY (cod_taller, documento_usu_anulacion_ot) REFERENCES usuarios (cod_taller, documento_usu),
    CONSTRAINT chk_ot_km_salida CHECK (kilometraje_salida_ot IS NULL OR kilometraje_salida_ot >= kilometraje_ingreso_ot)
);

CREATE TABLE detalle_orden_trabajo (
    cod_taller              INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    id_deto                 BIGINT  GENERATED ALWAYS AS IDENTITY,
    consecutivo_ot_deto     INTEGER NOT NULL,
    cod_pro_deto            INTEGER NOT NULL,
    fecha_confirmacion_deto DATE,
    valor_unitario_deto     INTEGER,
    cantidad_deto           NUMERIC(12, 3),   -- siempre positiva; permite fracciones (p.ej. 1.5 h de mano de obra)
    documento_usu_deto      VARCHAR(11),
    cobrar_deto             BOOLEAN NOT NULL DEFAULT true,          -- false: cortesía -- SÍ descuenta stock igual
    motivo_no_cobro_deto    VARCHAR(200),                           -- obligatorio si cobrar_deto = false
    CONSTRAINT pk_detalle_ot PRIMARY KEY (cod_taller, id_deto),
    CONSTRAINT fk_deto_taller   FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_deto_orden    FOREIGN KEY (cod_taller, consecutivo_ot_deto) REFERENCES ordenes_trabajo (cod_taller, consecutivo_ot),
    CONSTRAINT fk_deto_producto FOREIGN KEY (cod_taller, cod_pro_deto)        REFERENCES productos (cod_taller, cod_pro),
    CONSTRAINT fk_deto_usuario  FOREIGN KEY (cod_taller, documento_usu_deto)  REFERENCES usuarios (cod_taller, documento_usu),
    CONSTRAINT chk_deto_cantidad_positiva  CHECK (cantidad_deto > 0),
    CONSTRAINT chk_deto_motivo_si_no_cobra CHECK (cobrar_deto OR motivo_no_cobro_deto IS NOT NULL)
);

CREATE TABLE reclamos (
    cod_taller         INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    cod_rec            INTEGER NOT NULL DEFAULT nextval('seq_reclamos'),
    descripcion_rec    VARCHAR(500),
    consecutivo_ot_rec INTEGER,
    CONSTRAINT pk_reclamos PRIMARY KEY (cod_taller, cod_rec),
    CONSTRAINT fk_reclamos_taller FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_reclamos_orden  FOREIGN KEY (cod_taller, consecutivo_ot_rec) REFERENCES ordenes_trabajo (cod_taller, consecutivo_ot)
);

-- F1-07: pagos/abonos del CLIENTE del taller por una orden. Distinta a
-- propósito de `pagos` (billing de la plataforma vía Wompi, sin RLS -- ver
-- EXCEPCIONES_RLS): esta sí tiene cod_taller y RLS como el resto de tablas
-- del taller. No se edita ni se borra, solo se anula con motivo.
CREATE TABLE pagos_orden (
    cod_taller                    INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    cod_pago_orden                INTEGER NOT NULL DEFAULT nextval('seq_pagos_orden'),
    consecutivo_ot_pago           INTEGER NOT NULL,
    valor_pago                    NUMERIC(14, 2) NOT NULL,
    metodo_pago                   VARCHAR(20) NOT NULL,
    fecha_pago                    TIMESTAMP NOT NULL DEFAULT now(),
    documento_usu_pago            VARCHAR(11) NOT NULL,
    referencia_pago                VARCHAR(80),
    anulado_pago                  BOOLEAN NOT NULL DEFAULT false,
    motivo_anulacion_pago         VARCHAR(500),
    fecha_anulacion_pago          TIMESTAMP,
    documento_usu_anulacion_pago  VARCHAR(11),
    CONSTRAINT pk_pagos_orden PRIMARY KEY (cod_taller, cod_pago_orden),
    CONSTRAINT fk_po_taller    FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_po_orden     FOREIGN KEY (cod_taller, consecutivo_ot_pago) REFERENCES ordenes_trabajo (cod_taller, consecutivo_ot),
    CONSTRAINT fk_po_usuario   FOREIGN KEY (cod_taller, documento_usu_pago) REFERENCES usuarios (cod_taller, documento_usu),
    CONSTRAINT fk_po_usuario_anulacion FOREIGN KEY (cod_taller, documento_usu_anulacion_pago) REFERENCES usuarios (cod_taller, documento_usu),
    CONSTRAINT chk_po_valor_positivo CHECK (valor_pago > 0),
    CONSTRAINT chk_po_metodo CHECK (metodo_pago IN ('EFECTIVO', 'TRANSFERENCIA', 'NEQUI', 'DAVIPLATA', 'TARJETA', 'OTRO')),
    CONSTRAINT chk_po_anulacion_consistente CHECK (
        (NOT anulado_pago AND motivo_anulacion_pago IS NULL AND fecha_anulacion_pago IS NULL)
        OR (anulado_pago AND motivo_anulacion_pago IS NOT NULL AND fecha_anulacion_pago IS NOT NULL)
    )
);

ALTER TABLE pagos_orden ENABLE ROW LEVEL SECURITY;
ALTER TABLE pagos_orden FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_pagos_orden ON pagos_orden
    USING (cod_taller = current_setting('app.tenant_id', true)::integer)
    WITH CHECK (cod_taller = current_setting('app.tenant_id', true)::integer);

-- Inventario: kardex de movimientos de stock (ENTRADA/SALIDA/AJUSTE).
CREATE TABLE movimientos_inventario (
    cod_taller        INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    cod_mov           INTEGER NOT NULL DEFAULT nextval('seq_movimientos_inventario'),
    cod_pro_mov       INTEGER NOT NULL,
    tipo_mov          VARCHAR(10) NOT NULL,   -- ENTRADA / SALIDA / AJUSTE
    cantidad_mov      NUMERIC(12, 3) NOT NULL, -- delta aplicado al stock (+entra, -sale)
    stock_ant_mov     NUMERIC(12, 3),
    stock_nue_mov     NUMERIC(12, 3),
    motivo_mov        VARCHAR(255),
    documento_usu_mov VARCHAR(11),            -- quién lo hizo (auditoría, sin FK)
    fecha_mov         TIMESTAMP NOT NULL DEFAULT now(),
    referencia_mov    VARCHAR(50),            -- ej. "OT #12"; a futuro el cod_compra
    CONSTRAINT pk_mov_inv      PRIMARY KEY (cod_taller, cod_mov),
    CONSTRAINT fk_mov_taller   FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_mov_producto FOREIGN KEY (cod_taller, cod_pro_mov) REFERENCES productos (cod_taller, cod_pro),
    CONSTRAINT chk_mov_tipo    CHECK (tipo_mov IN ('ENTRADA', 'SALIDA', 'AJUSTE'))
);

-- Componentes de un paquete/combo (la "receta"/BOM). Cada PAQUETE incluye N
-- productos (BIEN o SERVICIO) con su cantidad. El precio lo pone el paquete.
CREATE TABLE paquete_componentes (
    cod_taller    INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    cod_paq_comp  INTEGER NOT NULL DEFAULT nextval('seq_paquete_componentes'),
    cod_pro_paq   INTEGER NOT NULL,                 -- el paquete (producto tipo PAQUETE)
    cod_pro_comp  INTEGER NOT NULL,                 -- el componente incluido
    cantidad_comp NUMERIC(12, 3) NOT NULL DEFAULT 1,
    CONSTRAINT pk_paq_comp      PRIMARY KEY (cod_taller, cod_paq_comp),
    CONSTRAINT fk_paqc_taller   FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_paqc_paquete  FOREIGN KEY (cod_taller, cod_pro_paq)  REFERENCES productos (cod_taller, cod_pro),
    CONSTRAINT fk_paqc_comp     FOREIGN KEY (cod_taller, cod_pro_comp) REFERENCES productos (cod_taller, cod_pro),
    CONSTRAINT chk_paqc_no_self CHECK (cod_pro_paq <> cod_pro_comp)
);

-- ============================================================
-- 4. TRIGGERS funcionales (ajustados a multi-taller)
-- ============================================================

-- La BD es la ÚNICA dueña del stock + kardex. INSERT descuenta, UPDATE ajusta el
-- delta, DELETE revierte. El servicio Python ya NO toca stock. El stock SIEMPRE
-- se descuenta para BIEN, se cobre o no (cobrar_deto=false es una cortesía, no
-- una excepción de inventario -- solo cambia el motivo que queda en el kardex).
-- Tipos: BIEN descuenta, SERVICIO no toca inventario, PAQUETE explota sus
-- componentes BIEN.

-- INSERT
CREATE OR REPLACE FUNCTION fn_actualizar_stock()
RETURNS TRIGGER AS $$
DECLARE
    v_tipo   TEXT;
    v_ant    NUMERIC(12, 3);
    v_nue    NUMERIC(12, 3);
    v_cant   NUMERIC(12, 3);
    v_motivo VARCHAR(255);
    r        RECORD;
BEGIN
    SELECT tipo_pro INTO v_tipo FROM productos
     WHERE cod_pro = NEW.cod_pro_deto AND cod_taller = NEW.cod_taller;

    IF v_tipo = 'SERVICIO' THEN
        RETURN NEW;
    END IF;

    v_motivo := CASE WHEN NEW.cobrar_deto THEN 'Uso en orden de trabajo'
                     ELSE 'Cortesía OT #' || NEW.consecutivo_ot_deto END;

    IF v_tipo = 'PAQUETE' THEN
        FOR r IN
            SELECT pc.cod_pro_comp, pc.cantidad_comp, p.tipo_pro AS tipo_comp
              FROM paquete_componentes pc
              JOIN productos p ON p.cod_pro = pc.cod_pro_comp AND p.cod_taller = pc.cod_taller
             WHERE pc.cod_pro_paq = NEW.cod_pro_deto AND pc.cod_taller = NEW.cod_taller
        LOOP
            IF r.tipo_comp = 'BIEN' THEN
                v_cant := r.cantidad_comp * NEW.cantidad_deto;
                SELECT stock_pro INTO v_ant FROM productos
                 WHERE cod_pro = r.cod_pro_comp AND cod_taller = NEW.cod_taller;
                v_nue := COALESCE(v_ant, 0) - v_cant;
                UPDATE productos SET stock_pro = v_nue
                 WHERE cod_pro = r.cod_pro_comp AND cod_taller = NEW.cod_taller;
                INSERT INTO movimientos_inventario
                  (cod_taller, cod_pro_mov, tipo_mov, cantidad_mov, stock_ant_mov, stock_nue_mov,
                   motivo_mov, documento_usu_mov, referencia_mov)
                VALUES
                  (NEW.cod_taller, r.cod_pro_comp, 'SALIDA', -v_cant, v_ant, v_nue,
                   CASE WHEN NEW.cobrar_deto THEN 'Componente de paquete'
                        ELSE 'Componente de paquete (Cortesía OT #' || NEW.consecutivo_ot_deto || ')' END,
                   NEW.documento_usu_deto, 'OT #' || NEW.consecutivo_ot_deto);
            END IF;
        END LOOP;
        RETURN NEW;
    END IF;

    IF v_tipo IS DISTINCT FROM 'BIEN' THEN
        RETURN NEW;
    END IF;

    -- BIEN
    v_cant := NEW.cantidad_deto;
    SELECT stock_pro INTO v_ant FROM productos
     WHERE cod_pro = NEW.cod_pro_deto AND cod_taller = NEW.cod_taller;
    v_nue := COALESCE(v_ant, 0) - v_cant;
    UPDATE productos SET stock_pro = v_nue
     WHERE cod_pro = NEW.cod_pro_deto AND cod_taller = NEW.cod_taller;
    INSERT INTO movimientos_inventario
      (cod_taller, cod_pro_mov, tipo_mov, cantidad_mov, stock_ant_mov, stock_nue_mov,
       motivo_mov, documento_usu_mov, referencia_mov)
    VALUES
      (NEW.cod_taller, NEW.cod_pro_deto, 'SALIDA', -v_cant, v_ant, v_nue,
       v_motivo, NEW.documento_usu_deto, 'OT #' || NEW.consecutivo_ot_deto);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_actualizar_stock
AFTER INSERT ON detalle_orden_trabajo
FOR EACH ROW EXECUTE FUNCTION fn_actualizar_stock();

-- DELETE: revertir el stock al quitar un detalle. BIEN devuelve su stock; PAQUETE
-- devuelve el de cada componente BIEN; SERVICIO no toca inventario.
CREATE OR REPLACE FUNCTION fn_revertir_stock_detalle()
RETURNS TRIGGER AS $$
DECLARE
    v_tipo TEXT;
    v_ant  NUMERIC(12, 3);
    v_nue  NUMERIC(12, 3);
    v_cant NUMERIC(12, 3);
    r      RECORD;
BEGIN
    SELECT tipo_pro INTO v_tipo FROM productos
     WHERE cod_pro = OLD.cod_pro_deto AND cod_taller = OLD.cod_taller;

    IF v_tipo = 'PAQUETE' THEN
        FOR r IN
            SELECT pc.cod_pro_comp, pc.cantidad_comp, p.tipo_pro AS tipo_comp
              FROM paquete_componentes pc
              JOIN productos p ON p.cod_pro = pc.cod_pro_comp AND p.cod_taller = pc.cod_taller
             WHERE pc.cod_pro_paq = OLD.cod_pro_deto AND pc.cod_taller = OLD.cod_taller
        LOOP
            IF r.tipo_comp = 'BIEN' THEN
                v_cant := r.cantidad_comp * OLD.cantidad_deto;
                SELECT stock_pro INTO v_ant FROM productos
                 WHERE cod_pro = r.cod_pro_comp AND cod_taller = OLD.cod_taller;
                v_nue := COALESCE(v_ant, 0) + v_cant;
                UPDATE productos SET stock_pro = v_nue
                 WHERE cod_pro = r.cod_pro_comp AND cod_taller = OLD.cod_taller;
                INSERT INTO movimientos_inventario
                  (cod_taller, cod_pro_mov, tipo_mov, cantidad_mov, stock_ant_mov, stock_nue_mov,
                   motivo_mov, documento_usu_mov, referencia_mov)
                VALUES
                  (OLD.cod_taller, r.cod_pro_comp, 'AJUSTE', v_cant, v_ant, v_nue,
                   'Reversa componente de paquete', OLD.documento_usu_deto, 'OT #' || OLD.consecutivo_ot_deto);
            END IF;
        END LOOP;
        RETURN OLD;
    END IF;

    IF v_tipo IS DISTINCT FROM 'BIEN' THEN
        RETURN OLD;
    END IF;

    v_cant := OLD.cantidad_deto;
    SELECT stock_pro INTO v_ant FROM productos
     WHERE cod_pro = OLD.cod_pro_deto AND cod_taller = OLD.cod_taller;
    v_nue := COALESCE(v_ant, 0) + v_cant;
    UPDATE productos SET stock_pro = v_nue
     WHERE cod_pro = OLD.cod_pro_deto AND cod_taller = OLD.cod_taller;
    INSERT INTO movimientos_inventario
      (cod_taller, cod_pro_mov, tipo_mov, cantidad_mov, stock_ant_mov, stock_nue_mov,
       motivo_mov, documento_usu_mov, referencia_mov)
    VALUES
      (OLD.cod_taller, OLD.cod_pro_deto, 'AJUSTE', v_cant, v_ant, v_nue,
       'Reversa por eliminación de OT', OLD.documento_usu_deto, 'OT #' || OLD.consecutivo_ot_deto);
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_revertir_stock
AFTER DELETE ON detalle_orden_trabajo
FOR EACH ROW EXECUTE FUNCTION fn_revertir_stock_detalle();

-- UPDATE: ajustar el stock por el delta al cambiar la cantidad. BIEN ajusta su
-- stock; PAQUETE ajusta el de cada componente BIEN; SERVICIO no toca inventario.
CREATE OR REPLACE FUNCTION fn_ajustar_stock_detalle()
RETURNS TRIGGER AS $$
DECLARE
    v_tipo   TEXT;
    v_ant    NUMERIC(12, 3);
    v_nue    NUMERIC(12, 3);
    v_delta  NUMERIC(12, 3);
    v_motivo VARCHAR(255);
    r        RECORD;
BEGIN
    IF NEW.cod_pro_deto <> OLD.cod_pro_deto THEN
        RETURN NEW;
    END IF;
    IF NEW.cantidad_deto = OLD.cantidad_deto THEN
        RETURN NEW;
    END IF;

    SELECT tipo_pro INTO v_tipo FROM productos
     WHERE cod_pro = NEW.cod_pro_deto AND cod_taller = NEW.cod_taller;

    v_motivo := CASE WHEN NEW.cobrar_deto THEN 'Edición de OT'
                     ELSE 'Edición de OT (Cortesía OT #' || NEW.consecutivo_ot_deto || ')' END;

    IF v_tipo = 'PAQUETE' THEN
        FOR r IN
            SELECT pc.cod_pro_comp, pc.cantidad_comp, p.tipo_pro AS tipo_comp
              FROM paquete_componentes pc
              JOIN productos p ON p.cod_pro = pc.cod_pro_comp AND p.cod_taller = pc.cod_taller
             WHERE pc.cod_pro_paq = NEW.cod_pro_deto AND pc.cod_taller = NEW.cod_taller
        LOOP
            IF r.tipo_comp = 'BIEN' THEN
                v_delta := r.cantidad_comp * (NEW.cantidad_deto - OLD.cantidad_deto);
                IF v_delta <> 0 THEN
                    SELECT stock_pro INTO v_ant FROM productos
                     WHERE cod_pro = r.cod_pro_comp AND cod_taller = NEW.cod_taller;
                    v_nue := COALESCE(v_ant, 0) - v_delta;
                    UPDATE productos SET stock_pro = v_nue
                     WHERE cod_pro = r.cod_pro_comp AND cod_taller = NEW.cod_taller;
                    INSERT INTO movimientos_inventario
                      (cod_taller, cod_pro_mov, tipo_mov, cantidad_mov, stock_ant_mov, stock_nue_mov,
                       motivo_mov, documento_usu_mov, referencia_mov)
                    VALUES
                      (NEW.cod_taller, r.cod_pro_comp, 'AJUSTE', -v_delta, v_ant, v_nue,
                       'Edición de paquete en OT', NEW.documento_usu_deto, 'OT #' || NEW.consecutivo_ot_deto);
                END IF;
            END IF;
        END LOOP;
        RETURN NEW;
    END IF;

    IF v_tipo IS DISTINCT FROM 'BIEN' THEN
        RETURN NEW;
    END IF;

    v_delta := NEW.cantidad_deto - OLD.cantidad_deto;
    SELECT stock_pro INTO v_ant FROM productos
     WHERE cod_pro = NEW.cod_pro_deto AND cod_taller = NEW.cod_taller;
    v_nue := COALESCE(v_ant, 0) - v_delta;
    UPDATE productos SET stock_pro = v_nue
     WHERE cod_pro = NEW.cod_pro_deto AND cod_taller = NEW.cod_taller;
    INSERT INTO movimientos_inventario
      (cod_taller, cod_pro_mov, tipo_mov, cantidad_mov, stock_ant_mov, stock_nue_mov,
       motivo_mov, documento_usu_mov, referencia_mov)
    VALUES
      (NEW.cod_taller, NEW.cod_pro_deto, 'AJUSTE', -v_delta, v_ant, v_nue,
       v_motivo, NEW.documento_usu_deto, 'OT #' || NEW.consecutivo_ot_deto);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_ajustar_stock
AFTER UPDATE ON detalle_orden_trabajo
FOR EACH ROW EXECUTE FUNCTION fn_ajustar_stock_detalle();

-- Consecutivo de OT POR TALLER (cada taller numera desde 1)
CREATE OR REPLACE FUNCTION fn_gen_consecutivo_ot()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.consecutivo_ot IS NULL THEN
        SELECT COALESCE(MAX(consecutivo_ot), 0) + 1
          INTO NEW.consecutivo_ot
          FROM ordenes_trabajo
         WHERE cod_taller = NEW.cod_taller;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_gen_consecutivo_ot
BEFORE INSERT ON ordenes_trabajo
FOR EACH ROW EXECUTE FUNCTION fn_gen_consecutivo_ot();

-- F1-04: la garantía de una orden la fijaba un trigger con el número de días
-- configurado en "Mi taller" (dias_garantia_pred), igual para toda orden sin
-- importar qué se hizo -- el campo manual del formulario (con su validación
-- de "mínimo 30 días") nunca tenía efecto, porque el trigger la pisaba
-- siempre al entregar. Ahora la garantía la da el servicio/producto más
-- largo de la orden (MAX(dias_garantia_pro) de sus ítems); 0 = sin garantía.
CREATE OR REPLACE FUNCTION fn_calc_fecha_garantia()
RETURNS TRIGGER AS $$
DECLARE
    v_dias_garantia INTEGER;
BEGIN
    IF NEW.cod_ot_est_ot = 4 THEN
        SELECT COALESCE(MAX(p.dias_garantia_pro), 0) INTO v_dias_garantia
        FROM detalle_orden_trabajo d
        JOIN productos p ON d.cod_pro_deto = p.cod_pro AND d.cod_taller = p.cod_taller
        WHERE d.consecutivo_ot_deto = NEW.consecutivo_ot AND d.cod_taller = NEW.cod_taller;

        IF v_dias_garantia > 0 AND NEW.fecha_entrega_ot IS NOT NULL THEN
            NEW.fecha_fin_garantia_ot := NEW.fecha_entrega_ot + make_interval(days => v_dias_garantia);
        ELSE
            NEW.fecha_fin_garantia_ot := NULL;
        END IF;
    ELSE
        NEW.fecha_fin_garantia_ot := NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_calc_fecha_garantia
BEFORE INSERT OR UPDATE ON ordenes_trabajo
FOR EACH ROW EXECUTE FUNCTION fn_calc_fecha_garantia();

-- ============================================================
-- 5. AUDITORÍA (audit_log con cod_taller)
-- ============================================================
CREATE TABLE audit_log (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cod_taller      INTEGER,
    fecha           TIMESTAMP    NOT NULL DEFAULT now(),
    usuario         VARCHAR(100) DEFAULT session_user,
    tabla           VARCHAR(100),
    evento          CHAR(1),
    valor_anterior  JSONB,
    valor_nuevo     JSONB
);

CREATE OR REPLACE FUNCTION fn_audit()
RETURNS TRIGGER AS $$
DECLARE
    v_taller  INTEGER;
    v_usuario VARCHAR(100);
BEGIN
    v_usuario := current_setting('app.usuario', true);
    IF v_usuario IS NULL OR v_usuario = '' THEN
        v_usuario := session_user;
    END IF;

    IF TG_OP = 'DELETE' THEN
        v_taller := OLD.cod_taller;
        INSERT INTO audit_log (cod_taller, usuario, tabla, evento, valor_anterior)
        VALUES (v_taller, v_usuario, TG_TABLE_NAME, 'D', to_jsonb(OLD));
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        v_taller := NEW.cod_taller;
        INSERT INTO audit_log (cod_taller, usuario, tabla, evento, valor_anterior, valor_nuevo)
        VALUES (v_taller, v_usuario, TG_TABLE_NAME, 'U', to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    ELSE
        v_taller := NEW.cod_taller;
        INSERT INTO audit_log (cod_taller, usuario, tabla, evento, valor_nuevo)
        VALUES (v_taller, v_usuario, TG_TABLE_NAME, 'I', to_jsonb(NEW));
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_audit_clientes AFTER INSERT OR UPDATE OR DELETE ON clientes
FOR EACH ROW EXECUTE FUNCTION fn_audit();
CREATE TRIGGER tg_audit_productos AFTER INSERT OR UPDATE OR DELETE ON productos
FOR EACH ROW EXECUTE FUNCTION fn_audit();
CREATE TRIGGER tg_audit_ordenes_trabajo AFTER INSERT OR UPDATE OR DELETE ON ordenes_trabajo
FOR EACH ROW EXECUTE FUNCTION fn_audit();
CREATE TRIGGER tg_audit_detalle_orden_trabajo AFTER INSERT OR UPDATE OR DELETE ON detalle_orden_trabajo
FOR EACH ROW EXECUTE FUNCTION fn_audit();
CREATE TRIGGER tg_audit_usuarios AFTER INSERT OR UPDATE OR DELETE ON usuarios
FOR EACH ROW EXECUTE FUNCTION fn_audit();
CREATE TRIGGER tg_audit_pagos_orden AFTER INSERT OR UPDATE OR DELETE ON pagos_orden
FOR EACH ROW EXECUTE FUNCTION fn_audit();

-- ============================================================
-- 5b. IDENTIDAD (sub Auth0 -> taller). SIN RLS: permite al backend resolver
--     el taller del usuario ANTES de fijar app.tenant_id (usuarios sí tiene RLS).
--     Se mantiene en sync con usuarios mediante un trigger.
-- ============================================================
CREATE TABLE usuarios_identidad (
    cod_taller    INTEGER NOT NULL REFERENCES talleres (cod_taller),
    documento_usu VARCHAR(11) NOT NULL,
    correo_usu    VARCHAR(50),
    sub_id_usu    VARCHAR(250),   -- NULL hasta el primer login (se vincula ahí)
    CONSTRAINT pk_usuarios_identidad PRIMARY KEY (cod_taller, documento_usu)
);
CREATE INDEX ix_identidad_sub    ON usuarios_identidad (sub_id_usu);
CREATE INDEX ix_identidad_correo ON usuarios_identidad (lower(correo_usu));

CREATE OR REPLACE FUNCTION fn_sync_identidad()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        DELETE FROM usuarios_identidad
         WHERE cod_taller = OLD.cod_taller AND documento_usu = OLD.documento_usu;
        RETURN OLD;
    END IF;
    INSERT INTO usuarios_identidad (cod_taller, documento_usu, correo_usu, sub_id_usu)
    VALUES (NEW.cod_taller, NEW.documento_usu, NEW.correo_usu, NEW.sub_id_usu)
    ON CONFLICT (cod_taller, documento_usu)
    DO UPDATE SET correo_usu = EXCLUDED.correo_usu, sub_id_usu = EXCLUDED.sub_id_usu;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_sync_identidad
AFTER INSERT OR UPDATE OR DELETE ON usuarios
FOR EACH ROW EXECUTE FUNCTION fn_sync_identidad();

-- ============================================================
-- 5c. SUPER-ADMIN DE PLATAFORMA (F0-14). SIN RLS a propósito: el super-admin
--     necesita ver auditoría/notas de TODOS los talleres, no aisladas por
--     tenant (igual motivo que talleres/pagos, ver rls_policy.py).
-- ============================================================
CREATE TABLE auditoria_superadmin (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario        VARCHAR(100) NOT NULL,
    fecha          TIMESTAMP    NOT NULL DEFAULT now(),
    cod_taller     INTEGER REFERENCES talleres (cod_taller),
    accion         VARCHAR(50)  NOT NULL,
    valor_anterior JSONB,
    valor_nuevo    JSONB,
    motivo         TEXT         NOT NULL
);

CREATE TABLE notas_taller (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cod_taller INTEGER NOT NULL REFERENCES talleres (cod_taller),
    autor      VARCHAR(100) NOT NULL,
    fecha      TIMESTAMP NOT NULL DEFAULT now(),
    texto      TEXT NOT NULL
);

-- ============================================================
-- 6. RLS (Row-Level Security) en las tablas por taller
--    Política: solo filas del taller actual (app.tenant_id).
--    FORCE para que aplique también al dueño de las tablas (el usuario de la app).
-- ============================================================
DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'perfiles','perfiles_permisos',
    'usuarios','clientes','marcas','motos','impuestos','productos',
    'productos_impuestos','ordenes_trabajo','detalle_orden_trabajo','reclamos','movimientos_inventario',
    'paquete_componentes'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY;', t);
    EXECUTE format($f$
      CREATE POLICY tenant_isolation ON %I
      USING (cod_taller = current_setting('app.tenant_id', true)::integer)
      WITH CHECK (cod_taller = current_setting('app.tenant_id', true)::integer);
    $f$, t);
  END LOOP;
END $$;

-- audit_log: RLS de solo lectura por taller (lo escribe el trigger en SECURITY DEFINER-like contexto del owner)
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_audit ON audit_log
  USING (cod_taller = current_setting('app.tenant_id', true)::integer)
  WITH CHECK (true);

-- ============================================================
-- 7. VISTAS (security_invoker=on => respetan el RLS del usuario que consulta)
-- ============================================================

CREATE OR REPLACE VIEW vw_ordenes_trabajo_completa WITH (security_invoker = on) AS
SELECT
    ot.consecutivo_ot, ot.fecha_elaboracion_ot, ot.fecha_entrega_ot,
    ot.kilometraje_ingreso_ot,
    ot.observacion_cli_ot, ot.observacion_ot,
    ot.fecha_fin_garantia_ot,
    m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot,
    mar.nombre_mar AS marca_moto,
    c.documento_cli,
    c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo_cliente,
    c.telefono_cli, c.correo_cli, c.direccion_cli,
    urp.documento_usu AS documento_recepcionista,
    urp.nombre_usu || ' ' || urp.apellido_1_usu AS recepcionista,
    umc.documento_usu AS documento_mecanico,
    umc.nombre_usu || ' ' || umc.apellido_1_usu AS mecanico,
    ote.nombre_ot_est AS estado_ot, ot.cod_ot_est_ot,
    (SELECT STRING_AGG(p.nombre_pro, ', ' ORDER BY p.nombre_pro)
       FROM detalle_orden_trabajo dot
       JOIN productos p ON dot.cod_pro_deto = p.cod_pro AND dot.cod_taller = p.cod_taller
      WHERE dot.consecutivo_ot_deto = ot.consecutivo_ot AND dot.cod_taller = ot.cod_taller
    ) AS trabajos,
    ot.kilometraje_salida_ot,
    ot.motivo_anulacion_ot, ot.fecha_anulacion_ot, ot.documento_usu_anulacion_ot
FROM ordenes_trabajo ot
INNER JOIN motos m       ON ot.placa_mot_ot = m.placa_mot AND ot.cod_taller = m.cod_taller
INNER JOIN clientes c    ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller
INNER JOIN marcas mar    ON m.cod_marca_mot = mar.cod_mar AND m.cod_taller = mar.cod_taller
INNER JOIN usuarios urp  ON ot.documento_usu_rp_ot = urp.documento_usu AND ot.cod_taller = urp.cod_taller
LEFT JOIN usuarios umc   ON ot.documento_usu_mc_ot = umc.documento_usu AND ot.cod_taller = umc.cod_taller
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est;

CREATE OR REPLACE VIEW vw_detalle_ot_productos WITH (security_invoker = on) AS
SELECT
    dot.consecutivo_ot_deto, dot.cod_pro_deto,
    p.nombre_pro, p.descripcion_pro, dot.cantidad_deto, dot.valor_unitario_deto,
    dot.cobrar_deto, dot.motivo_no_cobro_deto,
    (dot.cantidad_deto * dot.valor_unitario_deto) AS subtotal,
    dot.fecha_confirmacion_deto,
    u.nombre_usu || ' ' || u.apellido_1_usu AS usuario_confirmacion,
    e.nombre_est AS estado_producto
FROM detalle_orden_trabajo dot
INNER JOIN productos p ON dot.cod_pro_deto = p.cod_pro AND dot.cod_taller = p.cod_taller
INNER JOIN usuarios u  ON dot.documento_usu_deto = u.documento_usu AND dot.cod_taller = u.cod_taller
INNER JOIN estados e   ON p.cod_est_pro = e.cod_est;

-- F1-07: total_pagado/saldo_ot al final (no se puede reordenar una vista
-- existente con CREATE OR REPLACE, solo añadir al final). Excluye pagos
-- anulados; saldo_ot puede ser negativo si se sobrepagó (no hay bloqueo de
-- sobrepago -- no es un criterio de este ticket).
CREATE OR REPLACE VIEW vw_resumen_financiero_ot WITH (security_invoker = on) AS
SELECT
    ot.consecutivo_ot, ot.fecha_elaboracion_ot,
    c.nombre_cli || ' ' || c.apellido_1_cli AS cliente, m.placa_mot,
    COUNT(CASE WHEN dot.cobrar_deto THEN dot.cod_pro_deto END) AS total_items,
    SUM(CASE WHEN dot.cobrar_deto THEN dot.cantidad_deto * dot.valor_unitario_deto ELSE 0 END) AS subtotal_productos,
    0 AS total_impuestos,
    SUM(CASE WHEN dot.cobrar_deto THEN dot.cantidad_deto * dot.valor_unitario_deto ELSE 0 END) AS total_ot,
    COALESCE(pg.total_pagado, 0) AS total_pagado,
    SUM(CASE WHEN dot.cobrar_deto THEN dot.cantidad_deto * dot.valor_unitario_deto ELSE 0 END) - COALESCE(pg.total_pagado, 0) AS saldo_ot
FROM ordenes_trabajo ot
INNER JOIN detalle_orden_trabajo dot ON ot.consecutivo_ot = dot.consecutivo_ot_deto AND ot.cod_taller = dot.cod_taller
INNER JOIN motos m    ON ot.placa_mot_ot = m.placa_mot AND ot.cod_taller = m.cod_taller
INNER JOIN clientes c ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller
LEFT JOIN (
    SELECT cod_taller, consecutivo_ot_pago, SUM(valor_pago) AS total_pagado
    FROM pagos_orden
    WHERE NOT anulado_pago
    GROUP BY cod_taller, consecutivo_ot_pago
) pg ON pg.cod_taller = ot.cod_taller AND pg.consecutivo_ot_pago = ot.consecutivo_ot
GROUP BY ot.consecutivo_ot, ot.fecha_elaboracion_ot, c.nombre_cli, c.apellido_1_cli, m.placa_mot, pg.total_pagado;

-- F1-07: lista de abonos de una orden, con el nombre de quien registró/anuló.
CREATE OR REPLACE VIEW vw_pagos_orden WITH (security_invoker = on) AS
SELECT
    po.cod_pago_orden, po.consecutivo_ot_pago, po.valor_pago, po.metodo_pago,
    po.fecha_pago, po.documento_usu_pago,
    u.nombre_usu || ' ' || u.apellido_1_usu AS usuario_pago,
    po.referencia_pago, po.anulado_pago,
    po.motivo_anulacion_pago, po.fecha_anulacion_pago, po.documento_usu_anulacion_pago
FROM pagos_orden po
INNER JOIN usuarios u ON po.cod_taller = u.cod_taller AND po.documento_usu_pago = u.documento_usu;

-- Vistas de dominio para que los repos de inventario/paquetes no consulten `productos`.
CREATE OR REPLACE VIEW vw_movimientos_inventario WITH (security_invoker = on) AS
SELECT m.cod_mov, m.cod_pro_mov, p.nombre_pro, m.tipo_mov, m.cantidad_mov,
       m.stock_ant_mov, m.stock_nue_mov, m.motivo_mov, m.documento_usu_mov,
       to_char(m.fecha_mov, 'YYYY-MM-DD HH24:MI') AS fecha_mov, m.referencia_mov
FROM movimientos_inventario m
JOIN productos p ON p.cod_pro = m.cod_pro_mov AND p.cod_taller = m.cod_taller;

CREATE OR REPLACE VIEW vw_paquete_componentes WITH (security_invoker = on) AS
SELECT pc.cod_paq_comp, pc.cod_pro_paq, pc.cod_pro_comp, pc.cantidad_comp,
       p.nombre_pro, p.tipo_pro, p.stock_pro
FROM paquete_componentes pc
JOIN productos p ON p.cod_pro = pc.cod_pro_comp AND p.cod_taller = pc.cod_taller;

-- Vistas de dominio para dashboard y tablero (que sus repos no lean tablas ajenas).
CREATE OR REPLACE VIEW vw_dashboard_resumen WITH (security_invoker = on) AS
SELECT
  (SELECT count(*) FROM clientes)        AS total_clientes,
  (SELECT count(*) FROM motos)           AS total_motos,
  (SELECT count(*) FROM productos)       AS total_productos,
  (SELECT count(*) FROM ordenes_trabajo) AS total_ordenes,
  (SELECT count(*) FROM ordenes_trabajo WHERE cod_ot_est_ot IN (1, 2, 6)) AS ot_activas,
  (SELECT count(*) FROM productos
     WHERE cod_est_pro = 1 AND stock_pro <= stock_pro_min)               AS productos_bajo_stock,
  (SELECT count(*) FROM reclamos)        AS total_reclamos;

CREATE OR REPLACE VIEW vw_dashboard_ordenes_por_estado WITH (security_invoker = on) AS
SELECT e.cod_ot_est, e.nombre_ot_est, COUNT(o.consecutivo_ot) AS cantidad
FROM ot_estados e
LEFT JOIN ordenes_trabajo o ON o.cod_ot_est_ot = e.cod_ot_est
GROUP BY e.cod_ot_est, e.nombre_ot_est;

CREATE OR REPLACE VIEW vw_mecanicos WITH (security_invoker = on) AS
SELECT documento_usu, nombre_usu || ' ' || COALESCE(apellido_1_usu, '') AS nombre
FROM usuarios
WHERE NOT es_admin_usu AND cod_est_usu = 1;

CREATE OR REPLACE VIEW vw_ot_pendientes WITH (security_invoker = on) AS
SELECT
    ot.consecutivo_ot, ot.fecha_elaboracion_ot,
    (CURRENT_DATE - ot.fecha_elaboracion_ot) AS dias_pendiente,
    c.nombre_cli || ' ' || c.apellido_1_cli AS cliente, c.telefono_cli,
    m.placa_mot, mar.nombre_mar || ' ' || m.modelo_mot AS moto,
    umc.nombre_usu || ' ' || umc.apellido_1_usu AS mecanico_asignado,
    ote.nombre_ot_est AS estado
FROM ordenes_trabajo ot
INNER JOIN motos m        ON ot.placa_mot_ot = m.placa_mot AND ot.cod_taller = m.cod_taller
INNER JOIN marcas mar     ON m.cod_marca_mot = mar.cod_mar AND m.cod_taller = mar.cod_taller
INNER JOIN clientes c     ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller
LEFT JOIN usuarios umc    ON ot.documento_usu_mc_ot = umc.documento_usu AND ot.cod_taller = umc.cod_taller
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est
WHERE ot.fecha_entrega_ot IS NULL
ORDER BY ot.fecha_elaboracion_ot;

CREATE OR REPLACE VIEW vw_reclamos_completo WITH (security_invoker = on) AS
SELECT
    rec.cod_rec, rec.descripcion_rec, rec.consecutivo_ot_rec,
    ot.fecha_elaboracion_ot, ot.fecha_entrega_ot, ot.kilometraje_ingreso_ot,
    ot.observacion_cli_ot, ot.observacion_ot, ot.fecha_fin_garantia_ot,
    ote.nombre_ot_est AS estado_ot,
    m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot,
    mar.nombre_mar AS marca_moto,
    mar.nombre_mar || ' ' || m.modelo_mot || ' (' || m.placa_mot || ')' AS moto_completa,
    c.documento_cli,
    c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo_cliente,
    c.telefono_cli, c.correo_cli, c.direccion_cli,
    urp.documento_usu AS documento_recepcionista,
    urp.nombre_usu || ' ' || urp.apellido_1_usu AS recepcionista,
    umc.documento_usu AS documento_mecanico,
    umc.nombre_usu || ' ' || umc.apellido_1_usu AS mecanico,
    CASE
        WHEN ot.fecha_fin_garantia_ot >= CURRENT_DATE THEN 'VIGENTE'
        WHEN ot.fecha_fin_garantia_ot <  CURRENT_DATE THEN 'VENCIDA'
        ELSE 'SIN INFORMACIÓN'
    END AS estado_garantia,
    CASE WHEN ot.fecha_fin_garantia_ot >= CURRENT_DATE
         THEN (ot.fecha_fin_garantia_ot - CURRENT_DATE) ELSE NULL END AS dias_garantia_restantes
FROM reclamos rec
INNER JOIN ordenes_trabajo ot ON rec.consecutivo_ot_rec = ot.consecutivo_ot AND rec.cod_taller = ot.cod_taller
INNER JOIN motos m       ON ot.placa_mot_ot = m.placa_mot AND ot.cod_taller = m.cod_taller
INNER JOIN clientes c    ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller
INNER JOIN marcas mar    ON m.cod_marca_mot = mar.cod_mar AND m.cod_taller = mar.cod_taller
INNER JOIN usuarios urp  ON ot.documento_usu_rp_ot = urp.documento_usu AND ot.cod_taller = urp.cod_taller
LEFT JOIN usuarios umc   ON ot.documento_usu_mc_ot = umc.documento_usu AND ot.cod_taller = umc.cod_taller
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est;

CREATE OR REPLACE VIEW vw_reclamos_detalle WITH (security_invoker = on) AS
SELECT
    rec.cod_rec, rec.descripcion_rec, ot.consecutivo_ot,
    ot.fecha_elaboracion_ot, ot.fecha_entrega_ot, m.placa_mot,
    c.nombre_cli || ' ' || c.apellido_1_cli AS cliente, c.telefono_cli,
    ote.nombre_ot_est AS estado_ot
FROM reclamos rec
INNER JOIN ordenes_trabajo ot ON rec.consecutivo_ot_rec = ot.consecutivo_ot AND rec.cod_taller = ot.cod_taller
INNER JOIN motos m       ON ot.placa_mot_ot = m.placa_mot AND ot.cod_taller = m.cod_taller
INNER JOIN clientes c    ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est;

CREATE OR REPLACE VIEW vw_productos WITH (security_invoker = on) AS
SELECT p.cod_pro, p.nombre_pro, p.descripcion_pro, p.precio_pro,
       p.stock_pro, p.stock_pro_min, p.unidad_pro, p.cod_est_pro, e.nombre_est AS estado_producto,
       p.tipo_pro, p.dias_garantia_pro
FROM productos p INNER JOIN estados e ON p.cod_est_pro = e.cod_est;

CREATE OR REPLACE VIEW vw_productos_activos WITH (security_invoker = on) AS
SELECT p.cod_pro, p.nombre_pro, p.descripcion_pro, p.precio_pro,
       p.stock_pro, p.stock_pro_min, p.unidad_pro, p.cod_est_pro, e.nombre_est AS estado_producto,
       p.tipo_pro, p.dias_garantia_pro
FROM productos p INNER JOIN estados e ON p.cod_est_pro = e.cod_est
WHERE p.cod_est_pro = 1;

CREATE OR REPLACE VIEW vw_productos_impuestos WITH (security_invoker = on) AS
SELECT pi.cod_pro_imp, pi.cod_imp_pro_imp, pi.cod_pro_pro_imp, pi.porcentaje_pro_imp,
       i.cod_imp, i.nombre_imp, i.porcentaje_imp
FROM productos_impuestos pi
INNER JOIN impuestos i ON pi.cod_imp_pro_imp = i.cod_imp AND pi.cod_taller = i.cod_taller;

CREATE OR REPLACE VIEW vw_productos_con_impuestos WITH (security_invoker = on) AS
SELECT p.cod_pro, p.nombre_pro, p.descripcion_pro, p.precio_pro,
       p.stock_pro, p.stock_pro_min, p.unidad_pro, e.nombre_est AS estado_producto,
       pi.cod_pro_imp, i.nombre_imp, pi.porcentaje_pro_imp,
       ROUND(p.precio_pro * (pi.porcentaje_pro_imp / 100), 2) AS valor_impuesto,
       ROUND(p.precio_pro + (p.precio_pro * (pi.porcentaje_pro_imp / 100)), 2) AS precio_con_impuesto
FROM productos p
INNER JOIN estados e ON p.cod_est_pro = e.cod_est
LEFT JOIN productos_impuestos pi ON p.cod_pro = pi.cod_pro_pro_imp AND p.cod_taller = pi.cod_taller
LEFT JOIN impuestos i ON pi.cod_imp_pro_imp = i.cod_imp AND pi.cod_taller = i.cod_taller;

CREATE OR REPLACE VIEW vw_inventario_alertas WITH (security_invoker = on) AS
SELECT p.cod_pro, p.nombre_pro, p.descripcion_pro,
       p.stock_pro, p.stock_pro_min, p.precio_pro, e.nombre_est AS estado,
       CASE
           WHEN p.stock_pro = 0 THEN 'SIN STOCK'
           WHEN p.stock_pro <= p.stock_pro_min THEN 'STOCK BAJO'
           WHEN p.stock_pro > p.stock_pro_min AND p.stock_pro <= (p.stock_pro_min * 2) THEN 'STOCK MEDIO'
           ELSE 'STOCK NORMAL'
       END AS nivel_alerta,
       (p.stock_pro_min - p.stock_pro) AS cantidad_a_pedir
FROM productos p INNER JOIN estados e ON p.cod_est_pro = e.cod_est;

CREATE OR REPLACE VIEW vw_clientes WITH (security_invoker = on) AS
SELECT c.documento_cli, c.nombre_cli, c.apellido_1_cli, c.apellido_2_cli,
       c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo,
       c.telefono_cli, c.correo_cli, c.direccion_cli
FROM clientes c;

CREATE OR REPLACE VIEW vw_clientes_resumen WITH (security_invoker = on) AS
SELECT c.documento_cli,
       c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo,
       c.telefono_cli, c.correo_cli, c.direccion_cli,
       COUNT(m.placa_mot) AS total_motos
FROM clientes c
LEFT JOIN motos m ON c.documento_cli = m.documento_cli_mot AND c.cod_taller = m.cod_taller
GROUP BY c.documento_cli, c.nombre_cli, c.apellido_1_cli, c.apellido_2_cli,
         c.telefono_cli, c.correo_cli, c.direccion_cli;

CREATE OR REPLACE VIEW vw_clientes_motos WITH (security_invoker = on) AS
SELECT c.documento_cli,
       c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo,
       c.telefono_cli, c.correo_cli, c.direccion_cli,
       m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot, mar.nombre_mar AS marca
FROM clientes c
INNER JOIN motos m   ON c.documento_cli = m.documento_cli_mot AND c.cod_taller = m.cod_taller
INNER JOIN marcas mar ON m.cod_marca_mot = mar.cod_mar AND m.cod_taller = mar.cod_taller;

CREATE OR REPLACE VIEW vw_motos WITH (security_invoker = on) AS
SELECT m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot,
       m.documento_cli_mot, m.cod_marca_mot
FROM motos m;

CREATE OR REPLACE VIEW vw_motos_marcas WITH (security_invoker = on) AS
SELECT m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot,
       m.documento_cli_mot, m.cod_marca_mot, mar.nombre_mar AS marca
FROM motos m INNER JOIN marcas mar ON m.cod_marca_mot = mar.cod_mar AND m.cod_taller = mar.cod_taller;

CREATE OR REPLACE VIEW vw_motos_detalle WITH (security_invoker = on) AS
SELECT m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot,
       mar.nombre_mar AS marca, c.documento_cli,
       c.nombre_cli || ' ' || c.apellido_1_cli || ' ' || COALESCE(c.apellido_2_cli, '') AS nombre_completo_cliente,
       c.telefono_cli, c.correo_cli
FROM motos m
INNER JOIN marcas mar ON m.cod_marca_mot = mar.cod_mar AND m.cod_taller = mar.cod_taller
INNER JOIN clientes c ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller;

CREATE OR REPLACE VIEW vw_marcas WITH (security_invoker = on) AS
SELECT mar.cod_mar, mar.nombre_mar FROM marcas mar;

CREATE OR REPLACE VIEW vw_marcas_resumen WITH (security_invoker = on) AS
SELECT mar.cod_mar, mar.nombre_mar, COUNT(m.placa_mot) AS total_motos
FROM marcas mar
LEFT JOIN motos m ON mar.cod_mar = m.cod_marca_mot AND mar.cod_taller = m.cod_taller
GROUP BY mar.cod_mar, mar.nombre_mar;

CREATE OR REPLACE VIEW vw_marcas_motos WITH (security_invoker = on) AS
SELECT mar.cod_mar, mar.nombre_mar,
       m.placa_mot, m.modelo_mot, m.color_mot, m.cilindraje_mot
FROM marcas mar
LEFT JOIN motos m ON mar.cod_mar = m.cod_marca_mot AND mar.cod_taller = m.cod_taller;

CREATE OR REPLACE VIEW vw_usuarios_perfiles WITH (security_invoker = on) AS
SELECT u.documento_usu,
       u.nombre_usu || ' ' || u.apellido_1_usu || ' ' || COALESCE(u.apellido_2_usu, '') AS nombre_completo,
       u.correo_usu, u.cod_tipo_usu, e.nombre_est AS estado_usuario,
       p.nombre_prf AS perfil, p.descripcion_prf AS descripcion_perfil,
       u.es_admin_usu, u.ultimo_ingreso_usu
FROM usuarios u
INNER JOIN estados e  ON u.cod_est_usu = e.cod_est
INNER JOIN perfiles p ON u.cod_taller = p.cod_taller AND u.cod_prf_usu = p.cod_prf;

CREATE OR REPLACE VIEW vw_perfiles WITH (security_invoker = on) AS
SELECT p.cod_prf, p.nombre_prf, p.descripcion_prf, p.es_admin, p.cod_est_prf,
       e.nombre_est AS nombre_est_prf
FROM perfiles p
INNER JOIN estados e ON p.cod_est_prf = e.cod_est
ORDER BY p.cod_prf;

CREATE OR REPLACE VIEW vw_perfiles_permisos_detalle WITH (security_invoker = on) AS
SELECT pf.cod_prf, pf.nombre_prf, pf.es_admin,
       pm.cod_prm, pm.nombre_prm, pm.descripcion_prm,
       e.nombre_est AS estado_permiso
FROM perfiles_permisos pp
INNER JOIN perfiles pf ON pp.cod_taller = pf.cod_taller AND pp.cod_prf_pp = pf.cod_prf
INNER JOIN permisos pm ON pp.cod_prm_pp = pm.cod_prm
INNER JOIN estados e   ON pp.cod_est_pp = e.cod_est;

CREATE OR REPLACE VIEW vw_permisos WITH (security_invoker = on) AS
SELECT p.cod_prm, p.nombre_prm, p.descripcion_prm FROM permisos p;

CREATE OR REPLACE VIEW vw_permisos_por_perfil WITH (security_invoker = on) AS
SELECT p.cod_prm, p.nombre_prm, p.descripcion_prm, pp.cod_prf_pp, pp.cod_est_pp
FROM permisos p
INNER JOIN perfiles_permisos pp ON p.cod_prm = pp.cod_prm_pp;

-- ============================================================
-- 7b. SEMBRADO DE PERFILES POR TALLER
--    Crea los 3 perfiles por defecto (Admin/Mecánico/Recepcionista) del taller
--    y les asigna permisos del catálogo global. Lo usan tanto el seed inicial
--    como el registro de talleres (onboarding). Devuelve el cod_prf del Admin.
--    Selecciona permisos por NOMBRE (no por id) para no depender del orden del seed.
-- ============================================================
CREATE OR REPLACE FUNCTION fn_seed_perfiles_taller(p_taller INTEGER)
RETURNS INTEGER AS $$
DECLARE
    v_admin INTEGER;
    v_meca  INTEGER;
    v_recep INTEGER;
BEGIN
    PERFORM set_config('app.tenant_id', p_taller::text, true);

    INSERT INTO perfiles (cod_taller, cod_prf, nombre_prf, descripcion_prf, cod_est_prf, es_admin)
    VALUES (p_taller, nextval('seq_perfiles'), 'Administrador', 'Acceso total al taller', 1, true)
    RETURNING cod_prf INTO v_admin;

    INSERT INTO perfiles (cod_taller, cod_prf, nombre_prf, descripcion_prf, cod_est_prf, es_admin)
    VALUES (p_taller, nextval('seq_perfiles'), 'Mecánico', 'Gestión de órdenes de trabajo', 1, false)
    RETURNING cod_prf INTO v_meca;

    INSERT INTO perfiles (cod_taller, cod_prf, nombre_prf, descripcion_prf, cod_est_prf, es_admin)
    VALUES (p_taller, nextval('seq_perfiles'), 'Recepcionista', 'Gestión de clientes, motos y órdenes', 1, false)
    RETURNING cod_prf INTO v_recep;

    -- Admin: SIN asignación explícita (bypass vía es_admin_usu).

    INSERT INTO perfiles_permisos (cod_taller, cod_prm_pp, cod_prf_pp, cod_est_pp)
    SELECT p_taller, cod_prm, v_meca, 1 FROM permisos
    WHERE nombre_prm IN (
        'ver:clientes','ver:marcas','ver:motos','ver:productos',
        'ver:ordenes-trabajo','crear_editar:ordenes-trabajo',
        'ver:tablero','ver:reclamos','crear_editar:reclamos'
    );

    INSERT INTO perfiles_permisos (cod_taller, cod_prm_pp, cod_prf_pp, cod_est_pp)
    SELECT p_taller, cod_prm, v_recep, 1 FROM permisos
    WHERE nombre_prm IN (
        'ver:clientes','crear_editar:clientes','ver:marcas',
        'ver:motos','crear_editar:motos','ver:productos',
        'ver:ordenes-trabajo','crear_editar:ordenes-trabajo',
        'ver:tablero','ver_todo:tablero','ver:inventario','ajustar:inventario',
        'ver:reclamos','crear_editar:reclamos',
        'ver:pagos-orden','crear_editar:pagos-orden'
    );

    RETURN v_admin;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 8. SEED
-- ============================================================

-- ---- Catálogos GLOBALES ----
INSERT INTO estados (cod_est, nombre_est) VALUES (1,'Activo'),(2,'Inactivo');

INSERT INTO ot_estados (cod_ot_est, nombre_ot_est) VALUES
(1,'Pendiente'),(2,'En Proceso'),(3,'Completada'),(4,'Entregada'),(5,'Anulada'),(6,'Garantía');

-- F1-12: catálogo de permisos por módulo (ver / crear_editar /
-- eliminar_o_anular) + acciones sensibles. Reemplaza al catálogo viejo de
-- 48 permisos, que traía 24 muertos (operations/orders/roles/vistas/users/
-- perfiles-permisos -- ningún require_permiso los consultaba) y separaba
-- crear/actualizar en 2 filas que la UI ya agrupaba en una sola columna.
INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm) VALUES
(nextval('seq_permisos'),'ver:clientes','Permite ver clientes'),
(nextval('seq_permisos'),'crear_editar:clientes','Permite crear y editar clientes'),
(nextval('seq_permisos'),'eliminar_o_anular:clientes','Permite eliminar o anular clientes'),
(nextval('seq_permisos'),'ver:marcas','Permite ver marcas'),
(nextval('seq_permisos'),'crear_editar:marcas','Permite crear y editar marcas'),
(nextval('seq_permisos'),'eliminar_o_anular:marcas','Permite eliminar o anular marcas'),
(nextval('seq_permisos'),'ver:motos','Permite ver motos'),
(nextval('seq_permisos'),'crear_editar:motos','Permite crear y editar motos'),
(nextval('seq_permisos'),'eliminar_o_anular:motos','Permite eliminar o anular motos'),
(nextval('seq_permisos'),'ver:productos','Permite ver productos'),
(nextval('seq_permisos'),'crear_editar:productos','Permite crear y editar productos'),
(nextval('seq_permisos'),'eliminar_o_anular:productos','Permite eliminar o anular productos'),
(nextval('seq_permisos'),'ver:ordenes-trabajo','Permite ver órdenes de trabajo'),
(nextval('seq_permisos'),'crear_editar:ordenes-trabajo','Permite crear y editar órdenes de trabajo'),
(nextval('seq_permisos'),'eliminar_o_anular:ordenes-trabajo','Permite eliminar o anular órdenes de trabajo'),
(nextval('seq_permisos'),'marcar_no_cobro:ordenes-trabajo','Permite marcar un ítem de una orden como "no se cobra" (cortesía)'),
(nextval('seq_permisos'),'anular:ordenes-trabajo','Permite anular una orden de trabajo completa (con motivo obligatorio)'),
(nextval('seq_permisos'),'ver:reclamos','Permite ver reclamos'),
(nextval('seq_permisos'),'crear_editar:reclamos','Permite crear y editar reclamos'),
(nextval('seq_permisos'),'eliminar_o_anular:reclamos','Permite eliminar o anular reclamos'),
(nextval('seq_permisos'),'ver:inventario','Permite ver el inventario y el kardex'),
(nextval('seq_permisos'),'crear_editar:inventario','Permite registrar entradas y tomas físicas de inventario'),
(nextval('seq_permisos'),'eliminar_o_anular:inventario','Permite anular movimientos de inventario'),
(nextval('seq_permisos'),'ajustar:inventario','Permite registrar entradas y tomas físicas que ajustan el stock'),
(nextval('seq_permisos'),'ver:tablero','Permite ver el tablero de órdenes'),
(nextval('seq_permisos'),'crear_editar:tablero','Permite mover órdenes en el tablero'),
(nextval('seq_permisos'),'eliminar_o_anular:tablero','Permite anular órdenes desde el tablero'),
(nextval('seq_permisos'),'ver_todo:tablero','Permite ver el tablero completo (todas las órdenes, no solo las propias) y filtrar por mecánico'),
(nextval('seq_permisos'),'ver:talleres','Permite ver la configuración del taller ("Mi taller")'),
(nextval('seq_permisos'),'crear_editar:talleres','Permite editar la configuración del taller'),
(nextval('seq_permisos'),'eliminar_o_anular:talleres','Reservado (el taller no se elimina desde este módulo)'),
(nextval('seq_permisos'),'ver:planes','Permite ver el plan y la suscripción del taller'),
(nextval('seq_permisos'),'crear_editar:planes','Permite cambiar el plan del taller'),
(nextval('seq_permisos'),'eliminar_o_anular:planes','Reservado (no hay acción de eliminar plan hoy)'),
(nextval('seq_permisos'),'ver:impuestos','Permite ver el catálogo de impuestos'),
(nextval('seq_permisos'),'crear_editar:impuestos','Permite crear y editar impuestos'),
(nextval('seq_permisos'),'eliminar_o_anular:impuestos','Permite eliminar impuestos'),
(nextval('seq_permisos'),'ver_costos:productos','Permite ver costos y márgenes de productos');

-- F1-07: catálogo de permisos del módulo de pagos/abonos.
INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm) VALUES
(nextval('seq_permisos'),'ver:pagos-orden','Permite ver los pagos/abonos de una orden'),
(nextval('seq_permisos'),'crear_editar:pagos-orden','Permite registrar pagos/abonos a una orden'),
(nextval('seq_permisos'),'eliminar_o_anular:pagos-orden','Permite anular un pago/abono (con motivo obligatorio)');

-- Fin de los catálogos GLOBALES (reales, necesarios en cualquier ambiente,
-- incluida producción). El seed de DEMO (taller, usuarios y datos de ejemplo)
-- vive aparte en db/seed_demo.sql -- NUNCA se carga en producción (ver el
-- comentario de ese archivo). db/init/01_load.sql y 02_load_test.sql, y
-- .github/workflows/ci.yml, cargan este archivo y LUEGO seed_demo.sql.


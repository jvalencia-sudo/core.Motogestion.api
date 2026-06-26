-- ============================================================
-- MotoGestion - Esquema MULTI-TENANT (v2) - REFACTOR
-- Copia de full_schema.sql adaptada a multi-taller (SaaS).
-- Estrategia: esquema compartido + columna cod_taller + RLS de Postgres.
--   * Tablas POR TALLER: cod_taller con DEFAULT current_setting('app.tenant_id').
--     PK compuestas con cod_taller en las llaves naturales (documento/placa/consecutivo).
--     RLS + FORCE ROW LEVEL SECURITY para aislar cada taller.
--   * Tablas GLOBALES (catálogos y permisos): se comparten entre todos los talleres.
--   * El backend hará SET app.tenant_id=<id> por request; el DEFAULT y el RLS hacen el resto.
-- El original full_schema.sql se conserva intacto como respaldo (single-tenant).
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
    CONSTRAINT pk_talleres PRIMARY KEY (cod_taller)
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
CREATE SEQUENCE seq_roles                START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;

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

CREATE TABLE roles (
    cod_rol         INTEGER NOT NULL DEFAULT nextval('seq_roles'),
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
    cod_prm         INTEGER NOT NULL DEFAULT nextval('seq_permisos'),
    nombre_prm      VARCHAR(250),
    descripcion_prm VARCHAR(500),
    ruta_vis_prm    VARCHAR(500),
    CONSTRAINT pk_permisos PRIMARY KEY (cod_prm),
    CONSTRAINT fk_permisos_vista FOREIGN KEY (ruta_vis_prm) REFERENCES vistas (ruta_vis)
);

-- ============================================================
-- 2b. PERFILES Y SUS PERMISOS — POR TALLER (cod_taller + RLS)
--    Cada taller personaliza sus propios perfiles sin afectar a otros.
--    roles/vistas/permisos siguen siendo el catálogo GLOBAL compartido.
-- ============================================================
CREATE TABLE perfiles (
    cod_taller      INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    cod_prf         INTEGER NOT NULL DEFAULT nextval('seq_perfiles'),
    nombre_prf      VARCHAR(250),
    descripcion_prf VARCHAR(500),
    cod_est_prf     INTEGER,
    cod_rol_prf     INTEGER NOT NULL,
    CONSTRAINT pk_perfiles PRIMARY KEY (cod_taller, cod_prf, cod_rol_prf),
    CONSTRAINT fk_perfiles_taller FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_perfiles_estado FOREIGN KEY (cod_est_prf) REFERENCES estados (cod_est),
    CONSTRAINT fk_perfiles_rol    FOREIGN KEY (cod_rol_prf) REFERENCES roles (cod_rol)
);
-- cod_prf es único globalmente (seq) pero el PK incluye cod_taller para el aislamiento.

CREATE TABLE perfiles_permisos (
    cod_taller     INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    cod_prm_pp     INTEGER NOT NULL,
    cod_prf_pp     INTEGER NOT NULL,
    cod_rol_prf_pp INTEGER NOT NULL,
    cod_est_pp     INTEGER,
    CONSTRAINT pk_perfiles_permisos PRIMARY KEY (cod_taller, cod_prm_pp, cod_prf_pp, cod_rol_prf_pp),
    CONSTRAINT fk_pp_taller  FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_pp_permiso FOREIGN KEY (cod_prm_pp) REFERENCES permisos (cod_prm),
    CONSTRAINT fk_pp_perfil  FOREIGN KEY (cod_taller, cod_prf_pp, cod_rol_prf_pp) REFERENCES perfiles (cod_taller, cod_prf, cod_rol_prf),
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
    cod_rol_prf_usu INTEGER,
    CONSTRAINT pk_usuarios PRIMARY KEY (cod_taller, documento_usu),
    CONSTRAINT fk_usuarios_taller FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_usuarios_estado FOREIGN KEY (cod_est_usu) REFERENCES estados (cod_est),
    CONSTRAINT fk_usuarios_perfil FOREIGN KEY (cod_taller, cod_prf_usu, cod_rol_prf_usu) REFERENCES perfiles (cod_taller, cod_prf, cod_rol_prf)
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
    stock_pro       INTEGER,
    stock_pro_min   INTEGER,
    cod_est_pro     INTEGER,
    precio_pro      INTEGER,
    CONSTRAINT pk_productos PRIMARY KEY (cod_taller, cod_pro),
    CONSTRAINT fk_productos_taller FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_productos_estado FOREIGN KEY (cod_est_pro) REFERENCES estados (cod_est)
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
    kilometreje_salida_ot  DATE,
    observacion_cli_ot     VARCHAR(500),
    observacion_ot         VARCHAR(500),
    placa_mot_ot           VARCHAR(6),
    documento_usu_rp_ot    VARCHAR(11),
    documento_usu_mc_ot    VARCHAR(11),
    cod_ot_est_ot          INTEGER,
    fecha_fin_garantia_ot  DATE,
    CONSTRAINT pk_ordenes_trabajo PRIMARY KEY (cod_taller, consecutivo_ot),
    CONSTRAINT fk_ot_taller   FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_ot_moto     FOREIGN KEY (cod_taller, placa_mot_ot)        REFERENCES motos (cod_taller, placa_mot),
    CONSTRAINT fk_ot_recep    FOREIGN KEY (cod_taller, documento_usu_rp_ot) REFERENCES usuarios (cod_taller, documento_usu),
    CONSTRAINT fk_ot_mecanico FOREIGN KEY (cod_taller, documento_usu_mc_ot) REFERENCES usuarios (cod_taller, documento_usu),
    CONSTRAINT fk_ot_estado   FOREIGN KEY (cod_ot_est_ot)                   REFERENCES ot_estados (cod_ot_est)
);

CREATE TABLE detalle_orden_trabajo (
    cod_taller              INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    id_deto                 BIGINT  GENERATED ALWAYS AS IDENTITY,
    consecutivo_ot_deto     INTEGER NOT NULL,
    cod_pro_deto            INTEGER NOT NULL,
    fecha_confirmacion_deto DATE,
    valor_unitario_deto     INTEGER,
    cantidad_deto           INTEGER,
    documento_usu_deto      VARCHAR(11),
    CONSTRAINT pk_detalle_ot PRIMARY KEY (cod_taller, id_deto),
    CONSTRAINT fk_deto_taller   FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_deto_orden    FOREIGN KEY (cod_taller, consecutivo_ot_deto) REFERENCES ordenes_trabajo (cod_taller, consecutivo_ot),
    CONSTRAINT fk_deto_producto FOREIGN KEY (cod_taller, cod_pro_deto)        REFERENCES productos (cod_taller, cod_pro),
    CONSTRAINT fk_deto_usuario  FOREIGN KEY (cod_taller, documento_usu_deto)  REFERENCES usuarios (cod_taller, documento_usu)
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

-- ============================================================
-- 4. TRIGGERS funcionales (ajustados a multi-taller)
-- ============================================================

-- Descontar stock al confirmar un detalle (acotado al taller del detalle)
CREATE OR REPLACE FUNCTION fn_actualizar_stock()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE productos
       SET stock_pro = stock_pro - NEW.cantidad_deto
     WHERE cod_pro = NEW.cod_pro_deto
       AND cod_taller = NEW.cod_taller;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_actualizar_stock
AFTER INSERT ON detalle_orden_trabajo
FOR EACH ROW EXECUTE FUNCTION fn_actualizar_stock();

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

-- Fecha fin de garantía (1 mes desde entrega si estado = 4)
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
    v_taller INTEGER;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_taller := OLD.cod_taller;
        INSERT INTO audit_log (cod_taller, tabla, evento, valor_anterior)
        VALUES (v_taller, TG_TABLE_NAME, 'D', to_jsonb(OLD));
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        v_taller := NEW.cod_taller;
        INSERT INTO audit_log (cod_taller, tabla, evento, valor_anterior, valor_nuevo)
        VALUES (v_taller, TG_TABLE_NAME, 'U', to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    ELSE
        v_taller := NEW.cod_taller;
        INSERT INTO audit_log (cod_taller, tabla, evento, valor_nuevo)
        VALUES (v_taller, TG_TABLE_NAME, 'I', to_jsonb(NEW));
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
    'productos_impuestos','ordenes_trabajo','detalle_orden_trabajo','reclamos'
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
    ot.kilometraje_ingreso_ot, ot.observacion_cli_ot, ot.observacion_ot,
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
    ote.nombre_ot_est AS estado_ot, ot.cod_ot_est_ot
FROM ordenes_trabajo ot
INNER JOIN motos m       ON ot.placa_mot_ot = m.placa_mot AND ot.cod_taller = m.cod_taller
INNER JOIN clientes c    ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller
INNER JOIN marcas mar    ON m.cod_marca_mot = mar.cod_mar AND m.cod_taller = mar.cod_taller
INNER JOIN usuarios urp  ON ot.documento_usu_rp_ot = urp.documento_usu AND ot.cod_taller = urp.cod_taller
INNER JOIN usuarios umc  ON ot.documento_usu_mc_ot = umc.documento_usu AND ot.cod_taller = umc.cod_taller
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est;

CREATE OR REPLACE VIEW vw_detalle_ot_productos WITH (security_invoker = on) AS
SELECT
    dot.consecutivo_ot_deto, dot.cod_pro_deto,
    p.nombre_pro, p.descripcion_pro, dot.cantidad_deto, dot.valor_unitario_deto,
    (ABS(dot.cantidad_deto) * dot.valor_unitario_deto) AS subtotal,
    dot.fecha_confirmacion_deto,
    u.nombre_usu || ' ' || u.apellido_1_usu AS usuario_confirmacion,
    e.nombre_est AS estado_producto
FROM detalle_orden_trabajo dot
INNER JOIN productos p ON dot.cod_pro_deto = p.cod_pro AND dot.cod_taller = p.cod_taller
INNER JOIN usuarios u  ON dot.documento_usu_deto = u.documento_usu AND dot.cod_taller = u.cod_taller
INNER JOIN estados e   ON p.cod_est_pro = e.cod_est;

CREATE OR REPLACE VIEW vw_resumen_financiero_ot WITH (security_invoker = on) AS
SELECT
    ot.consecutivo_ot, ot.fecha_elaboracion_ot,
    c.nombre_cli || ' ' || c.apellido_1_cli AS cliente, m.placa_mot,
    COUNT(CASE WHEN dot.cantidad_deto > 0 THEN dot.cod_pro_deto END) AS total_items,
    SUM(CASE WHEN dot.cantidad_deto > 0 THEN dot.cantidad_deto * dot.valor_unitario_deto ELSE 0 END) AS subtotal_productos,
    0 AS total_impuestos,
    SUM(CASE WHEN dot.cantidad_deto > 0 THEN dot.cantidad_deto * dot.valor_unitario_deto ELSE 0 END) AS total_ot
FROM ordenes_trabajo ot
INNER JOIN detalle_orden_trabajo dot ON ot.consecutivo_ot = dot.consecutivo_ot_deto AND ot.cod_taller = dot.cod_taller
INNER JOIN motos m    ON ot.placa_mot_ot = m.placa_mot AND ot.cod_taller = m.cod_taller
INNER JOIN clientes c ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller
GROUP BY ot.consecutivo_ot, ot.fecha_elaboracion_ot, c.nombre_cli, c.apellido_1_cli, m.placa_mot;

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
INNER JOIN usuarios umc   ON ot.documento_usu_mc_ot = umc.documento_usu AND ot.cod_taller = umc.cod_taller
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
INNER JOIN usuarios umc  ON ot.documento_usu_mc_ot = umc.documento_usu AND ot.cod_taller = umc.cod_taller
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
       p.stock_pro, p.stock_pro_min, p.cod_est_pro, e.nombre_est AS estado_producto
FROM productos p INNER JOIN estados e ON p.cod_est_pro = e.cod_est;

CREATE OR REPLACE VIEW vw_productos_activos WITH (security_invoker = on) AS
SELECT p.cod_pro, p.nombre_pro, p.descripcion_pro, p.precio_pro,
       p.stock_pro, p.stock_pro_min, p.cod_est_pro, e.nombre_est AS estado_producto
FROM productos p INNER JOIN estados e ON p.cod_est_pro = e.cod_est
WHERE p.cod_est_pro = 1;

CREATE OR REPLACE VIEW vw_productos_impuestos WITH (security_invoker = on) AS
SELECT pi.cod_pro_imp, pi.cod_imp_pro_imp, pi.cod_pro_pro_imp, pi.porcentaje_pro_imp,
       i.cod_imp, i.nombre_imp, i.porcentaje_imp
FROM productos_impuestos pi
INNER JOIN impuestos i ON pi.cod_imp_pro_imp = i.cod_imp AND pi.cod_taller = i.cod_taller;

CREATE OR REPLACE VIEW vw_productos_con_impuestos WITH (security_invoker = on) AS
SELECT p.cod_pro, p.nombre_pro, p.descripcion_pro, p.precio_pro,
       p.stock_pro, p.stock_pro_min, e.nombre_est AS estado_producto,
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
       r.nombre_rol AS rol, r.descripcion_rol AS descripcion_rol
FROM usuarios u
INNER JOIN estados e  ON u.cod_est_usu = e.cod_est
INNER JOIN perfiles p ON u.cod_taller = p.cod_taller AND u.cod_prf_usu = p.cod_prf AND u.cod_rol_prf_usu = p.cod_rol_prf
INNER JOIN roles r    ON p.cod_rol_prf = r.cod_rol;

CREATE OR REPLACE VIEW vw_perfiles WITH (security_invoker = on) AS
SELECT p.cod_prf, p.nombre_prf, p.descripcion_prf,
       p.cod_rol_prf, p.cod_est_prf,
       e.nombre_est AS nombre_est_prf, r.nombre_rol AS nombre_rol_prf
FROM perfiles p
INNER JOIN estados e ON p.cod_est_prf = e.cod_est
INNER JOIN roles r   ON p.cod_rol_prf = r.cod_rol
ORDER BY p.cod_prf;

CREATE OR REPLACE VIEW vw_perfiles_permisos_detalle WITH (security_invoker = on) AS
SELECT pf.cod_prf, pf.nombre_prf, r.nombre_rol,
       pm.cod_prm, pm.nombre_prm, pm.descripcion_prm,
       v.nombre_vis, v.ruta_vis, e.nombre_est AS estado_permiso
FROM perfiles_permisos pp
INNER JOIN perfiles pf ON pp.cod_taller = pf.cod_taller AND pp.cod_prf_pp = pf.cod_prf AND pp.cod_rol_prf_pp = pf.cod_rol_prf
INNER JOIN roles r     ON pf.cod_rol_prf = r.cod_rol
INNER JOIN permisos pm ON pp.cod_prm_pp = pm.cod_prm
INNER JOIN vistas v    ON pm.ruta_vis_prm = v.ruta_vis
INNER JOIN estados e   ON pp.cod_est_pp = e.cod_est;

CREATE OR REPLACE VIEW vw_permisos WITH (security_invoker = on) AS
SELECT p.cod_prm, p.nombre_prm, p.descripcion_prm, p.ruta_vis_prm,
       NULL::INTEGER AS cod_rol_prm
FROM permisos p;

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
    -- Asegura el contexto de tenant para que el RLS permita los INSERT.
    PERFORM set_config('app.tenant_id', p_taller::text, true);

    INSERT INTO perfiles (cod_taller, cod_prf, nombre_prf, descripcion_prf, cod_est_prf, cod_rol_prf)
    VALUES (p_taller, nextval('seq_perfiles'), 'Administrador', 'Acceso total al taller', 1, 1)
    RETURNING cod_prf INTO v_admin;

    INSERT INTO perfiles (cod_taller, cod_prf, nombre_prf, descripcion_prf, cod_est_prf, cod_rol_prf)
    VALUES (p_taller, nextval('seq_perfiles'), 'Mecánico', 'Gestión de órdenes de trabajo', 1, 2)
    RETURNING cod_prf INTO v_meca;

    INSERT INTO perfiles (cod_taller, cod_prf, nombre_prf, descripcion_prf, cod_est_prf, cod_rol_prf)
    VALUES (p_taller, nextval('seq_perfiles'), 'Recepcionista', 'Gestión de clientes, motos y órdenes', 1, 3)
    RETURNING cod_prf INTO v_recep;

    -- Admin: TODOS los permisos del catálogo
    INSERT INTO perfiles_permisos (cod_taller, cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp)
    SELECT p_taller, cod_prm, v_admin, 1, 1 FROM permisos;

    -- Mecánico
    INSERT INTO perfiles_permisos (cod_taller, cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp)
    SELECT p_taller, cod_prm, v_meca, 2, 1 FROM permisos
    WHERE nombre_prm IN (
        'leer:clientes','leer:marcas','leer:motos','leer:productos',
        'leer:ordenes-trabajo','crear:ordenes-trabajo','actualizar:ordenes-trabajo',
        'leer:reclamos','crear:reclamos','actualizar:reclamos'
    );

    -- Recepcionista
    INSERT INTO perfiles_permisos (cod_taller, cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp)
    SELECT p_taller, cod_prm, v_recep, 3, 1 FROM permisos
    WHERE nombre_prm IN (
        'leer:clientes','crear:clientes','actualizar:clientes','leer:marcas',
        'leer:motos','crear:motos','actualizar:motos','leer:productos',
        'leer:ordenes-trabajo','crear:ordenes-trabajo','actualizar:ordenes-trabajo',
        'leer:reclamos','crear:reclamos','actualizar:reclamos'
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
(1,'Pendiente'),(2,'En Proceso'),(3,'Completada'),(4,'Entregada'),(5,'Cancelada'),(6,'Garantía');

INSERT INTO roles (cod_rol, nombre_rol, descripcion_rol) VALUES
(nextval('seq_roles'),'Administrador','Acceso total al sistema'),
(nextval('seq_roles'),'Mecánico','Gestión de órdenes de trabajo'),
(nextval('seq_roles'),'Recepcionista','Gestión de clientes, motos y órdenes');

INSERT INTO vistas (ruta_vis, nombre_vis) VALUES
('/admin','Administración'),('/ordenes','Órdenes de Trabajo'),('/productos','Inventario de Productos'),
('/marcas','Marcas'),('/clientes','Clientes'),('/motos','Motos'),('/reclamos','Reclamos');

-- Permisos (48) en el mismo orden que la versión single-tenant
INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm) VALUES
(nextval('seq_permisos'),'leer:clientes','Permite ver clientes','/clientes'),
(nextval('seq_permisos'),'crear:clientes','Permite crear clientes','/clientes'),
(nextval('seq_permisos'),'actualizar:clientes','Permite actualizar clientes','/clientes'),
(nextval('seq_permisos'),'eliminar:clientes','Permite eliminar - desactivar clientes','/clientes'),
(nextval('seq_permisos'),'leer:marcas','Permite ver marcas','/marcas'),
(nextval('seq_permisos'),'crear:marcas','Permite crear marcas','/marcas'),
(nextval('seq_permisos'),'actualizar:marcas','Permite actualizar marcas','/marcas'),
(nextval('seq_permisos'),'eliminar:marcas','Permite eliminar - desactivar marcas','/marcas'),
(nextval('seq_permisos'),'leer:motos','Permite ver motos','/motos'),
(nextval('seq_permisos'),'crear:motos','Permite crear motos','/motos'),
(nextval('seq_permisos'),'actualizar:motos','Permite actualizar motos','/motos'),
(nextval('seq_permisos'),'eliminar:motos','Permite eliminar - desactivar motos','/motos'),
(nextval('seq_permisos'),'leer:operations','Permite ver operaciones','/admin'),
(nextval('seq_permisos'),'crear:operations','Permite crear operaciones','/admin'),
(nextval('seq_permisos'),'actualizar:operations','Permite actualizar operaciones','/admin'),
(nextval('seq_permisos'),'eliminar:operations','Permite eliminar - desactivar operaciones','/admin'),
(nextval('seq_permisos'),'leer:ordenes-trabajo','Permite ver órdenes de trabajo','/ordenes'),
(nextval('seq_permisos'),'crear:ordenes-trabajo','Permite crear órdenes de trabajo','/ordenes'),
(nextval('seq_permisos'),'actualizar:ordenes-trabajo','Permite actualizar órdenes de trabajo','/ordenes'),
(nextval('seq_permisos'),'eliminar:ordenes-trabajo','Permite eliminar - desactivar órdenes de trabajo','/ordenes'),
(nextval('seq_permisos'),'leer:orders','Permite ver pedidos','/productos'),
(nextval('seq_permisos'),'crear:orders','Permite crear pedidos','/productos'),
(nextval('seq_permisos'),'actualizar:orders','Permite actualizar pedidos','/productos'),
(nextval('seq_permisos'),'eliminar:orders','Permite eliminar - desactivar pedidos','/productos'),
(nextval('seq_permisos'),'leer:perfiles-permisos','Permite ver perfiles de permisos','/admin'),
(nextval('seq_permisos'),'crear:perfiles-permisos','Permite crear perfiles de permisos','/admin'),
(nextval('seq_permisos'),'actualizar:perfiles-permisos','Permite actualizar perfiles de permisos','/admin'),
(nextval('seq_permisos'),'eliminar:perfiles-permisos','Permite eliminar - desactivar perfiles de permisos','/admin'),
(nextval('seq_permisos'),'leer:productos','Permite ver productos','/productos'),
(nextval('seq_permisos'),'crear:productos','Permite crear productos','/productos'),
(nextval('seq_permisos'),'actualizar:productos','Permite actualizar productos','/productos'),
(nextval('seq_permisos'),'eliminar:productos','Permite eliminar - desactivar productos','/productos'),
(nextval('seq_permisos'),'leer:roles','Permite ver roles','/admin'),
(nextval('seq_permisos'),'crear:roles','Permite crear roles','/admin'),
(nextval('seq_permisos'),'actualizar:roles','Permite actualizar roles','/admin'),
(nextval('seq_permisos'),'eliminar:roles','Permite eliminar - desactivar roles','/admin'),
(nextval('seq_permisos'),'leer:users','Permite ver usuarios','/admin'),
(nextval('seq_permisos'),'crear:users','Permite crear usuarios','/admin'),
(nextval('seq_permisos'),'actualizar:users','Permite actualizar usuarios','/admin'),
(nextval('seq_permisos'),'eliminar:users','Permite eliminar - desactivar usuarios','/admin'),
(nextval('seq_permisos'),'leer:vistas','Permite ver vistas','/admin'),
(nextval('seq_permisos'),'crear:vistas','Permite crear vistas','/admin'),
(nextval('seq_permisos'),'actualizar:vistas','Permite actualizar vistas','/admin'),
(nextval('seq_permisos'),'eliminar:vistas','Permite eliminar - desactivar vistas','/admin'),
(nextval('seq_permisos'),'leer:reclamos','Permite ver reclamos','/reclamos'),
(nextval('seq_permisos'),'crear:reclamos','Permite crear reclamos','/reclamos'),
(nextval('seq_permisos'),'actualizar:reclamos','Permite actualizar reclamos','/reclamos'),
(nextval('seq_permisos'),'eliminar:reclamos','Permite eliminar - desactivar reclamos','/reclamos');

-- ---- TALLER #1 (migración de los datos actuales) ----
INSERT INTO talleres (cod_taller, nombre_tal, nit_tal, correo_tal, estado_tal)
VALUES (nextval('seq_talleres'), 'MotoGestión Demo', '900000000-1', 'demo@motogestion.com', 'activo');

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

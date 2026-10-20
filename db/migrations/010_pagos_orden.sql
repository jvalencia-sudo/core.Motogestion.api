-- F1-07: pagos y abonos por orden. OJO: ya existe una tabla `pagos` (billing
-- de la plataforma vía Wompi, sin RLS a propósito -- ver EXCEPCIONES_RLS).
-- Esta es distinta a propósito: `pagos_orden` es dinero que el CLIENTE del
-- taller paga por una orden, con cod_taller y RLS como el resto de tablas
-- del taller.

CREATE SEQUENCE seq_pagos_orden START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;

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
    -- Igual que ordenes_trabajo con la anulación (F1-05): si está anulado,
    -- motivo y fecha de anulación deben venir; si no, deben estar vacíos.
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

-- Los pagos no se editan ni se borran (solo INSERT y el UPDATE de anular) --
-- igual que ordenes_trabajo/detalle_orden_trabajo, se audita quién hizo qué.
CREATE TRIGGER tg_audit_pagos_orden AFTER INSERT OR UPDATE OR DELETE ON pagos_orden
FOR EACH ROW EXECUTE FUNCTION fn_audit();

-- vw_resumen_financiero_ot: agrega total_pagado y saldo_ot AL FINAL del
-- SELECT (Postgres no permite reordenar columnas de una vista existente con
-- CREATE OR REPLACE, solo añadir al final -- mismo motivo que en 006/008/009).
-- Excluye pagos anulados; saldo_ot puede ser negativo si se sobrepagó (no se
-- impide un pago mayor al saldo -- no es un criterio de este ticket).
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

-- vw_pagos_orden: lista de abonos de una orden, con el nombre de quien
-- registró/anuló (para mostrar en el front sin otra consulta).
CREATE OR REPLACE VIEW vw_pagos_orden WITH (security_invoker = on) AS
SELECT
    po.cod_pago_orden, po.consecutivo_ot_pago, po.valor_pago, po.metodo_pago,
    po.fecha_pago, po.documento_usu_pago,
    u.nombre_usu || ' ' || u.apellido_1_usu AS usuario_pago,
    po.referencia_pago, po.anulado_pago,
    po.motivo_anulacion_pago, po.fecha_anulacion_pago, po.documento_usu_anulacion_pago
FROM pagos_orden po
INNER JOIN usuarios u ON po.cod_taller = u.cod_taller AND po.documento_usu_pago = u.documento_usu;

-- F1-07: catálogo de permisos del módulo nuevo.
INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm) VALUES
(nextval('seq_permisos'), 'ver:pagos-orden', 'Permite ver los pagos/abonos de una orden'),
(nextval('seq_permisos'), 'crear_editar:pagos-orden', 'Permite registrar pagos/abonos a una orden'),
(nextval('seq_permisos'), 'eliminar_o_anular:pagos-orden', 'Permite anular un pago/abono (con motivo obligatorio)');

-- Recepcionista recibe el módulo de pagos por defecto (es quien cobra en el
-- mostrador, igual que ya recibe crear_editar:clientes/motos). Mecánico no.
-- El Admin siempre tiene bypass -- no necesita fila en perfiles_permisos.
-- Talleres YA sembrados: el Admin puede asignar esto a su Recepcionista
-- desde la matriz de permisos, ya que no se backfillea acá (mismo criterio
-- que el resto del catálogo F1-12: un permiso nuevo no se auto-asigna a
-- perfiles no-admin ya existentes).
DO $$
DECLARE
    r RECORD;
    v_recep INTEGER;
BEGIN
    FOR r IN SELECT cod_taller FROM talleres LOOP
        PERFORM set_config('app.tenant_id', r.cod_taller::text, true);

        SELECT cod_prf INTO v_recep FROM perfiles
        WHERE cod_taller = r.cod_taller AND nombre_prf = 'Recepcionista';

        IF v_recep IS NOT NULL THEN
            INSERT INTO perfiles_permisos (cod_taller, cod_prm_pp, cod_prf_pp, cod_est_pp)
            SELECT r.cod_taller, cod_prm, v_recep, 1 FROM permisos
            WHERE nombre_prm IN ('ver:pagos-orden', 'crear_editar:pagos-orden');
        END IF;
    END LOOP;
END $$;

-- fn_seed_perfiles_taller: para talleres NUEVOS a partir de ahora, la
-- Recepcionista sembrada ya nace con el módulo de pagos.
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

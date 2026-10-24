-- F2-02/F2-03: diagnostico del mecanico (publico), horario del taller, y
-- aprobacion de cotizacion OPCIONAL por taller (switch, default apagado --
-- ningun taller pierde su flujo actual sin pedirlo).
--
-- diagnostico_ot es un campo NUEVO y SEPARADO de observacion_ot a proposito:
-- observacion_ot es interno/admin hoy (lo escribe el taller sin pensar que
-- el cliente final lo vaya a leer) -- reusarlo filtraria retroactivamente
-- texto no pensado para el cliente en ordenes que ya existen.
--
-- La aprobacion NO se implementa como un estado nuevo de cod_ot_est_ot (ese
-- codigo es libre, sin tabla de transiciones, y tocarlo arrastraria
-- tablero/kanban/reportes/PDF que ya asumen 1-6). Es una capa ortogonal: el
-- publico muestra "Esperando tu aprobacion" solo cuando el switch del taller
-- esta encendido Y la orden esta en estado 2 (En Proceso) Y hay cotizacion Y
-- no existe una fila vigente=true para esa orden. Si el taller apaga el
-- switch, el gate desaparece de inmediato para cualquier orden que lo tuviera
-- pendiente -- es el comportamiento esperado, nada en el backend depende de
-- "vigente" para poder seguir trabajando la orden.

ALTER TABLE ordenes_trabajo
    ADD COLUMN diagnostico_ot TEXT;

ALTER TABLE talleres
    ADD COLUMN horario_atencion_tal            TEXT,
    ADD COLUMN exige_aprobacion_cotizacion_tal  BOOLEAN NOT NULL DEFAULT false;

CREATE TABLE orden_aprobacion_cotizacion (
    cod_taller      INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    id_aprobacion   BIGINT  GENERATED ALWAYS AS IDENTITY,
    consecutivo_ot  INTEGER NOT NULL,
    aprobado_en     TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- TEXT, no INET: la IP real llega vía X-Forwarded-For (ver
    -- infrastructure/utils/client_ip.py) y es dato de auditoría, no se
    -- consulta por rango -- no vale la pena que un valor inesperado (proxy
    -- mal configurado, cliente de test) tumbe la aprobación con un 500.
    ip              TEXT,
    user_agent      TEXT,
    items_snapshot  JSONB NOT NULL,
    total_snapshot  NUMERIC(14, 2) NOT NULL,
    vigente         BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT pk_orden_aprobacion_cotizacion PRIMARY KEY (cod_taller, id_aprobacion),
    CONSTRAINT fk_oac_taller FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_oac_orden  FOREIGN KEY (cod_taller, consecutivo_ot) REFERENCES ordenes_trabajo (cod_taller, consecutivo_ot)
);
CREATE INDEX ix_oac_orden ON orden_aprobacion_cotizacion (cod_taller, consecutivo_ot);
-- Garantiza "una sola vigente por orden" a nivel de base de datos -- no solo
-- con el UPDATE previo en la misma transaccion (cierra la ventana de
-- doble-click / dos pestañas del cliente aprobando al mismo tiempo).
CREATE UNIQUE INDEX ux_oac_vigente ON orden_aprobacion_cotizacion (cod_taller, consecutivo_ot) WHERE vigente;

ALTER TABLE orden_aprobacion_cotizacion ENABLE ROW LEVEL SECURITY;
ALTER TABLE orden_aprobacion_cotizacion FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON orden_aprobacion_cotizacion
    USING (cod_taller = current_setting('app.tenant_id', true)::integer)
    WITH CHECK (cod_taller = current_setting('app.tenant_id', true)::integer);

-- diagnostico_ot al final de la vista (igual regla que token_publico en
-- F2-01: Postgres no permite reordenar columnas de una vista existente).
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
        AND NOT dot.retirado
    ) AS trabajos,
    ot.kilometraje_salida_ot,
    ot.motivo_anulacion_ot, ot.fecha_anulacion_ot, ot.documento_usu_anulacion_ot,
    c.tipo_documento_cli, m.ciudad_placa_mot,
    ot.token_publico::text AS token_publico,
    ot.diagnostico_ot
FROM ordenes_trabajo ot
INNER JOIN motos m       ON ot.placa_mot_ot = m.placa_mot AND ot.cod_taller = m.cod_taller
INNER JOIN clientes c    ON m.documento_cli_mot = c.documento_cli AND m.cod_taller = c.cod_taller
INNER JOIN marcas mar    ON m.cod_marca_mot = mar.cod_mar AND m.cod_taller = mar.cod_taller
INNER JOIN usuarios urp  ON ot.documento_usu_rp_ot = urp.documento_usu AND ot.cod_taller = urp.cod_taller
LEFT JOIN usuarios umc   ON ot.documento_usu_mc_ot = umc.documento_usu AND ot.cod_taller = umc.cod_taller
INNER JOIN ot_estados ote ON ot.cod_ot_est_ot = ote.cod_ot_est;

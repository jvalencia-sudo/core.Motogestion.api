-- F2-02: historial de estados de una orden con hora real, para la linea de
-- tiempo del link publico (hoy solo infiere "en que paso esta" sin saber
-- CUANDO llego a el, salvo ingreso/entrega que ya existen como columnas).
--
-- Un solo trigger (AFTER INSERT OR UPDATE OF cod_ot_est_ot) en vez de llamadas
-- repartidas en cada servicio (cambiar_estado, actualizar_orden, entregar_orden,
-- anular_orden): asi ningun camino que cambie el estado puede "olvidarse" de
-- registrar el hito. Ordenes de ANTES de esta migracion no tendran filas para
-- estados ya pasados -- el publico cae al comportamiento actual (sin hora,
-- solo "Ahora" en el paso vigente) para esas, ver estado.ts en el frontend.

CREATE TABLE orden_estado_historial (
    cod_taller      INTEGER NOT NULL DEFAULT current_setting('app.tenant_id')::integer,
    id_hist         BIGINT  GENERATED ALWAYS AS IDENTITY,
    consecutivo_ot  INTEGER NOT NULL,
    cod_ot_est_ot   INTEGER NOT NULL,
    ocurrido_en     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_orden_estado_historial PRIMARY KEY (cod_taller, id_hist),
    CONSTRAINT fk_oeh_taller FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT fk_oeh_orden  FOREIGN KEY (cod_taller, consecutivo_ot) REFERENCES ordenes_trabajo (cod_taller, consecutivo_ot),
    CONSTRAINT fk_oeh_estado FOREIGN KEY (cod_ot_est_ot) REFERENCES ot_estados (cod_ot_est)
);
CREATE INDEX ix_oeh_orden ON orden_estado_historial (cod_taller, consecutivo_ot);

ALTER TABLE orden_estado_historial ENABLE ROW LEVEL SECURITY;
ALTER TABLE orden_estado_historial FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON orden_estado_historial
    USING (cod_taller = current_setting('app.tenant_id', true)::integer)
    WITH CHECK (cod_taller = current_setting('app.tenant_id', true)::integer);

-- No se necesita el bypass por token_publico (como en ordenes_trabajo): para
-- cuando el endpoint publico llega hasta aqui ya hizo set_tenant(cod_taller)
-- con el tenant real resuelto del token, asi que la policy generica basta.

CREATE OR REPLACE FUNCTION fn_registrar_historial_estado()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.cod_ot_est_ot IS NULL THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'UPDATE' AND NEW.cod_ot_est_ot = OLD.cod_ot_est_ot THEN
        RETURN NEW;
    END IF;
    INSERT INTO orden_estado_historial (cod_taller, consecutivo_ot, cod_ot_est_ot)
    VALUES (NEW.cod_taller, NEW.consecutivo_ot, NEW.cod_ot_est_ot);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_historial_estado_ot
AFTER INSERT OR UPDATE OF cod_ot_est_ot ON ordenes_trabajo
FOR EACH ROW EXECUTE FUNCTION fn_registrar_historial_estado();

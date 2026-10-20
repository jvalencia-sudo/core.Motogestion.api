-- F1-09: personalizacion visual de la orden (logo, color, condiciones, pie,
-- interruptores). `talleres` no tiene RLS -- sin loop de set_config/tenant,
-- igual que 001_mi_taller_campos.sql.

ALTER TABLE talleres
    ADD COLUMN nombre_comercial_tal          VARCHAR(150),
    ADD COLUMN whatsapp_tal                  VARCHAR(20),
    ADD COLUMN color_principal_tal           VARCHAR(7) NOT NULL DEFAULT '#00B06E',
    ADD COLUMN texto_condiciones_tal         VARCHAR(1500),
    ADD COLUMN texto_pie_tal                 VARCHAR(200),
    ADD COLUMN mostrar_precios_unitarios_tal BOOLEAN NOT NULL DEFAULT true,
    ADD COLUMN mostrar_mecanico_tal          BOOLEAN NOT NULL DEFAULT true,
    ADD COLUMN mostrar_firma_cliente_tal     BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE talleres
    ADD CONSTRAINT chk_taller_color_principal CHECK (color_principal_tal ~ '^#[0-9A-Fa-f]{6}$');

-- El logo va en una tabla aparte (no en `talleres`) para que el SELECT * que
-- ya usan BaseRepository.get_all/get_by_id (listado de super-admin, config
-- del propio taller) no arrastre un BYTEA en cada fila/llamada -- solo los
-- 2 métodos nuevos que lo necesitan (servir el logo, generar el PDF) lo
-- consultan. Sin RLS: mismo criterio que `talleres` (tabla global de
-- metadatos, el tenant se valida en la capa de servicio, no en Postgres).
CREATE TABLE taller_logo (
    cod_taller     INTEGER      NOT NULL,
    logo           BYTEA        NOT NULL,
    content_type   VARCHAR(20)  NOT NULL,
    actualizado_en TIMESTAMP    NOT NULL DEFAULT now(),
    CONSTRAINT pk_taller_logo PRIMARY KEY (cod_taller),
    CONSTRAINT fk_taller_logo_taller FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller)
);

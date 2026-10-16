-- ============================================================
-- Migración: PAGOS / suscripciones (Fase 1, item 3 — Wompi).
-- `pagos` es billing de plataforma (SIN RLS): el webhook de Wompi llega sin
-- sesión y debe poder resolver el pago por su referencia. Cada fila guarda el
-- cod_taller para consultas por taller.
-- Idempotente. Correr como el rol DUEÑO de las tablas (mt_app local).
-- ============================================================

BEGIN;

CREATE SEQUENCE IF NOT EXISTS seq_pagos START WITH 1 INCREMENT BY 1 CACHE 1 NO CYCLE;

CREATE TABLE IF NOT EXISTS pagos (
    cod_pago             INTEGER      NOT NULL DEFAULT nextval('seq_pagos'),
    cod_taller           INTEGER      NOT NULL,
    nombre_plan          VARCHAR(50)  NOT NULL,
    monto                INTEGER      NOT NULL,          -- COP
    referencia           VARCHAR(80)  NOT NULL,
    estado               VARCHAR(20)  NOT NULL DEFAULT 'PENDING', -- PENDING | APPROVED | DECLINED
    wompi_transaction_id VARCHAR(80),
    fecha                TIMESTAMP    NOT NULL DEFAULT now(),
    CONSTRAINT pk_pagos PRIMARY KEY (cod_pago),
    CONSTRAINT ux_pagos_referencia UNIQUE (referencia),
    CONSTRAINT fk_pagos_taller FOREIGN KEY (cod_taller) REFERENCES talleres (cod_taller),
    CONSTRAINT chk_pagos_estado CHECK (estado IN ('PENDING', 'APPROVED', 'DECLINED'))
);
-- pagos NO lleva RLS (el webhook público lo consulta por referencia sin tenant).

COMMIT;

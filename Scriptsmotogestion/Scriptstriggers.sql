-------------------------------------------------------------------------------
-- 1. tg_val_correo_cli
-- Tabla    : clientes
-- Momento  : BEFORE INSERT OR UPDATE
-- Propósito: Validar formato de correo electrónico
-- Error    : -20001
-------------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tg_val_correo_cli
BEFORE INSERT OR UPDATE ON clientes
FOR EACH ROW
BEGIN
    IF :NEW.correo_cli IS NOT NULL THEN
        IF NOT REGEXP_LIKE(
                :NEW.correo_cli,
                '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
           ) THEN
            RAISE_APPLICATION_ERROR(
                -20001,
                'El correo del cliente no tiene un formato válido.'
            );
        END IF;
    END IF;
END;
/

-------------------------------------------------------------------------------
-- 2. tg_val_telefono_cli
-- Tabla    : clientes
-- Momento  : BEFORE INSERT OR UPDATE
-- Propósito: Validar formato de teléfono (solo números)
-- Error    : -20002
-------------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tg_val_telefono_cli
BEFORE INSERT OR UPDATE ON clientes
FOR EACH ROW
BEGIN
    IF :NEW.telefono_cli IS NOT NULL THEN
        IF NOT REGEXP_LIKE(:NEW.telefono_cli, '^[0-9]+$') THEN
            RAISE_APPLICATION_ERROR(
                -20002,
                'El teléfono del cliente solo debe contener números.'
            );
        END IF;
    END IF;
END;
/

-------------------------------------------------------------------------------
-- 4. tg_actualizar_stock
-- Tabla    : detalle_orden_trabajo (lógica sobre productos)
-- Momento  : AFTER INSERT
-- Propósito: Descontar del stock del producto en tabla productos
-- NOTA     : No lanza error; solo actualiza stock.
-------------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tg_actualizar_stock
AFTER INSERT ON detalle_orden_trabajo
FOR EACH ROW
BEGIN
    UPDATE productos
       SET stock_pro = stock_pro - :NEW.cantidad_deto
     WHERE cod_pro   = :NEW.cod_pro_deto;
    -- Si quisieras validar que no quede negativo, eso ya lo hace tg_val_stock_disponible.
END;
/

-------------------------------------------------------------------------------
-- 5. tg_val_stock_disponible
-- Tabla    : detalle_orden_trabajo
-- Momento  : BEFORE INSERT
-- Propósito: Verificar que hay stock suficiente antes de agregar al detalle
-- Error    : -20004
-------------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tg_val_stock_disponible
BEFORE INSERT ON detalle_orden_trabajo
FOR EACH ROW
DECLARE
    v_stock productos.stock_pro%TYPE;
BEGIN
    BEGIN
        SELECT stock_pro
          INTO v_stock
          FROM productos
         WHERE cod_pro = :NEW.cod_pro_deto;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(
                -20004,
                'No existe el producto asociado al detalle de la orden de trabajo.'
            );
    END;

    IF :NEW.cantidad_deto > v_stock THEN
        RAISE_APPLICATION_ERROR(
            -20004,
            'No hay stock suficiente para el producto seleccionado.'
        );
    END IF;
END;
/

-------------------------------------------------------------------------------
-- 6. tg_fecha_confirm_deto
-- Tabla    : detalle_orden_trabajo
-- Momento  : BEFORE INSERT OR UPDATE
-- Propósito: Validar que fecha_confirmacion_deto no sea futura
-- Error    : -20005
-------------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tg_fecha_confirm_deto
BEFORE INSERT OR UPDATE ON detalle_orden_trabajo
FOR EACH ROW
BEGIN
    IF :NEW.fecha_confirmacion_deto IS NOT NULL
       AND :NEW.fecha_confirmacion_deto > SYSDATE THEN
        RAISE_APPLICATION_ERROR(
            -20005,
            'La fecha de confirmación del detalle no puede ser futura.'
        );
    END IF;
END;
/

-------------------------------------------------------------------------------
-- 7. tg_val_placa_mot
-- Tabla    : motos
-- Momento  : BEFORE INSERT OR UPDATE
-- Propósito: Validar formato de placa (alfanumérico, 5-6 caracteres)
-- Error    : -20006
-------------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tg_val_placa_mot
BEFORE INSERT OR UPDATE ON motos
FOR EACH ROW
BEGIN
    IF :NEW.placa_mot IS NULL
       OR NOT REGEXP_LIKE(:NEW.placa_mot, '^[A-Z0-9]{5,6}$') THEN
        RAISE_APPLICATION_ERROR(
            -20006,
            'La placa de la moto debe ser alfanumérica de 5 a 6 caracteres.'
        );
    END IF;
END;
/

-------------------------------------------------------------------------------
-- 8. tg_val_modelo_mot
-- Tabla    : motos
-- Momento  : BEFORE INSERT OR UPDATE
-- Propósito: Validar que modelo_mot sea >= 1950 y <= año actual + 1
-- Error    : -20007
-------------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tg_val_modelo_mot
BEFORE INSERT OR UPDATE ON motos
FOR EACH ROW
DECLARE
    v_anio_actual NUMBER;
BEGIN
    v_anio_actual := EXTRACT(YEAR FROM SYSDATE);

    IF :NEW.modelo_mot IS NULL
       OR :NEW.modelo_mot < 1950
       OR :NEW.modelo_mot > (v_anio_actual + 1) THEN
        RAISE_APPLICATION_ERROR(
            -20007,
            'El modelo de la moto debe estar entre 1950 y el año actual + 1.'
        );
    END IF;
END;
/

-------------------------------------------------------------------------------
-- 9. tg_val_cilindraje_mot
-- Tabla    : motos
-- Momento  : BEFORE INSERT OR UPDATE
-- Propósito: Validar que cilindraje_mot sea mayor que 0
-- Error    : -20008
-------------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tg_val_cilindraje_mot
BEFORE INSERT OR UPDATE ON motos
FOR EACH ROW
BEGIN
    IF :NEW.cilindraje_mot IS NULL
       OR :NEW.cilindraje_mot <= 0 THEN
        RAISE_APPLICATION_ERROR(
            -20008,
            'El cilindraje de la moto debe ser mayor que cero.'
        );
    END IF;
END;
/

-------------------------------------------------------------------------------
-- 10. tg_gen_consecutivo_ot
-- Tabla    : ordenes_trabajo
-- Momento  : BEFORE INSERT
-- Propósito: Generar consecutivo automático para la orden de trabajo
-- NOTA     : Usa MAX(consecutivo_ot) + 1 para evitar depender de una secuencia.
-------------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tg_gen_consecutivo_ot
BEFORE INSERT ON ordenes_trabajo
FOR EACH ROW
DECLARE
    v_max NUMBER;
BEGIN
    IF :NEW.consecutivo_ot IS NULL THEN
        SELECT NVL(MAX(consecutivo_ot), 0) + 1
          INTO v_max
          FROM ordenes_trabajo;

        :NEW.consecutivo_ot := v_max;
    END IF;
END;
/

-------------------------------------------------------------------------------
-- 11. tg_val_fechas_ot
-- Tabla    : ordenes_trabajo
-- Momento  : BEFORE INSERT OR UPDATE
-- Propósito: Validar que fecha_entrega_ot >= fecha_elaboracion_ot
-- Error    : -20009
-------------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tg_val_fechas_ot
BEFORE INSERT OR UPDATE ON ordenes_trabajo
FOR EACH ROW
BEGIN
    IF :NEW.fecha_elaboracion_ot IS NOT NULL
       AND :NEW.fecha_entrega_ot IS NOT NULL
       AND :NEW.fecha_entrega_ot < :NEW.fecha_elaboracion_ot THEN
        RAISE_APPLICATION_ERROR(
            -20009,
            'La fecha de entrega de la orden no puede ser anterior a la fecha de elaboración.'
        );
    END IF;
END;
/

-------------------------------------------------------------------------------
-- 12. tg_val_kilometraje_ot
-- Tabla    : ordenes_trabajo
-- Momento  : BEFORE INSERT OR UPDATE
-- Propósito: Validar que kilometraje_ingreso_ot sea mayor que 0
-- Error    : -20010
-------------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tg_val_kilometraje_ot
BEFORE INSERT OR UPDATE ON ordenes_trabajo
FOR EACH ROW
BEGIN
    IF :NEW.kilometraje_ingreso_ot IS NULL
       OR :NEW.kilometraje_ingreso_ot <= 0 THEN
        RAISE_APPLICATION_ERROR(
            -20010,
            'El kilometraje de ingreso debe ser mayor que cero.'
        );
    END IF;
END;
/

-------------------------------------------------------------------------------
-- 13. tg_val_usuarios_ot
-- Tabla    : ordenes_trabajo
-- Momento  : BEFORE INSERT OR UPDATE
-- Propósito: Validar que documento_usu_rp_ot sea diferente de documento_usu_mc_ot
-- Error    : -20011
-------------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tg_val_usuarios_ot
BEFORE INSERT OR UPDATE ON ordenes_trabajo
FOR EACH ROW
BEGIN
    IF :NEW.documento_usu_rp_ot IS NOT NULL
       AND :NEW.documento_usu_mc_ot IS NOT NULL
       AND :NEW.documento_usu_rp_ot = :NEW.documento_usu_mc_ot THEN
        RAISE_APPLICATION_ERROR(
            -20011,
            'El usuario responsable y el mecánico no pueden ser la misma persona en la orden de trabajo.'
        );
    END IF;
END;
/

-------------------------------------------------------------------------------
-- 14. tg_calc_fecha_garantia
-- Tabla    : ordenes_trabajo
-- Momento  : BEFORE INSERT OR UPDATE
-- Propósito: Calcular fecha_fin_garantia_ot automáticamente
-- NOTA     : Aquí se asume una garantía de 3 meses desde fecha_entrega_ot.
-------------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tg_calc_fecha_garantia
BEFORE INSERT OR UPDATE ON ordenes_trabajo
FOR EACH ROW
BEGIN
    IF :NEW.cod_ot_est_ot = 4 THEN
        IF :NEW.fecha_entrega_ot IS NOT NULL THEN
            :NEW.fecha_fin_garantia_ot := ADD_MONTHS(:NEW.fecha_entrega_ot, 1);
        END IF;
        
    ELSE
        :NEW.fecha_fin_garantia_ot := NULL;
    END IF;
END;
/

------------------------------------------------------------------------------
-- 15. tg_val_stock_pro
-- Tabla    : productos
-- Momento  : BEFORE INSERT OR UPDATE
-- Propósito: Validar que stock_pro sea mayor o igual a 0
-- Error    : -20012
-------------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tg_val_stock_pro
BEFORE INSERT OR UPDATE ON productos
FOR EACH ROW
BEGIN
    IF :NEW.stock_pro < 0 THEN
        RAISE_APPLICATION_ERROR(
            -20012,
            'El stock del producto no puede ser negativo.'
        );
    END IF;
END;
/

-------------------------------------------------------------------------------
-- 16. tg_val_precio_pro
-- Tabla    : productos
-- Momento  : BEFORE INSERT OR UPDATE
-- Propósito: Validar que precio_pro sea mayor que 0
-- Error    : -20013
-------------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tg_val_precio_pro
BEFORE INSERT OR UPDATE ON productos
FOR EACH ROW
BEGIN
    IF :NEW.precio_pro IS NULL
       OR :NEW.precio_pro <= 0 THEN
        RAISE_APPLICATION_ERROR(
            -20013,
            'El precio del producto debe ser mayor que cero.'
        );
    END IF;
END;
/

-------------------------------------------------------------------------------
-- 17. tg_alerta_stock_bajo
-- Tabla    : productos
-- Momento  : AFTER UPDATE
-- Propósito: Registrar alerta cuando stock_pro <= stock_pro_min
-- Error    : -20014  (si se desea bloquear la operación)
-- NOTA     : Si solo quieres alerta lógica y no bloquear, elimina el RAISE.
-------------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tg_alerta_stock_bajo
AFTER UPDATE ON productos
FOR EACH ROW
BEGIN
    IF :NEW.stock_pro <= :NEW.stock_pro_min THEN
        -- Aquí podrías llamar a una lógica de notificación externa.
        RAISE_APPLICATION_ERROR(
            -20014,
            'El stock del producto está por debajo o igual al mínimo permitido.'
        );
    END IF;
END;
/

-------------------------------------------------------------------------------
-- 18. tg_val_correo_usu
-- Tabla    : usuarios
-- Momento  : BEFORE INSERT OR UPDATE
-- Propósito: Validar formato de correo electrónico
-- Error    : -20015
-------------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tg_val_correo_usu
BEFORE INSERT OR UPDATE ON usuarios
FOR EACH ROW
BEGIN
    IF :NEW.correo_usu IS NOT NULL THEN
        IF NOT REGEXP_LIKE(
                :NEW.correo_usu,
                '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
           ) THEN
            RAISE_APPLICATION_ERROR(
                -20015,
                'El correo del usuario no tiene un formato válido.'
            );
        END IF;
    END IF;
END;
/

-------------------------------------------------------------------------------
-- 19. tg_val_ot_entregada
-- Tabla    : reclamos
-- Momento  : BEFORE INSERT
-- Propósito: Validar que la orden de trabajo esté en estado 'entregada'
-- Error    : -20016
-------------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tg_val_ot_entregada
BEFORE INSERT ON reclamos
FOR EACH ROW
DECLARE
    v_cod_estado ot_estados.cod_ot_est%TYPE;
BEGIN
    SELECT e.cod_ot_est
      INTO v_cod_estado
      FROM ordenes_trabajo ot
      JOIN ot_estados e
        ON ot.cod_ot_est_ot = e.cod_ot_est
     WHERE ot.consecutivo_ot = :NEW.consecutivo_ot_rec;

    IF v_cod_estado <> 4 THEN
        RAISE_APPLICATION_ERROR(
            -20016,
            'La orden de trabajo asociada al reclamo debe estar en estado ''Entregada''.'
        );
    END IF;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(
            -20016,
            'No existe una orden de trabajo asociada al reclamo.'
        );
END;

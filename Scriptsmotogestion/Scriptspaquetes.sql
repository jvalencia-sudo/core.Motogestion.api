---Paquete de Auditoria
CREATE OR REPLACE PACKAGE PKG_AUDITORIA AS

    FUNCTION EXISTE_ARCHIVO(
        p_directorio IN VARCHAR2,
        p_archivo    IN VARCHAR2
    ) RETURN BOOLEAN;

    PROCEDURE AUDITORIA_TABLAS_LOG (
        p_usuario         VARCHAR2,
        p_tabla           VARCHAR2,
        p_evento          VARCHAR2,
        p_valor_anterior  VARCHAR2,
        p_valor_nuevo     VARCHAR2
    );

END PKG_AUDITORIA;
/

CREATE OR REPLACE PACKAGE BODY PKG_AUDITORIA AS

    FUNCTION EXISTE_ARCHIVO(
        p_directorio IN VARCHAR2,
        p_archivo    IN VARCHAR2
    ) RETURN BOOLEAN
    IS
        v_existe     BOOLEAN;
        v_file_len   NUMBER;
        v_block_size NUMBER;
    BEGIN
        UTL_FILE.FGETATTR(p_directorio, p_archivo, v_existe, v_file_len, v_block_size);
        RETURN v_existe;

    EXCEPTION
        WHEN OTHERS THEN
            RETURN FALSE;
    END EXISTE_ARCHIVO;

    PROCEDURE AUDITORIA_TABLAS_LOG (
        p_usuario         VARCHAR2,
        p_tabla           VARCHAR2,
        p_evento          VARCHAR2,
        p_valor_anterior  VARCHAR2,
        p_valor_nuevo     VARCHAR2
    ) AS
        v_archivo   UTL_FILE.FILE_TYPE;
        v_nombre    VARCHAR2(100);
        v_texto     VARCHAR2(4000);
    BEGIN
        v_nombre := 'auditoria_' || TO_CHAR(SYSDATE, 'YYYYMMDD') || '.txt';
        v_texto := 'U:' || p_usuario || ',T:' || p_tabla || ',E:' || p_evento;
        IF p_evento = 'U' THEN
            v_texto := v_texto || ',AN:' || p_valor_anterior || ',NU:' || p_valor_nuevo;
        ELSIF p_evento = 'I' THEN
            v_texto := v_texto || ',NU:' || p_valor_nuevo;
        ELSIF p_evento = 'D' THEN
            v_texto := v_texto || ',AN:' || p_valor_anterior;
        END IF;
        IF EXISTE_ARCHIVO('DIR_LOGS', v_nombre) THEN
            v_archivo := UTL_FILE.FOPEN('DIR_LOGS', v_nombre, 'A');
        ELSE
            v_archivo := UTL_FILE.FOPEN('DIR_LOGS', v_nombre, 'W');
        END IF;
        UTL_FILE.PUT_LINE(v_archivo, v_texto);
        UTL_FILE.FCLOSE(v_archivo);

    EXCEPTION
        WHEN OTHERS THEN
            NULL; 
    END AUDITORIA_TABLAS_LOG;

END PKG_AUDITORIA;
/

CREATE OR REPLACE FUNCTION FN_EXISTE_ARCHIVO(
    p_directorio IN VARCHAR2,
    p_archivo    IN VARCHAR2
) RETURN BOOLEAN
IS
    v_existe     BOOLEAN;
    v_file_len   NUMBER;
    v_block_size NUMBER;
BEGIN
    UTL_FILE.FGETATTR(p_directorio, p_archivo, v_existe, v_file_len, v_block_size);
    RETURN v_existe;
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;
/
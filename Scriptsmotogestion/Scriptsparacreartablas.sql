CREATE TABLE clientes (
    documento_cli  VARCHAR2(11 BYTE),
    nombre_cli     VARCHAR2(50 BYTE),
    apellido_1_cli VARCHAR2(50 BYTE),
    apellido_2_cli VARCHAR2(50 BYTE),
    telefono_cli   VARCHAR2(15 BYTE),
    correo_cli     VARCHAR2(50 BYTE),
    direccion_cli  VARCHAR2(500 BYTE)
) TABLESPACE ts_ppi;

CREATE TABLE detalle_orden_trabajo (
    consecutivo_ot_deto     NUMBER(7),
    cod_pro_deto            NUMBER(5),
    fecha_confirmacion_deto DATE,
    valor_unitario_deto     NUMBER(8),
    cantidad_deto           NUMBER(2),
    documento_usu_deto      VARCHAR2(11 BYTE)
) TABLESPACE ts_ppi;

CREATE TABLE estados (
    cod_est    NUMBER(1),
    nombre_est VARCHAR2(50 BYTE)
) TABLESPACE ts_ppi;

CREATE TABLE excepciones (
    cod_exc         NUMBER(2),
    nombre_exc      VARCHAR2(250 BYTE),
    descripcion_exp VARCHAR2(500 BYTE)
) TABLESPACE ts_ppi;

CREATE TABLE impuestos (
    cod_imp        NUMBER(2),
    nombre_imp     VARCHAR2(50),
    porcentaje_imp NUMBER(5, 2)
) TABLESPACE ts_ppi;

CREATE TABLE marcas (
    cod_mar    NUMBER(3),
    nombre_mar VARCHAR2(50)
) TABLESPACE ts_ppi;

CREATE TABLE motos (
    placa_mot         VARCHAR2(6 BYTE),
    modelo_mot        NUMBER(4),
    color_mot         VARCHAR2(50),
    cilindraje_mot    NUMBER(4),
    documento_cli_mot VARCHAR2(11 BYTE),
    cod_marca_mot     NUMBER(3)
) TABLESPACE ts_ppi;

CREATE TABLE ordenes_trabajo (
    consecutivo_ot         NUMBER(7),
    fecha_elaboracion_ot   DATE,
    fecha_entrega_ot       DATE,
    kilometraje_ingreso_ot NUMBER(7),
    kilometreje_salida_ot  DATE,
    observacion_cli_ot     VARCHAR2(500 BYTE),
    observacion_ot         VARCHAR2(500 BYTE),
    placa_mot_ot           VARCHAR2(6 BYTE),
    documento_usu_rp_ot    VARCHAR2(11 BYTE),
    documento_usu_mc_ot    VARCHAR2(11 BYTE),
    cod_ot_est_ot          NUMBER(1),
    fecha_fin_garantia_ot  DATE
) TABLESPACE ts_ppi;

CREATE TABLE ot_estados (
    cod_ot_est    NUMBER(1),
    nombre_ot_est VARCHAR2(50 BYTE)
) TABLESPACE ts_ppi;

CREATE TABLE perfiles (
    cod_prf         NUMBER(2),
    nombre_prf      VARCHAR2(250 BYTE),
    descripcion_prf VARCHAR2(500 BYTE),
    cod_est_prf     NUMBER(1),
    cod_rol_prf     NUMBER(2)
) TABLESPACE ts_ppi;

CREATE TABLE perfiles_permisos (
    cod_prm_pp     NUMBER(3),
    cod_prf_pp     NUMBER(2),
    cod_rol_prf_pp NUMBER(2),
    cod_est_pp     NUMBER(1)
) TABLESPACE ts_ppi;

CREATE TABLE permisos (
    cod_prm         NUMBER(3),
    nombre_prm      VARCHAR2(250 BYTE),
    descripcion_prm VARCHAR2(500 BYTE),
    ruta_vis_prm    VARCHAR2(500 BYTE)
) TABLESPACE ts_ppi;

CREATE TABLE productos (
    cod_pro         NUMBER(5),
    nombre_pro      VARCHAR2(70 BYTE),
    descripcion_pro VARCHAR2(500 BYTE),
    stock_pro       NUMBER(3),
    stock_pro_min   NUMBER(3),
    cod_est_pro     NUMBER(1),
    precio_pro      NUMBER(8)
) TABLESPACE ts_ppi;

CREATE TABLE productos_impuestos (
    cod_pro_imp        NUMBER(7),
    cod_imp_pro_imp    NUMBER(2),
    cod_pro_pro_imp    NUMBER(5),
    porcentaje_pro_imp NUMBER(5, 2)
) TABLESPACE ts_ppi;

CREATE TABLE reclamos (
    cod_rec            NUMBER(7),
    descripcion_rec    VARCHAR2(500 BYTE),
    consecutivo_ot_rec NUMBER(7)
) TABLESPACE ts_ppi;

CREATE TABLE roles (
    cod_rol         NUMBER(2),
    nombre_rol      VARCHAR2(250 BYTE),
    descripcion_rol VARCHAR2(500 BYTE)
) TABLESPACE ts_ppi;

CREATE TABLE usuarios (
    documento_usu   VARCHAR2(11 BYTE),
    nombre_usu      VARCHAR2(50 BYTE),
    apellido_1_usu  VARCHAR2(50 BYTE),
    apellido_2_usu  VARCHAR2(50 BYTE),
    correo_usu      VARCHAR2(50 BYTE),
    contrasena_usu  VARCHAR2(50 BYTE),
    cod_tipo_usu    NUMBER,
    cod_est_usu     NUMBER(1),
    sub_id_usu      VARCHAR2(250 BYTE),
    cod_prf_usu     NUMBER(2),
    cod_rol_prf_usu NUMBER(2)
) TABLESPACE ts_ppi;

CREATE TABLE vistas (
    ruta_vis   VARCHAR2(500 BYTE),
    nombre_vis VARCHAR2(50 BYTE)
) TABLESPACE ts_ppi;
CREATE OR REPLACE DIRECTORY DIR_LOGS AS 'C:\nada';

CREATE OR REPLACE TRIGGER TG_AUDITORIA_CLIENTES_LOG
BEFORE INSERT OR UPDATE OR DELETE ON clientes
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'clientes', 'I', NULL,
            'doc:'||:NEW.documento_cli||',nombre:'||:NEW.nombre_cli||',apellido1:'||:NEW.apellido_1_cli||',apellido2:'||:NEW.apellido_2_cli||
            ',telefono:'||:NEW.telefono_cli||',correo:'||:NEW.correo_cli||',direccion:'||:NEW.direccion_cli);
    ELSIF UPDATING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'clientes', 'U',
            'doc:'||:OLD.documento_cli||',nombre:'||:OLD.nombre_cli||',apellido1:'||:OLD.apellido_1_cli||',apellido2:'||:OLD.apellido_2_cli||
            ',telefono:'||:OLD.telefono_cli||',correo:'||:OLD.correo_cli||',direccion:'||:OLD.direccion_cli,
            'doc:'||:NEW.documento_cli||',nombre:'||:NEW.nombre_cli||',apellido1:'||:NEW.apellido_1_cli||',apellido2:'||:NEW.apellido_2_cli||
            ',telefono:'||:NEW.telefono_cli||',correo:'||:NEW.correo_cli||',direccion:'||:NEW.direccion_cli);
    ELSIF DELETING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'clientes', 'D',
            'doc:'||:OLD.documento_cli||',nombre:'||:OLD.nombre_cli||',apellido1:'||:OLD.apellido_1_cli||',apellido2:'||:OLD.apellido_2_cli||
            ',telefono:'||:OLD.telefono_cli||',correo:'||:OLD.correo_cli||',direccion:'||:OLD.direccion_cli,
            NULL);
    END IF;
END;
/


CREATE OR REPLACE TRIGGER TG_AUDITORIA_DETALLE_OT_LOG
BEFORE INSERT OR UPDATE OR DELETE ON detalle_orden_trabajo
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'detalle_orden_trabajo', 'I', NULL,
            'cons:'||:NEW.consecutivo_ot_deto||',prod:'||:NEW.cod_pro_deto||',fecha:'||TO_CHAR(:NEW.fecha_confirmacion_deto,'YYYY-MM-DD')||
            ',valor:'||:NEW.valor_unitario_deto||',cant:'||:NEW.cantidad_deto||',usu:'||:NEW.documento_usu_deto);
    ELSIF UPDATING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'detalle_orden_trabajo', 'U',
            'cons:'||:OLD.consecutivo_ot_deto||',prod:'||:OLD.cod_pro_deto||',fecha:'||TO_CHAR(:OLD.fecha_confirmacion_deto,'YYYY-MM-DD')||
            ',valor:'||:OLD.valor_unitario_deto||',cant:'||:OLD.cantidad_deto||',usu:'||:OLD.documento_usu_deto,
            'cons:'||:NEW.consecutivo_ot_deto||',prod:'||:NEW.cod_pro_deto||',fecha:'||TO_CHAR(:NEW.fecha_confirmacion_deto,'YYYY-MM-DD')||
            ',valor:'||:NEW.valor_unitario_deto||',cant:'||:NEW.cantidad_deto||',usu:'||:NEW.documento_usu_deto);
    ELSIF DELETING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'detalle_orden_trabajo', 'D',
            'cons:'||:OLD.consecutivo_ot_deto||',prod:'||:OLD.cod_pro_deto||',fecha:'||TO_CHAR(:OLD.fecha_confirmacion_deto,'YYYY-MM-DD')||
            ',valor:'||:OLD.valor_unitario_deto||',cant:'||:OLD.cantidad_deto||',usu:'||:OLD.documento_usu_deto,
            NULL);
    END IF;
END;
/

CREATE OR REPLACE TRIGGER TG_AUDITORIA_ESTADOS_LOG
BEFORE INSERT OR UPDATE OR DELETE ON estados
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'estados', 'I', NULL, 'cod:'||:NEW.cod_est||',nombre:'||:NEW.nombre_est);
    ELSIF UPDATING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'estados', 'U',
            'cod:'||:OLD.cod_est||',nombre:'||:OLD.nombre_est,
            'cod:'||:NEW.cod_est||',nombre:'||:NEW.nombre_est);
    ELSIF DELETING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'estados', 'D',
            'cod:'||:OLD.cod_est||',nombre:'||:OLD.nombre_est, NULL);
    END IF;
END;
/


CREATE OR REPLACE TRIGGER TG_AUDITORIA_EXCEPCIONES_LOG
BEFORE INSERT OR UPDATE OR DELETE ON excepciones
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'excepciones', 'I', NULL,
            'cod:'||:NEW.cod_exc||',nombre:'||:NEW.nombre_exc||',desc:'||:NEW.descripcion_exp);
    ELSIF UPDATING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'excepciones', 'U',
            'cod:'||:OLD.cod_exc||',nombre:'||:OLD.nombre_exc||',desc:'||:OLD.descripcion_exp,
            'cod:'||:NEW.cod_exc||',nombre:'||:NEW.nombre_exc||',desc:'||:NEW.descripcion_exp);
    ELSIF DELETING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'excepciones', 'D',
            'cod:'||:OLD.cod_exc||',nombre:'||:OLD.nombre_exc||',desc:'||:OLD.descripcion_exp, NULL);
    END IF;
END;
/


CREATE OR REPLACE TRIGGER TG_AUDITORIA_IMPUESTOS_LOG
BEFORE INSERT OR UPDATE OR DELETE ON impuestos
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'impuestos', 'I', NULL,
            'cod:'||:NEW.cod_imp||',nombre:'||:NEW.nombre_imp||',porcentaje:'||:NEW.porcentaje_imp);
    ELSIF UPDATING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'impuestos', 'U',
            'cod:'||:OLD.cod_imp||',nombre:'||:OLD.nombre_imp||',porcentaje:'||:OLD.porcentaje_imp,
            'cod:'||:NEW.cod_imp||',nombre:'||:NEW.nombre_imp||',porcentaje:'||:NEW.porcentaje_imp);
    ELSIF DELETING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'impuestos', 'D',
            'cod:'||:OLD.cod_imp||',nombre:'||:OLD.nombre_imp||',porcentaje:'||:OLD.porcentaje_imp, NULL);
    END IF;
END;
/

CREATE OR REPLACE TRIGGER TG_AUDITORIA_MARCAS_LOG
BEFORE INSERT OR UPDATE OR DELETE ON marcas
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'marcas', 'I', NULL, 'cod:'||:NEW.cod_mar||',nombre:'||:NEW.nombre_mar);
    ELSIF UPDATING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'marcas', 'U',
            'cod:'||:OLD.cod_mar||',nombre:'||:OLD.nombre_mar,
            'cod:'||:NEW.cod_mar||',nombre:'||:NEW.nombre_mar);
    ELSIF DELETING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'marcas', 'D',
            'cod:'||:OLD.cod_mar||',nombre:'||:OLD.nombre_mar, NULL);
    END IF;
END;
/


CREATE OR REPLACE TRIGGER TG_AUDITORIA_MOTOS_LOG
BEFORE INSERT OR UPDATE OR DELETE ON motos
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'motos', 'I', NULL,
            'placa:'||:NEW.placa_mot||',modelo:'||:NEW.modelo_mot||',color:'||:NEW.color_mot||
            ',cilindraje:'||:NEW.cilindraje_mot||',doc_cli:'||:NEW.documento_cli_mot||',marca:'||:NEW.cod_marca_mot);
    ELSIF UPDATING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'motos', 'U',
            'placa:'||:OLD.placa_mot||',modelo:'||:OLD.modelo_mot||',color:'||:OLD.color_mot||
            ',cilindraje:'||:OLD.cilindraje_mot||',doc_cli:'||:OLD.documento_cli_mot||',marca:'||:OLD.cod_marca_mot,
            'placa:'||:NEW.placa_mot||',modelo:'||:NEW.modelo_mot||',color:'||:NEW.color_mot||
            ',cilindraje:'||:NEW.cilindraje_mot||',doc_cli:'||:NEW.documento_cli_mot||',marca:'||:NEW.cod_marca_mot);
    ELSIF DELETING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'motos', 'D',
            'placa:'||:OLD.placa_mot||',modelo:'||:OLD.modelo_mot||',color:'||:OLD.color_mot||
            ',cilindraje:'||:OLD.cilindraje_mot||',doc_cli:'||:OLD.documento_cli_mot||',marca:'||:OLD.cod_marca_mot,
            NULL);
    END IF;
END;
/

CREATE OR REPLACE TRIGGER TG_AUDITORIA_ORDENES_TRABAJO_LOG
BEFORE INSERT OR UPDATE OR DELETE ON ordenes_trabajo
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'ordenes_trabajo', 'I', NULL,
            'cons:'||:NEW.consecutivo_ot||',fecha_ela:'||TO_CHAR(:NEW.fecha_elaboracion_ot,'YYYY-MM-DD')||
            ',fecha_ent:'||TO_CHAR(:NEW.fecha_entrega_ot,'YYYY-MM-DD')||
            ',km_ing:'||:NEW.kilometraje_ingreso_ot||',km_sal:'||:NEW.kilometreje_salida_ot||
            ',obs_cli:'||:NEW.observacion_cli_ot||',obs_ot:'||:NEW.observacion_ot||
            ',placa:'||:NEW.placa_mot_ot||',usu_rp:'||:NEW.documento_usu_rp_ot||
            ',usu_mc:'||:NEW.documento_usu_mc_ot||',est:'||:NEW.cod_ot_est_ot||
            ',fin_gar:'||TO_CHAR(:NEW.fecha_fin_garantia_ot,'YYYY-MM-DD'));
    ELSIF UPDATING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'ordenes_trabajo', 'U',
            'cons:'||:OLD.consecutivo_ot||',fecha_ela:'||TO_CHAR(:OLD.fecha_elaboracion_ot,'YYYY-MM-DD')||
            ',fecha_ent:'||TO_CHAR(:OLD.fecha_entrega_ot,'YYYY-MM-DD')||
            ',km_ing:'||:OLD.kilometraje_ingreso_ot||',km_sal:'||:OLD.kilometreje_salida_ot||
            ',obs_cli:'||:OLD.observacion_cli_ot||',obs_ot:'||:OLD.observacion_ot||
            ',placa:'||:OLD.placa_mot_ot||',usu_rp:'||:OLD.documento_usu_rp_ot||
            ',usu_mc:'||:OLD.documento_usu_mc_ot||',est:'||:OLD.cod_ot_est_ot||
            ',fin_gar:'||TO_CHAR(:OLD.fecha_fin_garantia_ot,'YYYY-MM-DD'),
            'cons:'||:NEW.consecutivo_ot||',fecha_ela:'||TO_CHAR(:NEW.fecha_elaboracion_ot,'YYYY-MM-DD')||
            ',fecha_ent:'||TO_CHAR(:NEW.fecha_entrega_ot,'YYYY-MM-DD')||
            ',km_ing:'||:NEW.kilometraje_ingreso_ot||',km_sal:'||:NEW.kilometreje_salida_ot||
            ',obs_cli:'||:NEW.observacion_cli_ot||',obs_ot:'||:NEW.observacion_ot||
            ',placa:'||:NEW.placa_mot_ot||',usu_rp:'||:NEW.documento_usu_rp_ot||
            ',usu_mc:'||:NEW.documento_usu_mc_ot||',est:'||:NEW.cod_ot_est_ot||
            ',fin_gar:'||TO_CHAR(:NEW.fecha_fin_garantia_ot,'YYYY-MM-DD'));
    ELSIF DELETING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'ordenes_trabajo', 'D',
            'cons:'||:OLD.consecutivo_ot||',fecha_ela:'||TO_CHAR(:OLD.fecha_elaboracion_ot,'YYYY-MM-DD')||
            ',fecha_ent:'||TO_CHAR(:OLD.fecha_entrega_ot,'YYYY-MM-DD')||
            ',km_ing:'||:OLD.kilometraje_ingreso_ot||',km_sal:'||:OLD.kilometreje_salida_ot||
            ',obs_cli:'||:OLD.observacion_cli_ot||',obs_ot:'||:OLD.observacion_ot||
            ',placa:'||:OLD.placa_mot_ot||',usu_rp:'||:OLD.documento_usu_rp_ot||
            ',usu_mc:'||:OLD.documento_usu_mc_ot||',est:'||:OLD.cod_ot_est_ot||
            ',fin_gar:'||TO_CHAR(:OLD.fecha_fin_garantia_ot,'YYYY-MM-DD'),
            NULL);
    END IF;
END;
/

CREATE OR REPLACE TRIGGER TG_AUDITORIA_OT_ESTADOS_LOG
BEFORE INSERT OR UPDATE OR DELETE ON ot_estados
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'ot_estados', 'I', NULL, 'cod:'||:NEW.cod_ot_est||',nombre:'||:NEW.nombre_ot_est);
    ELSIF UPDATING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'ot_estados', 'U',
            'cod:'||:OLD.cod_ot_est||',nombre:'||:OLD.nombre_ot_est,
            'cod:'||:NEW.cod_ot_est||',nombre:'||:NEW.nombre_ot_est);
    ELSIF DELETING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'ot_estados', 'D',
            'cod:'||:OLD.cod_ot_est||',nombre:'||:OLD.nombre_ot_est, NULL);
    END IF;
END;
/

CREATE OR REPLACE TRIGGER TG_AUDITORIA_PERFILES_LOG
BEFORE INSERT OR UPDATE OR DELETE ON perfiles
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER,'perfiles','I',NULL,
            'cod:'||:NEW.cod_prf||',nom:'||:NEW.nombre_prf||
            ',des:'||:NEW.descripcion_prf||',est:'||:NEW.cod_est_prf||
            ',rol:'||:NEW.cod_rol_prf);

    ELSIF UPDATING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER,'perfiles','U',
            'cod:'||:OLD.cod_prf||',nom:'||:OLD.nombre_prf||
            ',des:'||:OLD.descripcion_prf||',est:'||:OLD.cod_est_prf||
            ',rol:'||:OLD.cod_rol_prf,
            'cod:'||:NEW.cod_prf||',nom:'||:NEW.nombre_prf||
            ',des:'||:NEW.descripcion_prf||',est:'||:NEW.cod_est_prf||
            ',rol:'||:NEW.cod_rol_prf);

    ELSIF DELETING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER,'perfiles','D',
            'cod:'||:OLD.cod_prf||',nom:'||:OLD.nombre_prf||
            ',des:'||:OLD.descripcion_prf||',est:'||:OLD.cod_est_prf||
            ',rol:'||:OLD.cod_rol_prf,
            NULL);
    END IF;
END;
/

CREATE OR REPLACE TRIGGER TG_AUDITORIA_PERMISOS
BEFORE INSERT OR UPDATE OR DELETE ON permisos
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER,'permisos','I',NULL,
            'cod:'||:NEW.cod_prm||',nom:'||:NEW.nombre_prm||
            ',ruta:'||:NEW.ruta_vis_prm);
            
    ELSIF UPDATING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER,'permisos','U',
            'cod:'||:OLD.cod_prm||',nom:'||:OLD.nombre_prm||
            ',ruta:'||:OLD.ruta_vis_prm,
            'cod:'||:NEW.cod_prm||',nom:'||:NEW.nombre_prm||
            ',ruta:'||:NEW.ruta_vis_prm);
            
    ELSIF DELETING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER,'permisos','D',
            'cod:'||:OLD.cod_prm||',nom:'||:OLD.nombre_prm||
            ',ruta:'||:OLD.ruta_vis_prm,
            NULL);
    END IF;
END;
/
CREATE OR REPLACE TRIGGER TG_AUDITORIA_PERFILES_PERMISOS
BEFORE INSERT OR UPDATE OR DELETE ON perfiles_permisos
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER,'perfiles_permisos','I',NULL,
            'cod_pp:'||:NEW.cod_prm_pp||',prf:'||:NEW.cod_prf_pp||
            ',rol:'||:NEW.cod_rol_prf_pp||',est:'||:NEW.cod_est_pp);

    ELSIF UPDATING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER,'perfiles_permisos','U',
            'cod_pp:'||:OLD.cod_prm_pp||',prf:'||:OLD.cod_prf_pp||
            ',rol:'||:OLD.cod_rol_prf_pp||',est:'||:OLD.cod_est_pp,
            'cod_pp:'||:NEW.cod_prm_pp||',prf:'||:NEW.cod_prf_pp||
            ',rol:'||:NEW.cod_rol_prf_pp||',est:'||:NEW.cod_est_pp);

    ELSIF DELETING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER,'perfiles_permisos','D',
            'cod_pp:'||:OLD.cod_prm_pp||',prf:'||:OLD.cod_prf_pp||
            ',rol:'||:OLD.cod_rol_prf_pp||',est:'||:OLD.cod_est_pp,
            NULL);
    END IF;
END;
/

CREATE OR REPLACE TRIGGER TG_AUDITORIA_PRODUCTOS_LOG
BEFORE INSERT OR UPDATE OR DELETE ON productos
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'productos', 'I', NULL,
            'cod:'||:NEW.cod_pro||',nombre:'||:NEW.nombre_pro||',desc:'||:NEW.descripcion_pro||
            ',stock:'||:NEW.stock_pro||',stock_min:'||:NEW.stock_pro_min||',estado:'||:NEW.cod_est_pro||
            ',precio:'||:NEW.precio_pro);
    ELSIF UPDATING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'productos', 'U',
            'cod:'||:OLD.cod_pro||',nombre:'||:OLD.nombre_pro||',desc:'||:OLD.descripcion_pro||
            ',stock:'||:OLD.stock_pro||',stock_min:'||:OLD.stock_pro_min||',estado:'||:OLD.cod_est_pro||
            ',precio:'||:OLD.precio_pro,
            'cod:'||:NEW.cod_pro||',nombre:'||:NEW.nombre_pro||',desc:'||:NEW.descripcion_pro||
            ',stock:'||:NEW.stock_pro||',stock_min:'||:NEW.stock_pro_min||',estado:'||:NEW.cod_est_pro||
            ',precio:'||:NEW.precio_pro);
    ELSIF DELETING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'productos', 'D',
            'cod:'||:OLD.cod_pro||',nombre:'||:OLD.nombre_pro||',desc:'||:OLD.descripcion_pro||
            ',stock:'||:OLD.stock_pro||',stock_min:'||:OLD.stock_pro_min||',estado:'||:OLD.cod_est_pro||
            ',precio:'||:OLD.precio_pro,
            NULL);
    END IF;
END;
/

CREATE OR REPLACE TRIGGER TG_AUDITORIA_PRODUCTOS_IMP_LOG
BEFORE INSERT OR UPDATE OR DELETE ON productos_impuestos
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'productos_impuestos', 'I', NULL,
            'cod:'||:NEW.cod_pro_imp||',imp:'||:NEW.cod_imp_pro_imp||',pro:'||:NEW.cod_pro_pro_imp||
            ',porc:'||:NEW.porcentaje_pro_imp);
    ELSIF UPDATING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'productos_impuestos', 'U',
            'cod:'||:OLD.cod_pro_imp||',imp:'||:OLD.cod_imp_pro_imp||',pro:'||:OLD.cod_pro_pro_imp||
            ',porc:'||:OLD.porcentaje_pro_imp,
            'cod:'||:NEW.cod_pro_imp||',imp:'||:NEW.cod_imp_pro_imp||',pro:'||:NEW.cod_pro_pro_imp||
            ',porc:'||:NEW.porcentaje_pro_imp);
    ELSIF DELETING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'productos_impuestos', 'D',
            'cod:'||:OLD.cod_pro_imp||',imp:'||:OLD.cod_imp_pro_imp||',pro:'||:OLD.cod_pro_pro_imp||
            ',porc:'||:OLD.porcentaje_pro_imp,
            NULL);
    END IF;
END;
/

CREATE OR REPLACE TRIGGER TG_AUDITORIA_RECLAMOS_LOG
BEFORE INSERT OR UPDATE OR DELETE ON reclamos
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'reclamos', 'I', NULL,
            'cod:'||:NEW.cod_rec||',desc:'||:NEW.descripcion_rec||',ot:'||:NEW.consecutivo_ot_rec);
    ELSIF UPDATING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'reclamos', 'U',
            'cod:'||:OLD.cod_rec||',desc:'||:OLD.descripcion_rec||',ot:'||:OLD.consecutivo_ot_rec,
            'cod:'||:NEW.cod_rec||',desc:'||:NEW.descripcion_rec||',ot:'||:NEW.consecutivo_ot_rec);
    ELSIF DELETING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'reclamos', 'D',
            'cod:'||:OLD.cod_rec||',desc:'||:OLD.descripcion_rec||',ot:'||:OLD.consecutivo_ot_rec, NULL);
    END IF;
END;
/

CREATE OR REPLACE TRIGGER TG_AUDITORIA_ROLES_LOG
BEFORE INSERT OR UPDATE OR DELETE ON roles
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'roles', 'I', NULL,
            'cod:'||:NEW.cod_rol||',nombre:'||:NEW.nombre_rol||',desc:'||:NEW.descripcion_rol);
    ELSIF UPDATING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'roles', 'U',
            'cod:'||:OLD.cod_rol||',nombre:'||:OLD.nombre_rol||',desc:'||:OLD.descripcion_rol,
            'cod:'||:NEW.cod_rol||',nombre:'||:NEW.nombre_rol||',desc:'||:NEW.descripcion_rol);
    ELSIF DELETING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'roles', 'D',
            'cod:'||:OLD.cod_rol||',nombre:'||:OLD.nombre_rol||',desc:'||:OLD.descripcion_rol, NULL);
    END IF;
END;
/

CREATE OR REPLACE TRIGGER TG_AUDITORIA_USUARIOS_LOG
BEFORE INSERT OR UPDATE OR DELETE ON usuarios
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'usuarios', 'I', NULL,
            'doc:'||:NEW.documento_usu||',nombre:'||:NEW.nombre_usu||',correo:'||:NEW.correo_usu);
    ELSIF UPDATING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'usuarios', 'U',
            'doc:'||:OLD.documento_usu||',nombre:'||:OLD.nombre_usu||',correo:'||:OLD.correo_usu,
            'doc:'||:NEW.documento_usu||',nombre:'||:NEW.nombre_usu||',correo:'||:NEW.correo_usu);
    ELSIF DELETING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'usuarios', 'D',
            'doc:'||:OLD.documento_usu||',nombre:'||:OLD.nombre_usu||',correo:'||:OLD.correo_usu, NULL);
    END IF;
END;
/

CREATE OR REPLACE TRIGGER TG_AUDITORIA_VISTAS_LOG
BEFORE INSERT OR UPDATE OR DELETE ON vistas
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'vistas', 'I', NULL,
            'ruta:'||:NEW.ruta_vis||',nombre:'||:NEW.nombre_vis);
    ELSIF UPDATING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'vistas', 'U',
            'ruta:'||:OLD.ruta_vis||',nombre:'||:OLD.nombre_vis,
            'ruta:'||:NEW.ruta_vis||',nombre:'||:NEW.nombre_vis);
    ELSIF DELETING THEN
        PKG_AUDITORIA.AUDITORIA_TABLAS_LOG(USER, 'vistas', 'D',
            'ruta:'||:OLD.ruta_vis||',nombre:'||:OLD.nombre_vis, NULL);
    END IF;
END;
/

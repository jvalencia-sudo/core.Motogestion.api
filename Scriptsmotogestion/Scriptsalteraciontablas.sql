ALTER TABLE clientes ADD CONSTRAINT clientes_pk PRIMARY KEY (documento_cli);
ALTER TABLE detalle_orden_trabajo ADD CONSTRAINT det_ot_pk PRIMARY KEY (cod_pro_deto, consecutivo_ot_deto);
ALTER TABLE estados ADD CONSTRAINT estados_pk PRIMARY KEY (cod_est);
ALTER TABLE excepciones ADD CONSTRAINT excepciones_pk PRIMARY KEY (cod_exc);
ALTER TABLE impuestos ADD CONSTRAINT impuestos_pk PRIMARY KEY (cod_imp);
ALTER TABLE marcas ADD CONSTRAINT marcas_pk PRIMARY KEY (cod_mar);
ALTER TABLE motos ADD CONSTRAINT motos_pk PRIMARY KEY (placa_mot);
ALTER TABLE ordenes_trabajo ADD CONSTRAINT ot_pk PRIMARY KEY (consecutivo_ot);
ALTER TABLE ot_estados ADD CONSTRAINT ot_est_pk PRIMARY KEY (cod_ot_est);
ALTER TABLE perfiles ADD CONSTRAINT perfiles_pk PRIMARY KEY (cod_prf, cod_rol_prf);
ALTER TABLE perfiles_permisos ADD CONSTRAINT perf_perm_pk PRIMARY KEY (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp);
ALTER TABLE permisos ADD CONSTRAINT permisos_pk PRIMARY KEY (cod_prm);
ALTER TABLE productos ADD CONSTRAINT prod_pk PRIMARY KEY (cod_pro);
ALTER TABLE productos_impuestos ADD CONSTRAINT pimp_pk PRIMARY KEY (cod_pro_imp);
ALTER TABLE reclamos ADD CONSTRAINT reclamos_pk PRIMARY KEY (cod_rec);
ALTER TABLE roles ADD CONSTRAINT roles_pk PRIMARY KEY (cod_rol);
ALTER TABLE usuarios ADD CONSTRAINT usuarios_pk PRIMARY KEY (documento_usu);
ALTER TABLE vistas ADD CONSTRAINT vistas_pk PRIMARY KEY (ruta_vis);

ALTER TABLE usuarios ADD CONSTRAINT usuarios_un UNIQUE (correo_usu, sub_id_usu);



ALTER TABLE detalle_orden_trabajo
    ADD CONSTRAINT detalle_orden_trabajo_inventario_fk FOREIGN KEY ( cod_pro_deto )
        REFERENCES productos ( cod_pro );

ALTER TABLE detalle_orden_trabajo
    ADD CONSTRAINT detalle_orden_trabajo_ordenes_trabajo_fk FOREIGN KEY ( consecutivo_ot_deto )
        REFERENCES ordenes_trabajo ( consecutivo_ot );

ALTER TABLE detalle_orden_trabajo
    ADD CONSTRAINT detalle_orden_trabajo_usuario_fk FOREIGN KEY ( documento_usu_deto )
        REFERENCES usuarios ( documento_usu );

ALTER TABLE productos
    ADD CONSTRAINT inventario_estados_fk FOREIGN KEY ( cod_est_pro )
        REFERENCES estados ( cod_est );

ALTER TABLE motos
    ADD CONSTRAINT motos_clientes_fk FOREIGN KEY ( documento_cli_mot )
        REFERENCES clientes ( documento_cli );

ALTER TABLE motos
    ADD CONSTRAINT motos_marcas_fk FOREIGN KEY ( cod_marca_mot )
        REFERENCES marcas ( cod_mar );

ALTER TABLE ordenes_trabajo
    ADD CONSTRAINT ordenes_trabajo_estados_ot_fk FOREIGN KEY ( cod_ot_est_ot )
        REFERENCES ot_estados ( cod_ot_est );

ALTER TABLE ordenes_trabajo
    ADD CONSTRAINT ordenes_trabajo_motos_fk FOREIGN KEY ( placa_mot_ot )
        REFERENCES motos ( placa_mot );

ALTER TABLE ordenes_trabajo
    ADD CONSTRAINT ordenes_trabajo_usuario_fk FOREIGN KEY ( documento_usu_rp_ot )
        REFERENCES usuarios ( documento_usu );

ALTER TABLE ordenes_trabajo
    ADD CONSTRAINT ordenes_trabajo_usuario_fkv2 FOREIGN KEY ( documento_usu_mc_ot )
        REFERENCES usuarios ( documento_usu );

ALTER TABLE perfiles
    ADD CONSTRAINT perfiles_estados_fk FOREIGN KEY ( cod_est_prf )
        REFERENCES estados ( cod_est );

ALTER TABLE perfiles_permisos
    ADD CONSTRAINT perfiles_permisos_estados_fk FOREIGN KEY ( cod_est_pp )
        REFERENCES estados ( cod_est );

ALTER TABLE perfiles_permisos
    ADD CONSTRAINT perfiles_permisos_perfiles_fk
        FOREIGN KEY ( cod_prf_pp,
                      cod_rol_prf_pp )
            REFERENCES perfiles ( cod_prf,
                                  cod_rol_prf );

ALTER TABLE perfiles_permisos
    ADD CONSTRAINT perfiles_permisos_permisos_fk FOREIGN KEY ( cod_prm_pp )
        REFERENCES permisos ( cod_prm );

ALTER TABLE perfiles
    ADD CONSTRAINT perfiles_roles_fk FOREIGN KEY ( cod_rol_prf )
        REFERENCES roles ( cod_rol );

ALTER TABLE permisos
    ADD CONSTRAINT permisos_vistas_fk FOREIGN KEY ( ruta_vis_prm )
        REFERENCES vistas ( ruta_vis );

ALTER TABLE productos_impuestos
    ADD CONSTRAINT productos_impuestos_impuestos_fk FOREIGN KEY ( cod_imp_pro_imp )
        REFERENCES impuestos ( cod_imp );

ALTER TABLE productos_impuestos
    ADD CONSTRAINT productos_impuestos_productos_fk FOREIGN KEY ( cod_pro_pro_imp )
        REFERENCES productos ( cod_pro );

ALTER TABLE reclamos
    ADD CONSTRAINT reclamos_ordenes_trabajo_fk FOREIGN KEY ( consecutivo_ot_rec )
        REFERENCES ordenes_trabajo ( consecutivo_ot );

ALTER TABLE usuarios
    ADD CONSTRAINT usuario_estados_fk FOREIGN KEY ( cod_est_usu )
        REFERENCES estados ( cod_est );

ALTER TABLE usuarios
    ADD CONSTRAINT usuario_perfiles_fk
        FOREIGN KEY ( cod_prf_usu,
                      cod_rol_prf_usu )
            REFERENCES perfiles ( cod_prf,
                                  cod_rol_prf );


ALTER TABLE clientes ADD CONSTRAINT nn_cli_doc CHECK (documento_cli IS NOT NULL);
ALTER TABLE clientes ADD CONSTRAINT nn_cli_nom CHECK (nombre_cli IS NOT NULL);
ALTER TABLE clientes ADD CONSTRAINT nn_cli_ap1 CHECK (apellido_1_cli IS NOT NULL);
ALTER TABLE clientes ADD CONSTRAINT nn_cli_tel CHECK (telefono_cli IS NOT NULL);
ALTER TABLE clientes ADD CONSTRAINT nn_cli_cor CHECK (correo_cli IS NOT NULL);

ALTER TABLE detalle_orden_trabajo ADD CONSTRAINT nn_deto_con CHECK (consecutivo_ot_deto IS NOT NULL);
ALTER TABLE detalle_orden_trabajo ADD CONSTRAINT nn_deto_cod CHECK (cod_pro_deto IS NOT NULL);
ALTER TABLE detalle_orden_trabajo ADD CONSTRAINT nn_deto_val CHECK (valor_unitario_deto IS NOT NULL);
ALTER TABLE detalle_orden_trabajo ADD CONSTRAINT nn_deto_can CHECK (cantidad_deto IS NOT NULL);
ALTER TABLE detalle_orden_trabajo ADD CONSTRAINT nn_deto_usu CHECK (documento_usu_deto IS NOT NULL);

ALTER TABLE estados ADD CONSTRAINT nn_est_cod CHECK (cod_est IS NOT NULL);
ALTER TABLE estados ADD CONSTRAINT nn_est_nom CHECK (nombre_est IS NOT NULL);

ALTER TABLE excepciones ADD CONSTRAINT nn_exc_cod CHECK (cod_exc IS NOT NULL);
ALTER TABLE excepciones ADD CONSTRAINT nn_exc_nom CHECK (nombre_exc IS NOT NULL);
ALTER TABLE excepciones ADD CONSTRAINT nn_exc_desc CHECK (descripcion_exp IS NOT NULL);

ALTER TABLE impuestos ADD CONSTRAINT nn_imp_cod CHECK (cod_imp IS NOT NULL);
ALTER TABLE impuestos ADD CONSTRAINT nn_imp_nom CHECK (nombre_imp IS NOT NULL);
ALTER TABLE impuestos ADD CONSTRAINT nn_imp_por CHECK (porcentaje_imp IS NOT NULL);

ALTER TABLE marcas ADD CONSTRAINT nn_mar_cod CHECK (cod_mar IS NOT NULL);
ALTER TABLE marcas ADD CONSTRAINT nn_mar_nom CHECK (nombre_mar IS NOT NULL);

ALTER TABLE motos ADD CONSTRAINT nn_mot_plac CHECK (placa_mot IS NOT NULL);
ALTER TABLE motos ADD CONSTRAINT nn_mot_mod CHECK (modelo_mot IS NOT NULL);
ALTER TABLE motos ADD CONSTRAINT nn_mot_col CHECK (color_mot IS NOT NULL);
ALTER TABLE motos ADD CONSTRAINT nn_mot_cil CHECK (cilindraje_mot IS NOT NULL);
ALTER TABLE motos ADD CONSTRAINT nn_mot_doc CHECK (documento_cli_mot IS NOT NULL);
ALTER TABLE motos ADD CONSTRAINT nn_mot_mar CHECK (cod_marca_mot IS NOT NULL);

ALTER TABLE ordenes_trabajo ADD CONSTRAINT nn_ot_con CHECK (consecutivo_ot IS NOT NULL);
ALTER TABLE ordenes_trabajo ADD CONSTRAINT nn_ot_fec CHECK (fecha_elaboracion_ot IS NOT NULL);
ALTER TABLE ordenes_trabajo ADD CONSTRAINT nn_ot_km CHECK (kilometraje_ingreso_ot IS NOT NULL);
ALTER TABLE ordenes_trabajo ADD CONSTRAINT nn_ot_plac CHECK (placa_mot_ot IS NOT NULL);
ALTER TABLE ordenes_trabajo ADD CONSTRAINT nn_ot_usrrp CHECK (documento_usu_rp_ot IS NOT NULL);
ALTER TABLE ordenes_trabajo ADD CONSTRAINT nn_ot_usrmc CHECK (documento_usu_mc_ot IS NOT NULL);
ALTER TABLE ordenes_trabajo ADD CONSTRAINT nn_ot_est CHECK (cod_ot_est_ot IS NOT NULL);

ALTER TABLE ot_estados ADD CONSTRAINT nn_otest_cod CHECK (cod_ot_est IS NOT NULL);
ALTER TABLE ot_estados ADD CONSTRAINT nn_otest_nom CHECK (nombre_ot_est IS NOT NULL);

ALTER TABLE perfiles ADD CONSTRAINT nn_per_cod CHECK (cod_prf IS NOT NULL);
ALTER TABLE perfiles ADD CONSTRAINT nn_per_nom CHECK (nombre_prf IS NOT NULL);
ALTER TABLE perfiles ADD CONSTRAINT nn_per_des CHECK (descripcion_prf IS NOT NULL);
ALTER TABLE perfiles ADD CONSTRAINT nn_per_est CHECK (cod_est_prf IS NOT NULL);
ALTER TABLE perfiles ADD CONSTRAINT nn_per_rol CHECK (cod_rol_prf IS NOT NULL);

ALTER TABLE perfiles_permisos ADD CONSTRAINT nn_pp_prm CHECK (cod_prm_pp IS NOT NULL);
ALTER TABLE perfiles_permisos ADD CONSTRAINT nn_pp_prf CHECK (cod_prf_pp IS NOT NULL);
ALTER TABLE perfiles_permisos ADD CONSTRAINT nn_pp_rol CHECK (cod_rol_prf_pp IS NOT NULL);
ALTER TABLE perfiles_permisos ADD CONSTRAINT nn_pp_est CHECK (cod_est_pp IS NOT NULL);

ALTER TABLE permisos ADD CONSTRAINT nn_prm_cod CHECK (cod_prm IS NOT NULL);
ALTER TABLE permisos ADD CONSTRAINT nn_prm_nom CHECK (nombre_prm IS NOT NULL);
ALTER TABLE permisos ADD CONSTRAINT nn_prm_des CHECK (descripcion_prm IS NOT NULL);
ALTER TABLE permisos ADD CONSTRAINT nn_prm_rut CHECK (ruta_vis_prm IS NOT NULL);

ALTER TABLE productos ADD CONSTRAINT nn_pro_cod CHECK (cod_pro IS NOT NULL);
ALTER TABLE productos ADD CONSTRAINT nn_pro_nom CHECK (nombre_pro IS NOT NULL);
ALTER TABLE productos ADD CONSTRAINT nn_pro_des CHECK (descripcion_pro IS NOT NULL);
ALTER TABLE productos ADD CONSTRAINT nn_pro_stk CHECK (stock_pro IS NOT NULL);
ALTER TABLE productos ADD CONSTRAINT nn_pro_stkm CHECK (stock_pro_min IS NOT NULL);
ALTER TABLE productos ADD CONSTRAINT nn_pro_est CHECK (cod_est_pro IS NOT NULL);
ALTER TABLE productos ADD CONSTRAINT nn_pro_pre CHECK (precio_pro IS NOT NULL);

ALTER TABLE productos_impuestos ADD CONSTRAINT nn_pimp_cod CHECK (cod_pro_imp IS NOT NULL);
ALTER TABLE productos_impuestos ADD CONSTRAINT nn_pimp_cimp CHECK (cod_imp_pro_imp IS NOT NULL);
ALTER TABLE productos_impuestos ADD CONSTRAINT nn_pimp_cpro CHECK (cod_pro_pro_imp IS NOT NULL);
ALTER TABLE productos_impuestos ADD CONSTRAINT nn_pimp_por CHECK (porcentaje_pro_imp IS NOT NULL);

ALTER TABLE reclamos ADD CONSTRAINT nn_rec_cod CHECK (cod_rec IS NOT NULL);
ALTER TABLE reclamos ADD CONSTRAINT nn_rec_des CHECK (descripcion_rec IS NOT NULL);
ALTER TABLE reclamos ADD CONSTRAINT nn_rec_ot CHECK (consecutivo_ot_rec IS NOT NULL);

ALTER TABLE roles ADD CONSTRAINT nn_rol_cod CHECK (cod_rol IS NOT NULL);
ALTER TABLE roles ADD CONSTRAINT nn_rol_nom CHECK (nombre_rol IS NOT NULL);
ALTER TABLE roles ADD CONSTRAINT nn_rol_des CHECK (descripcion_rol IS NOT NULL);

ALTER TABLE usuarios ADD CONSTRAINT nn_usu_doc CHECK (documento_usu IS NOT NULL);
ALTER TABLE usuarios ADD CONSTRAINT nn_usu_nom CHECK (nombre_usu IS NOT NULL);
ALTER TABLE usuarios ADD CONSTRAINT nn_usu_ap1 CHECK (apellido_1_usu IS NOT NULL);
ALTER TABLE usuarios ADD CONSTRAINT nn_usu_cor CHECK (correo_usu IS NOT NULL);
ALTER TABLE usuarios ADD CONSTRAINT nn_usu_con CHECK (contrasena_usu IS NOT NULL);
ALTER TABLE usuarios ADD CONSTRAINT nn_usu_tip CHECK (cod_tipo_usu IS NOT NULL);
ALTER TABLE usuarios ADD CONSTRAINT nn_usu_est CHECK (cod_est_usu IS NOT NULL);
ALTER TABLE usuarios ADD CONSTRAINT nn_usu_sub CHECK (sub_id_usu IS NOT NULL);
ALTER TABLE usuarios ADD CONSTRAINT nn_usu_prf CHECK (cod_prf_usu IS NOT NULL);
ALTER TABLE usuarios ADD CONSTRAINT nn_usu_rl CHECK (cod_rol_prf_usu IS NOT NULL);

ALTER TABLE vistas ADD CONSTRAINT nn_vis_rut CHECK (ruta_vis IS NOT NULL);
ALTER TABLE vistas ADD CONSTRAINT nn_vis_nom CHECK (nombre_vis IS NOT NULL);
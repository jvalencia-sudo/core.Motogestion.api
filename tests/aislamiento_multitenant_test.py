"""Tests de aislamiento multi-tenant end-to-end: endpoint -> servicio -> repositorio
-> _apply_tenant -> RLS real de Postgres. Usan TestClient contra la app real (ver
tests/conftest.py) con Auth0 mockeado a nivel de Auth0Provider.verify, pero dejando
correr de verdad la resolución de tenant, el usuario y el chequeo de suscripción.

Requieren Postgres real con la BD dedicada de test (ver tests/conftest.py) — corren
con `docker compose up -d` local o el servicio postgres de CI.
"""
import psycopg
import pytest

from tests.conftest import TALLER_A, TALLER_B, _dsn, auth_headers

# mock_auth0 no es autouse (ver conftest.py): este archivo entero lo necesita porque
# todas sus clases hacen requests HTTP simuladas con tokens de prueba.
pytestmark = [pytest.mark.db, pytest.mark.usefixtures("mock_auth0")]


class TestControl:
    """Si esto falla, cualquier 404 de abajo puede venir de un override de auth mal
    hecho y no de que el RLS esté funcionando — se corre primero por diseño."""

    def test_taller_a_ve_su_propio_cliente(self, client, seed_talleres):
        seed = seed_talleres[TALLER_A]
        r = client.get(f"/api/clientes/{seed.documento_cliente}", headers=auth_headers(TALLER_A))
        assert r.status_code == 200


class TestAislamientoClientes:
    def test_no_puede_leer_cliente_de_otro_taller(self, client, seed_talleres):
        ajeno = seed_talleres[TALLER_B].documento_cliente
        r = client.get(f"/api/clientes/{ajeno}", headers=auth_headers(TALLER_A))
        assert r.status_code == 404

    def test_no_puede_editar_cliente_de_otro_taller(self, client, seed_talleres):
        ajeno = seed_talleres[TALLER_B].documento_cliente
        r = client.put(
            f"/api/clientes/{ajeno}", json={"nombre_cli": "Hackeado"}, headers=auth_headers(TALLER_A)
        )
        assert r.status_code == 404

    def test_no_puede_eliminar_cliente_de_otro_taller(self, client, seed_talleres):
        ajeno = seed_talleres[TALLER_B].documento_cliente
        r = client.delete(f"/api/clientes/{ajeno}", headers=auth_headers(TALLER_A))
        assert r.status_code == 404

    def test_listado_no_incluye_clientes_de_otro_taller(self, client, seed_talleres):
        ajeno = seed_talleres[TALLER_B].documento_cliente
        r = client.get("/api/clientes", headers=auth_headers(TALLER_A))
        assert r.status_code == 200
        assert ajeno not in {c["documentoCli"] for c in r.json()}


class TestAislamientoMotos:
    def test_no_puede_leer_moto_de_otro_taller(self, client, seed_talleres):
        ajena = seed_talleres[TALLER_B].placa_moto
        r = client.get(f"/api/motos/{ajena}", headers=auth_headers(TALLER_A))
        assert r.status_code == 404

    def test_no_puede_editar_moto_de_otro_taller(self, client, seed_talleres):
        ajena = seed_talleres[TALLER_B].placa_moto
        r = client.put(f"/api/motos/{ajena}", json={"color_mot": "Rojo"}, headers=auth_headers(TALLER_A))
        assert r.status_code == 404

    def test_no_puede_eliminar_moto_de_otro_taller(self, client, seed_talleres):
        ajena = seed_talleres[TALLER_B].placa_moto
        r = client.delete(f"/api/motos/{ajena}", headers=auth_headers(TALLER_A))
        assert r.status_code == 404

    def test_listado_no_incluye_motos_de_otro_taller(self, client, seed_talleres):
        ajena = seed_talleres[TALLER_B].placa_moto
        r = client.get("/api/motos", headers=auth_headers(TALLER_A))
        assert r.status_code == 200
        assert ajena not in {m["placaMot"] for m in r.json()}


class TestAislamientoProductos:
    def test_no_puede_leer_producto_de_otro_taller(self, client, seed_talleres):
        ajeno = seed_talleres[TALLER_B].cod_producto
        r = client.get(f"/api/productos/{ajeno}", headers=auth_headers(TALLER_A))
        assert r.status_code == 404

    def test_no_puede_editar_producto_de_otro_taller(self, client, seed_talleres):
        ajeno = seed_talleres[TALLER_B].cod_producto
        r = client.put(
            f"/api/productos/{ajeno}", json={"nombre_pro": "Hackeado"}, headers=auth_headers(TALLER_A)
        )
        assert r.status_code == 404

    def test_no_puede_eliminar_producto_de_otro_taller(self, client, seed_talleres):
        ajeno = seed_talleres[TALLER_B].cod_producto
        r = client.delete(f"/api/productos/{ajeno}", headers=auth_headers(TALLER_A))
        assert r.status_code == 404

    def test_listado_no_incluye_productos_de_otro_taller(self, client, seed_talleres):
        ajeno = seed_talleres[TALLER_B].cod_producto
        r = client.get("/api/productos", headers=auth_headers(TALLER_A))
        assert r.status_code == 200
        assert ajeno not in {p["codPro"] for p in r.json()}


class TestAislamientoMarcas:
    def test_no_puede_leer_marca_de_otro_taller(self, client, seed_talleres):
        ajena = seed_talleres[TALLER_B].cod_marca
        r = client.get(f"/api/marcas/{ajena}", headers=auth_headers(TALLER_A))
        assert r.status_code == 404

    def test_no_puede_editar_marca_de_otro_taller(self, client, seed_talleres):
        ajena = seed_talleres[TALLER_B].cod_marca
        r = client.put(f"/api/marcas/{ajena}", json={"nombre_mar": "Hackeada"}, headers=auth_headers(TALLER_A))
        assert r.status_code == 404

    def test_no_puede_eliminar_marca_de_otro_taller(self, client, seed_talleres):
        ajena = seed_talleres[TALLER_B].cod_marca
        r = client.delete(f"/api/marcas/{ajena}", headers=auth_headers(TALLER_A))
        assert r.status_code == 404

    def test_listado_no_incluye_marcas_de_otro_taller(self, client, seed_talleres):
        ajena = seed_talleres[TALLER_B].cod_marca
        r = client.get("/api/marcas", headers=auth_headers(TALLER_A))
        assert r.status_code == 200
        assert ajena not in {m["codMar"] for m in r.json()}


class TestAislamientoReclamos:
    def test_no_puede_leer_reclamo_de_otro_taller(self, client, seed_talleres):
        ajeno = seed_talleres[TALLER_B].cod_reclamo
        r = client.get(f"/api/reclamos/{ajeno}", headers=auth_headers(TALLER_A))
        assert r.status_code == 404

    def test_no_puede_editar_reclamo_de_otro_taller(self, client, seed_talleres):
        ajeno = seed_talleres[TALLER_B].cod_reclamo
        r = client.put(
            f"/api/reclamos/{ajeno}", json={"descripcion_rec": "Hackeado"}, headers=auth_headers(TALLER_A)
        )
        assert r.status_code == 404

    def test_no_puede_eliminar_reclamo_de_otro_taller(self, client, seed_talleres):
        ajeno = seed_talleres[TALLER_B].cod_reclamo
        r = client.delete(f"/api/reclamos/{ajeno}", headers=auth_headers(TALLER_A))
        assert r.status_code == 404

    def test_listado_no_incluye_reclamos_de_otro_taller(self, client, seed_talleres):
        ajeno = seed_talleres[TALLER_B].cod_reclamo
        r = client.get("/api/reclamos", headers=auth_headers(TALLER_A))
        assert r.status_code == 200
        assert ajeno not in {rc["codRec"] for rc in r.json()}


class TestAislamientoOrdenesTrabajo:
    """Los dos talleres tienen consecutivo_ot DISTINTOS (ver conftest), así que un
    404 acá confirma aislamiento real y no una simple colisión de IDs."""

    def test_no_puede_leer_orden_de_otro_taller(self, client, seed_talleres):
        ajena = seed_talleres[TALLER_B].consecutivo_ot
        r = client.get(f"/api/ordenes-trabajo/{ajena}", headers=auth_headers(TALLER_A))
        assert r.status_code == 404

    def test_no_puede_editar_orden_de_otro_taller(self, client, seed_talleres):
        ajena = seed_talleres[TALLER_B].consecutivo_ot
        r = client.put(
            f"/api/ordenes-trabajo/{ajena}",
            json={"observacion_ot": "Hackeada"},
            headers=auth_headers(TALLER_A),
        )
        assert r.status_code == 404

    def test_no_puede_eliminar_producto_de_orden_de_otro_taller(self, client, seed_talleres):
        """No existe DELETE de la orden completa: el único DELETE real es a nivel de
        producto/ítem de la orden."""
        seed_b = seed_talleres[TALLER_B]
        r = client.delete(
            f"/api/ordenes-trabajo/{seed_b.consecutivo_ot}/productos/{seed_b.cod_producto}",
            headers=auth_headers(TALLER_A),
        )
        assert r.status_code == 404

    def test_listado_no_incluye_ordenes_de_otro_taller(self, client, seed_talleres):
        ajena = seed_talleres[TALLER_B].consecutivo_ot
        r = client.get("/api/ordenes-trabajo", headers=auth_headers(TALLER_A))
        assert r.status_code == 200
        assert ajena not in {o["consecutivoOt"] for o in r.json()}


class TestAislamientoInventario:
    """Sin PUT/DELETE expuestos (ver auditoría F0-02): solo se prueba lectura."""

    def test_movimientos_no_incluye_los_de_otro_taller(self, client, seed_talleres):
        ajeno = seed_talleres[TALLER_B].cod_movimiento
        r = client.get("/api/inventario/movimientos", headers=auth_headers(TALLER_A))
        assert r.status_code == 200
        assert ajeno not in {m["codMov"] for m in r.json()}

    def test_stock_no_incluye_productos_de_otro_taller(self, client, seed_talleres):
        ajeno = seed_talleres[TALLER_B].cod_producto
        r = client.get("/api/inventario/productos", headers=auth_headers(TALLER_A))
        assert r.status_code == 200
        assert ajeno not in {p["codPro"] for p in r.json()}


class TestAislamientoTablero:
    def test_no_puede_cambiar_estado_de_orden_de_otro_taller(self, client, seed_talleres):
        ajena = seed_talleres[TALLER_B].consecutivo_ot
        r = client.put(
            f"/api/tablero/{ajena}/estado",
            json={"cod_estado": 2},
            headers=auth_headers(TALLER_A),
        )
        assert r.status_code == 404

    def test_resumen_no_revienta_y_responde_200(self, client, seed_talleres):
        r = client.get("/api/tablero", headers=auth_headers(TALLER_A))
        assert r.status_code == 200


class TestExcepcionesRLS:
    """pagos, talleres y usuarios_identidad NO tienen RLS (ver
    infrastructure/utils/rls_policy.py): aquí la única barrera es código de
    aplicación, no Postgres — el hueco más importante a probar."""

    def test_pagos_no_devuelve_los_de_otro_taller(self, client, seed_talleres):
        # /suscripciones/pagos devuelve un dict crudo (columnas en MAYÚSCULAS, sin el
        # contrato camelCase habitual) — ver PagoRepositorio.listar_por_taller.
        cod_pago_ajeno = seed_talleres[TALLER_B].cod_pago
        r = client.get("/api/suscripciones/pagos", headers=auth_headers(TALLER_A))
        assert r.status_code == 200
        assert cod_pago_ajeno not in {p["COD_PAGO"] for p in r.json()}

    def test_config_devuelve_la_del_propio_taller_no_la_ajena(self, client, seed_talleres):
        """/talleres/config toma el taller del token, no de un path param (talleres
        no tiene RLS). tarifa_hora_pred = cod_taller en el seed, así que un valor
        cruzado confirmaría que se coló la config de otro taller."""
        r = client.get("/api/talleres/config", headers=auth_headers(TALLER_A))
        assert r.status_code == 200
        assert r.json()["tarifaHoraPred"] == TALLER_A

    def test_usuario_normal_no_puede_leer_taller_ajeno(self, client, seed_talleres):
        r = client.get(f"/api/talleres/{TALLER_B}", headers=auth_headers(TALLER_A))
        assert r.status_code == 403

    def test_usuario_normal_no_puede_editar_taller_ajeno(self, client, seed_talleres):
        r = client.put(
            f"/api/talleres/{TALLER_B}",
            json={"nombre_tal": "Hackeado"},
            headers=auth_headers(TALLER_A),
        )
        assert r.status_code == 403

    def test_usuarios_identidad_no_se_expone_por_ningun_endpoint(self):
        """Es de solo lectura interna (solo la usa resolve_tenant); no debería
        aparecer en ningún path de la API."""
        from api import api_router

        rutas = " ".join(route.path for route in api_router.routes)
        assert "usuarios_identidad" not in rutas


class TestEscrituraCruzada:
    """No basta con que el USING de la policy oculte filas ajenas en lectura: el
    WITH CHECK debe rechazar también el intento de escribir/mover una fila hacia
    otro taller. Se prueba a nivel de BD directamente, con una conexión propia para
    no dejar el app.tenant_id de la sesión compartida en un estado raro."""

    @pytest.fixture
    def conn_propia(self):
        conn = psycopg.connect(
            _dsn(),
            autocommit=True,
        )
        yield conn
        conn.close()

    def test_insert_no_puede_declarar_taller_ajeno(self, conn_propia, seed_talleres):
        with conn_propia.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cur.execute(
                    "INSERT INTO clientes (cod_taller, documento_cli, nombre_cli, "
                    "apellido_1_cli, telefono_cli) VALUES (%s, '99999999', 'Fuga', 'Test', '3000000000')",
                    (TALLER_B,),
                )

    def test_update_no_puede_mover_fila_a_otro_taller(self, conn_propia, seed_talleres):
        documento = seed_talleres[TALLER_A].documento_cliente
        with conn_propia.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cur.execute(
                    "UPDATE clientes SET cod_taller = %s WHERE documento_cli = %s",
                    (TALLER_B, documento),
                )

"""Tests de regresión sobre el catálogo de sistema de Postgres: confirman que el RLS
multi-tenant sigue cubriendo lo que debería cubrir, sin depender de que alguien se
acuerde de revisarlo a mano cada vez que se agrega una tabla o vista nueva.

Son de solo lectura sobre catálogos del sistema (no escriben datos), pero corren
contra la BD DEDICADA de test igual que el resto de tests/ — tests/conftest.py
sobrescribe DB_NAME a motogestion_test antes de que este archivo importe `config`.
"""
import pytest

from infrastructure.utils.rls_policy import EXCEPCIONES_RLS
from tests.conftest import _dsn, conectar_o_fallar

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def conn():
    with conectar_o_fallar(_dsn()) as connection:
        yield connection


def test_toda_tabla_con_cod_taller_tiene_rls_forzado(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relkind = 'r'
              AND EXISTS (
                  SELECT 1 FROM information_schema.columns
                  WHERE table_schema = 'public'
                    AND table_name = c.relname
                    AND column_name = 'cod_taller'
              )
              AND NOT (c.relrowsecurity AND c.relforcerowsecurity)
            """
        )
        tablas_sin_rls = {row[0] for row in cur.fetchall()}

    sin_documentar = tablas_sin_rls - EXCEPCIONES_RLS.keys()
    assert not sin_documentar, (
        f"Tablas con cod_taller sin RLS forzado y sin excepción documentada en "
        f"infrastructure/utils/rls_policy.py: {sin_documentar}"
    )


def test_toda_vista_vw_tiene_security_invoker(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.relname, c.reloptions
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'v' AND c.relname LIKE 'vw\\_%'
            """
        )
        vistas = cur.fetchall()

    assert vistas, "No se encontraron vistas vw_* — revisa que el esquema esté cargado"

    def _tiene_security_invoker(reloptions):
        # Postgres guarda el valor literal con el que se declaró (on/true/yes/1...);
        # el esquema de este repo usa "on" en todos lados.
        return reloptions and any(
            opt in ("security_invoker=on", "security_invoker=true")
            for opt in reloptions
        )

    sin_security_invoker = [
        nombre for nombre, reloptions in vistas if not _tiene_security_invoker(reloptions)
    ]
    assert not sin_security_invoker, (
        f"Vistas sin security_invoker habilitado (heredan permisos del dueño en vez "
        f"del invocador): {sin_security_invoker}"
    )


def test_toda_tabla_con_rls_tiene_policy_completa(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relrowsecurity
            """
        )
        tablas_con_rls = {row[0] for row in cur.fetchall()}

        cur.execute(
            """
            SELECT tablename
            FROM pg_policies
            WHERE schemaname = 'public'
              AND cmd = 'ALL'
              AND qual IS NOT NULL
              AND with_check IS NOT NULL
            """
        )
        tablas_con_policy_completa = {row[0] for row in cur.fetchall()}

    incompletas = tablas_con_rls - tablas_con_policy_completa
    assert not incompletas, (
        f"Tablas con RLS habilitado pero sin policy FOR ALL con USING+WITH CHECK "
        f"completos: {incompletas}"
    )


def test_ninguna_funcion_security_definer_es_de_un_superusuario(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.proname, r.rolname
            FROM pg_proc p
            JOIN pg_roles r ON r.oid = p.proowner
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'public' AND p.prosecdef AND r.rolsuper
            """
        )
        riesgosas = cur.fetchall()

    assert not riesgosas, (
        f"Funciones SECURITY DEFINER propiedad de un superusuario (se saltan el RLS "
        f"al correr con los privilegios del dueño): {riesgosas}"
    )

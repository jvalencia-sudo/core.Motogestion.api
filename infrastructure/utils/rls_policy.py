"""Excepciones documentadas al RLS multi-tenant: tablas con columna cod_taller que a
propósito NO tienen Row Level Security. Fuente única de verdad citada tanto por
tests/rls_coverage_test.py (falla si aparece una tabla nueva sin RLS y sin excepción
documentada aquí) como por el README."""

EXCEPCIONES_RLS = {
    "pagos": "billing de plataforma; el webhook de Wompi llega sin sesión",
    "usuarios_identidad": "resuelve el tenant antes de poder fijar app.tenant_id",
    "talleres": "raíz del tenant; protegida por require_super_admin, no por RLS",
}

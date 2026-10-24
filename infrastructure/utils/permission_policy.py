"""Excepciones documentadas al gateo de permisos (F0-11): rutas no-GET del API que a
propósito NO llevan require_permiso/require_admin/require_super_admin. Fuente única
de verdad citada por tests/permisos_coverage_test.py (falla si aparece una ruta
nueva sin gateo y sin excepción documentada acá) y por el README.

Clave: "MÉTODO /ruta" tal como aparece en api_router.routes (incluye el prefijo del
sub-router, no el prefijo global settings.api_url)."""

EXCEPCIONES_PERMISOS = {
    "POST /auth/login": "público; es el propio flujo de login (aún no hay token)",
    "POST /talleres": "público; registro de un taller nuevo desde la landing",
    "POST /public/wompi/webhook": "público; validado por firma del evento de Wompi, no por sesión",
    "GET /public/ordenes-trabajo/estado/{token}": "público (F2-01); la identidad la da el UUID impredecible del token, no una sesión",
    "PATCH /public/ordenes-trabajo/{token}/aprobar": "público (F2-03); la identidad la da el UUID impredecible del token, no una sesión; rate limit aparte (ver infrastructure/utils/rate_limiter.py)",
}

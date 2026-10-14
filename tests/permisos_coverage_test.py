"""F0-11: el backend no validaba permisos en casi ningún endpoint (AuthRequest
existía pero estaba comentado en todos lados). Este test recorre app_router.routes
igual que tests/aislamiento_multitenant_test.py ya hace puntualmente en
test_usuarios_identidad_no_se_expone_por_ningun_endpoint, y falla si una ruta que no
sea GET no declara require_permiso/require_admin/require_super_admin, ni está en la
lista de excepciones documentadas de permission_policy.py -- así una ruta nueva sin
gateo no puede colarse en silencio."""
from fastapi.routing import APIRoute

from api import api_router
from infrastructure.utils.permission_policy import EXCEPCIONES_PERMISOS

_GATEADAS = {"require_admin", "require_super_admin"}


def _tiene_guardia(route: APIRoute) -> bool:
    for dep in route.dependant.dependencies:
        nombre = getattr(dep.call, "__qualname__", "")
        if nombre in _GATEADAS or nombre.startswith("require_permiso.<locals>"):
            return True
    return False


def test_toda_ruta_no_get_exige_permiso_o_esta_documentada():
    sin_gateo = []

    for route in api_router.routes:
        if not isinstance(route, APIRoute):
            continue
        metodos = route.methods - {"HEAD", "OPTIONS"}
        if metodos <= {"GET"}:
            continue
        if _tiene_guardia(route):
            continue
        for metodo in metodos:
            clave = f"{metodo} {route.path}"
            if clave not in EXCEPCIONES_PERMISOS:
                sin_gateo.append(clave)

    assert not sin_gateo, (
        "Rutas no-GET sin require_permiso/require_admin/require_super_admin y sin "
        f"excepción documentada en infrastructure/utils/permission_policy.py: {sorted(sin_gateo)}"
    )


def test_las_excepciones_documentadas_siguen_existiendo():
    """Si una excepción documentada deja de corresponder a una ruta real (se borró o
    cambió de path/método), permission_policy.py queda con basura que nadie revisa:
    mejor que el test lo note."""
    rutas_reales = set()
    for route in api_router.routes:
        if not isinstance(route, APIRoute):
            continue
        for metodo in route.methods - {"HEAD", "OPTIONS"}:
            rutas_reales.add(f"{metodo} {route.path}")

    obsoletas = set(EXCEPCIONES_PERMISOS) - rutas_reales
    assert not obsoletas, f"Excepciones documentadas que ya no existen como ruta: {obsoletas}"

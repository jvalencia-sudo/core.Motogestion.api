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


def _tiene_guardia_super_admin(route: APIRoute) -> bool:
    """A diferencia de _tiene_guardia (que acepta require_admin o
    require_super_admin), esta exige específicamente require_super_admin --
    require_admin es "Admin de SU taller", no "super-admin de la plataforma".
    Si el router de /superadmin se gateara con require_admin por error, las
    rutas seguirían "teniendo guardia" para _tiene_guardia (el test de arriba
    no fallaría) pero CUALQUIER Admin de taller vería datos de todos los
    talleres -- por eso este check específico."""
    for dep in route.dependant.dependencies:
        if getattr(dep.call, "__qualname__", "") == "require_super_admin":
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


def test_toda_ruta_get_de_superadmin_exige_require_super_admin():
    """F0-14 corrección 7: el test de arriba salta TODA ruta cuyo único método
    sea GET (por diseño -- no es su alcance). Las GET de /api/superadmin
    (ej. detalle de taller: correo/teléfono del dueño) sí están protegidas hoy
    -- vía `dependencies=_super_admin` a nivel de router en api/__init__.py,
    que FastAPI mezcla en el `dependant` de cada ruta -- pero nada lo verificaba
    de forma genérica. Si alguien agrega una ruta GET nueva bajo /superadmin
    por fuera de ese router (sin ese guard), este test la atrapa."""
    rutas_get_vistas = []
    rutas_get_sin_guardia = []

    for route in api_router.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/superadmin"):
            continue
        if "GET" not in (route.methods - {"HEAD", "OPTIONS"}):
            continue
        rutas_get_vistas.append(route.path)
        if not _tiene_guardia_super_admin(route):
            rutas_get_sin_guardia.append(f"GET {route.path}")

    # Si esto da 0, el filtro de arriba está mal (ej. el prefijo cambió) y el
    # test de abajo pasaría en falso por no haber encontrado nada que revisar.
    assert rutas_get_vistas, "No se encontró ninguna ruta GET bajo /superadmin -- revisa el path del test"
    assert not rutas_get_sin_guardia, (
        f"Rutas GET de /superadmin sin require_super_admin: {sorted(rutas_get_sin_guardia)}"
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

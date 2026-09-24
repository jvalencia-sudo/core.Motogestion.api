# core.Motogestion.api

## Seguridad multi-tenant (RLS)

Cada taller solo ve sus propios datos gracias a Row-Level Security (RLS) de Postgres:
las tablas de negocio tienen columna `cod_taller` y `FORCE ROW LEVEL SECURITY` con una
policy que compara contra `current_setting('app.tenant_id')`. El tenant se resuelve del
JWT en cada request (`infrastructure/dependencies/tenant_request.py::resolve_tenant`) y
se fija en la sesión de BD antes de cada query
(`repository/data/database.py::_apply_tenant`); sin sesión válida, `app.tenant_id` cae a
`-1` (ningún taller), no a "todos los talleres".

**Esto solo funciona si el rol de BD de la app no es superusuario ni tiene
`BYPASSRLS`** — cualquiera de los dos anula el RLS por completo y de forma silenciosa.
Por eso la app verifica el rol al arrancar (`repository/data/db_pool.py::init_pool`) y
**se niega a arrancar** si detecta un rol privilegiado.

`tests/rls_coverage_test.py` corre en CI contra Postgres real y falla si: alguna tabla
nueva con `cod_taller` queda sin RLS forzado, alguna vista `vw_*` pierde
`security_invoker`, alguna policy queda incompleta (sin `USING`/`WITH CHECK` para todos
los comandos), o aparece una función `SECURITY DEFINER` propiedad de un superusuario.

### Excepciones documentadas al RLS

Tres tablas con `cod_taller` **no** llevan RLS a propósito (lista también en
`infrastructure/utils/rls_policy.py::EXCEPCIONES_RLS`, fuente única de verdad citada
por el test de cobertura):

| Tabla | Por qué no tiene RLS | Cómo se aísla en su lugar |
|---|---|---|
| `pagos` | Billing de plataforma; el webhook de Wompi llega sin sesión de usuario y debe poder resolver el pago por su referencia. | Filtro explícito `WHERE cod_taller = :1` en `PagoRepositorio`, usando el taller del usuario autenticado (`require_admin`). |
| `usuarios_identidad` | Resuelve el taller del usuario a partir del `sub` de Auth0 **antes** de poder fijar `app.tenant_id` — es el mecanismo que hace posible el resto del RLS. | Es de solo lectura interna; ningún endpoint la expone directamente. |
| `talleres` | Es la raíz del tenant (no tiene un tenant "padre" contra el cual aislarse). | Los endpoints que reciben `cod_taller` como parámetro (`GET`/`PUT /talleres/{cod_taller}`) están protegidos con `require_super_admin`, no con RLS. |

El aislamiento a nivel de aplicación de estas tres excepciones se prueba en
`tests/aislamiento_multitenant_test.py`.

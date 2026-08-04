# ERP Panadería
## Historial de Auditoría Técnica

### Versión Base
- ERP recibido para auditoría: `core_erp` (proyecto FastAPI + frontend HTML, sin versión previa de auditoría).
- Estado inicial: sin correcciones aplicadas.
- Hallazgos pendientes al inicio:
  - N°1 — Valorización incorrecta del inventario de producto terminado.
  - N°2 — Rentabilidad por tienda usando costo estándar en lugar de costo real.
  - N°3 — Permiso de escritura de mermas mal asignado (usa `inventario.leer`).
  - N°4 — README desactualizado respecto a routers implementados.
  - N°5 — Las ventas no generan movimientos de inventario/kardex.

---

## ERP_Panaderia_Auditoria_Correccion_Hallazgo01_v1.zip

**Fecha:** 2026-08-03

**Hallazgo corregido:** N°1 – Valorización incorrecta del inventario de producto terminado.

**Resumen técnico:**
El lote de producto terminado ingresaba al inventario (estado EMPAQUE) valorizado
únicamente con `costo_insumos_real`, sin considerar mano de obra ni CIF. Se corrigió
para que ingrese valorizado con el costo real completo (insumos + mano de obra 15 %
+ CIF 10 %), reutilizando las constantes `LABOR_PCT` / `CIF_PCT` ya existentes en el
módulo — no se creó ningún método de cálculo nuevo.

**Archivos modificados:**
- `app/services/produccion_service.py`

**Pruebas ejecutadas:**
- Producción de "Torta de Chocolate" (9 de 10 unidades solicitadas):
  `costo_insumos_real` = S/ 30.10 → `costo_real_total` = S/ 37.625.
- `/api/consultas/stock` reflejó el `valor_total` del lote en S/ 37.625
  (costo unitario ≈ S/ 4.1806).
- Verificación de consistencia antes y después de `FACTURADO` (sin recálculo
  silencioso del costo ya asentado).

**Alcance respetado:** no se modificó `recetas_service.py`, `ventas_service.py`,
permisos ni frontend.

**Resultado:** ✅ Cerrado.

---

## ERP_Panaderia_Auditoria_Correccion_Hallazgo02_v2.zip

**Fecha:** 2026-08-03

**Hallazgo corregido:** N°2 – Rentabilidad por tienda usando costo real.

**Subcorrecciones:**
- Uso de costo real del lote (`inventario_service.costo_promedio()`) en vez del
  costo estándar de receta (`calcular_costo_estandar()`, que no incluía mano de
  obra ni CIF).
- Manejo explícito de `COSTO_NO_DISPONIBLE`: un producto sin costo real
  verificable ya no se interpreta como costo cero (lo que inflaba el margen a
  100 % falso); queda fuera del diccionario de costos y la fila sale con
  `costo_total_estimado` / `utilidad_real` / `margen_real_pct` en `null`.
- Separación correcta por sucursal: `rentabilidad_por_tienda()` agregaba ventas
  de **todas** las sucursales (`db.query(Venta).all()` sin filtro) aunque el
  costo sí se calculaba con el almacén de la sucursal consultada (este defecto
  fue reportado como candidato a "Hallazgo N°6" durante la validación, y se
  cerró en esta misma versión por ser el mismo código). Se agregó el filtro
  `Venta.sucursal_id == sucursal_id`, lo que requirió agregar el parámetro
  `sucursal_id` a la función y actualizar sus dos llamadores.
- Corrección del ordenamiento con valores `None`: el `sorted()` final lanzaba
  `TypeError` al comparar `utilidad_real=None` con valores numéricos; se
  corrigió con `key=lambda r: r["utilidad_real"] if ... else float("-inf")`.

**Archivos modificados:**
- `app/services/ventas_service.py`
- `app/routers/ventas.py`
- `app/services/kpi_service.py` (llamador afectado por el cambio de firma de
  `rentabilidad_por_tienda()`, necesario para no romper el dashboard ejecutivo)

**Pruebas ejecutadas:**
- Venta con stock disponible: costo usado coincide con el costo real del lote
  (S/ 4.1806/u), no con el costo estándar.
- Producto sin costo disponible: queda marcado `COSTO_NO_DISPONIBLE`, no
  asume costo cero.
- Consulta a sucursal A devuelve únicamente ventas de sucursal A; consulta a
  sucursal B devuelve únicamente ventas de sucursal B (validado con datos
  simulados en SQLite).

**Resultado:** ✅ Cerrado.

---

## ERP_Panaderia_Auditoria_Correccion_Hallazgo03_v1.zip

**Fecha:** 2026-08-04

**Hallazgo corregido:** N°3 – Permisos de registro de mermas.

**Diagnóstico:** `POST /api/mermas` exigía el permiso `inventario.leer` (solo
lectura) para una operación que descuenta stock real vía consumo FEFO y genera
un movimiento `SALIDA_MERMA` — cualquier usuario con acceso de solo consulta,
incluido el rol `gerencia` (documentado como "solo lectura"), podía alterar
inventario.

**Cambios:**
- Nuevo permiso: `mermas.escribir`, creado siguiendo la estructura de permisos
  existente (patrón de permiso propio por módulo, igual que `produccion.escribir`
  / `compras.escribir` / `ventas.escribir`).
- `app/routers/mermas.py`: el `POST` ahora exige `mermas.escribir` en vez de
  `inventario.leer`.

**Roles autorizados:**
- admin
- almacen
- produccion
- tienda (validado que cada tienda tiene almacén propio y aislado 1:1, y que
  `verificar_acceso_sucursal` impide que un usuario de tienda afecte el
  inventario de otra sucursal)

**Roles sin autorización:**
- gerencia
- compras
- ventas

**Pruebas de autorización ejecutadas** (simuladas contra la cadena real de
dependencias `require_permission` → `sucursal_scope` → `verificar_acceso_sucursal`):
1. Usuario `gerencia` intenta registrar merma → **403** (permiso denegado).
2. Usuario `almacen` registra merma en su sucursal → **200** (autorizado).
3. Usuario `tienda` registra merma en su propia sucursal → **200** (autorizado).
4. Usuario `tienda` intenta registrar merma en otra sucursal → **403**
   (restricción de sucursal, independiente del permiso).

**Archivos modificados:**
- `app/routers/mermas.py`
- `seed.py`

**Resultado:** ✅ Cerrado.

---

## ERP_Panaderia_Auditoria_Correccion_Hallazgo06_v1.zip

**Fecha:** 2026-08-04

**Hallazgo corregido:** N°6 – Integridad del empaquetado y estructura del proyecto.

**Diagnóstico:** El ZIP recibido (`core_erp_panader_1_2.zip`) traía el
código de `app/` movido un nivel de más, a `core_erp/bankend/app/` (nombre
no documentado en README ni en ninguna versión anterior, con typo:
"bankend" en vez de "backend"). `seed.py` y `requirements.txt` se quedaron
en la raíz, desincronizados de `app/`. Como consecuencia, ni
`python seed.py` ni `uvicorn app.main:app --reload` funcionaban ejecutados
desde la raíz del proyecto, tal como indica el README.

Comparación byte a byte contra la línea base post-Hallazgo N°3 confirmó que
`app/`, `seed.py`, `requirements.txt`, `VERSION.txt`,
`AUDITORIA_TRAZABILIDAD.md`, `README.md` y `frontend/core_erp_dashboard.html`
eran idénticos en contenido — es decir, **no hubo regresión de lógica de
negocio**; el defecto era exclusivamente de empaquetado/estructura de
carpetas.

**Decisión de arquitectura:** en vez de revertir a la estructura antigua
(`app/` en la raíz), se adoptó una arquitectura definitiva con separación
explícita `backend/` / `frontend/` / `docs/`.

**Cambios:**
- Renombrado `bankend/` → `backend/` (corrige el typo y formaliza el nombre).
- Consolidados dentro de `backend/` todos los archivos propios del backend:
  `app/` (con todos sus `models/`, `routers/`, `schemas/`, `services/` y los
  `.bak` de trazabilidad que ya traían), `seed.py`, `seed.py.bak`,
  `requirements.txt`.
- `frontend/core_erp_dashboard.html` se mantiene sin cambios y completamente
  separado de `backend/`; no depende de ninguna ruta interna del backend
  (se comunica solo por HTTP).
- Creada carpeta `docs/` para documentación de auditoría futura.
- `README.md`: agregada sección "Estructura del proyecto" y actualizados los
  comandos oficiales de instalación/arranque para ejecutarse desde
  `backend/` (`cd backend && pip install -r requirements.txt && python
  seed.py && uvicorn app.main:app --reload`). También se corrigieron las
  referencias a `app/main.py` → `backend/app/main.py` en el resto del texto.
- **No se modificó ninguna línea de código de negocio** en `app/`: el único
  cambio dentro de `backend/app/` es su nueva ubicación física.

**Pruebas ejecutadas (end-to-end, desde `backend/`):**
1. `python3 -m py_compile` sobre todos los `.py` de `backend/app/` y
   `backend/seed.py` → sin errores de sintaxis.
2. `python3 -c "import app.main"` ejecutado con `cwd = backend/` → import
   correcto, sin `ModuleNotFoundError`.
3. `python3 seed.py` ejecutado con `cwd = backend/` → `Seed OK`, crea
   usuarios, empresa, sucursales, insumos y producto con receta activa.
4. `uvicorn app.main:app --host 127.0.0.1 --port 8010` ejecutado con
   `cwd = backend/` → arranca sin errores, `GET /api/health` → `200 OK`.

**Resultado:** ✅ Cerrado.

---

## ERP_Panaderia_Auditoria_Correccion_Hallazgo04_v2.zip

**Fecha:** 2026-08-04

**Hallazgo corregido:** N°4 – README desactualizado respecto a routers implementados.

**Motivo del hallazgo:** el README.md arrastraba cifras y afirmaciones de una
fase intermedia del proyecto (Sesión 4) que quedaron obsoletas en cuanto se
incorporaron los módulos de Calidad/SPC, Inteligencia Competitiva,
Inteligencia Tributaria y Lean Captura sin actualizar el documento: seguía
anunciando **14 routers / 40 endpoints** cuando el backend real ya tenía 18
routers y 78 endpoints, y la sección "Pendiente" afirmaba que Inteligencia
Competitiva e Inteligencia Tributaria "no se construyeron", lo cual era falso
— ambos módulos existían completos en el código.

**Diagnóstico realizado:** comparación directa entre lo declarado en
README.md y el estado real de `backend/app/` (routers registrados en
`main.py`, modelos, servicios, schemas y vistas del dashboard). Se confirmó
que los cuatro módulos (Calidad, Competencia, Tributaria, Lean Captura)
tenían implementación completa (modelo + servicio + schema + router + vista
propia en `frontend/core_erp_dashboard.html`) pero cero mención en la
documentación, y que el conteo de routers/endpoints citado en el README
correspondía a una foto anterior del proyecto.

**Archivos revisados:**
- `backend/app/main.py` (registro real de routers vía `include_router`)
- `backend/app/routers/*.py` (los 18 módulos de rutas, incluidos
  `calidad.py`, `competencia.py`, `tributaria.py`, `lean_captura.py`)
- `backend/app/models/calidad.py`, `competencia.py`, `tributaria.py`,
  `lean_captura.py`
- `backend/app/services/spc_service.py`, `competencia_service.py`,
  `tributaria_service.py`, `lean_captura_service.py`
- `frontend/core_erp_dashboard.html` (vistas `view-spc`, `view-competencia`,
  `view-tributaria`, `view-lean-captura`)
- `README.md` (versión previa, con las cifras y afirmaciones desactualizadas)
- `VERSION.txt` (versión previa)

**Documentación corregida:** `README.md` y `VERSION.txt`.

**Cambios efectuados en README.md:**
- Actualizado el conteo de routers/endpoints en la sección "Qué se
  construyó", de 14 routers / 40 endpoints a **18 routers y 78 endpoints**,
  con el listado completo de los 18 routers.
- Agregada la sección "Módulos: Calidad (SPC), Inteligencia Competitiva,
  Inteligencia Tributaria y Lean Captura", describiendo modelo, servicio,
  router, prefijo de API y vista de dashboard de cada uno de los cuatro
  módulos.
- Ampliado el listado de vistas del frontend (sección "Incluye") para
  mencionar explícitamente Lean Captura, Six Sigma SPC, Competencia y
  Tributaria SUNAT, que antes no figuraban.
- Corregida la sección de pendientes: eliminada la afirmación de que
  Inteligencia Competitiva e Inteligencia Tributaria "no se construyeron";
  reemplazada por la lista real de pendientes (extender forecast a
  producción/compras/inventarios; Monte Carlo excluido explícitamente por el
  cliente; validar el flujo completo en un entorno con red, ya resuelto en
  sesiones posteriores).

**Cambios efectuados en VERSION.txt:**
- Agregada la entrada "Hallazgo N°4: Estado: Cerrado." en la sección
  `HALLAZGOS CERRADOS`, con severidad revisada de Baja a Media (no era solo
  una cifra vieja, sino una afirmación activamente incorrecta sobre
  funcionalidad existente) y el detalle de archivos modificados
  (`README.md`, `VERSION.txt`).
- Agregada la entrada `v5 - ERP_Panaderia_Auditoria_Correccion_Hallazgo04_v1.zip`
  en `HISTORIAL DE VERSIONES`.

**Cantidad real de routers y endpoints documentados:** verificado por conteo
directo sobre el código (`@router.get/post/put/delete/patch` en
`backend/app/routers/*.py`, excluyendo `.bak`): **18 routers y 78 endpoints**,
cifra que coincide exactamente con la ya declarada en README.md y VERSION.txt.
Desglose por router: `auth` (2), `organizacion` (2), `productos` (4),
`compras` (4), `produccion` (3), `ventas` (3), `recetas` (3), `mermas` (1),
`consultas` (2), `dashboard` (4), `lean` (4), `inteligencia` (2),
`logistica` (3), `reportes` (3), `lean_captura` (23), `calidad` (5),
`competencia` (5), `tributaria` (5).

**Módulos nuevos incorporados a la documentación:**
- **Calidad — Six Sigma SPC** (`/api/calidad`): mediciones por variable de
  proceso, gráfico de control X-bar, histograma y Cp/Cpk.
- **Inteligencia Competitiva** (`/api/competencia`): precios de la
  competencia, comparativo propio vs. competencia, elasticidad de demanda,
  precio recomendado y simulación de promociones.
- **Inteligencia Tributaria** (`/api/tributaria`): control documental SUNAT
  (emisión/anulación de boleta/factura, ventas sin documento, reporte de
  mermas/desmedros).
- **Lean Captura** (`/api/lean-captura`): captura operativa de 5S, Kaizen,
  SMED, Jidoka, Andon, Heijunka y VSM.

**Corrección de afirmaciones que indicaban erróneamente que esos módulos no
existían:** la versión previa del README, en su sección de pendientes,
afirmaba que Inteligencia Competitiva e Inteligencia Tributaria "no se
construyeron". La revisión del código confirmó que ambos módulos (y también
Calidad/SPC y Lean Captura, que tampoco estaban mencionados) existían
completos desde antes de esta corrección. La afirmación fue eliminada y
reemplazada por la sección "Módulos: Calidad (SPC), Inteligencia
Competitiva, Inteligencia Tributaria y Lean Captura" con el detalle real de
cada uno.

**Validación realizada:**
1. Conteo directo de rutas (`@router.get/post/put/delete/patch`) sobre los
   18 archivos de `backend/app/routers/` (excluidos `.bak`) → 78 endpoints,
   coincide con la cifra documentada.
2. Verificación de que los 18 routers están efectivamente registrados en
   `backend/app/main.py` vía `include_router` → los 18 aparecen.
3. Verificación cruzada de que cada uno de los cuatro módulos nuevos tiene
   modelo, servicio, schema, router y vista de dashboard propia → confirmado
   para los cuatro.
4. Relectura completa de README.md y VERSION.txt tras la corrección →ambos
   documentan la misma cifra (18 routers / 78 endpoints), el mismo estado
   (Cerrado, severidad Media) y no contienen afirmaciones contradictorias
   entre sí.
5. Confirmado que no se modificó ningún archivo de `backend/` ni
   `frontend/core_erp_dashboard.html` como parte de esta corrección.

**Impacto del cambio:** puramente documental. No se alteró backend, frontend,
modelos, routers, services, schemas ni permisos. El impacto es que la
documentación deja de subestimar el alcance real del proyecto (dejaba fuera
cuatro módulos completos) y deja de contener una afirmación incorrecta que
podría inducir a un desarrollador o auditor futuro a asumir que Inteligencia
Competitiva e Inteligencia Tributaria no existen y a reconstruirlas por
error.

**Conclusión técnica:** el hallazgo quedó correctamente cerrado desde la
versión `ERP_Panaderia_Auditoria_Correccion_Hallazgo04_v1.zip`
(2026-08-04) a nivel de README.md y VERSION.txt; lo único pendiente era que
`AUDITORIA_TRAZABILIDAD.md` (este archivo) no había incorporado su sección
técnica ni lo había retirado de la tabla de hallazgos pendientes —
inconsistencia puramente de trazabilidad, sin efecto sobre el estado real
del proyecto ni sobre ningún hallazgo posterior (N°5, N°6). Con esta entrada
queda subsanada.

**Resultado:** ✅ Cerrado.

---

## ERP_Panaderia_Auditoria_Correccion_Hallazgo05_v1.zip

**Fecha:** 2026-08-04

**Hallazgo corregido:** N°5 – Las ventas no generaban movimientos de inventario/kardex.

**Diagnóstico (fase previa, aprobada antes de implementar):** `POST /api/ventas` →
`ventas_service.registrar_venta()` únicamente insertaba la fila en `ventas`
(`db.add(venta); db.commit()`); no llamaba a ningún método de
`inventario_service`. Como consecuencia: `LoteInventario.cantidad_disponible`
nunca se decrementaba al vender, no se creaba ningún `MovimientoInventario`
(`TipoMovimiento.SALIDA_VENTA` existía declarado en el enum pero no se usaba
en ningún lado del proyecto), y `Venta` no guardaba costo ni lote, por lo que
el costo histórico de una venta era irreconstruible.

**Corrección:**
- `ventas_service.registrar_venta()` ahora recibe también `almacen_id` y, tras
  agregar la `Venta` (`db.flush()`, sin commit todavía, para disponer de su
  `id`), llama a `inventario_service.consumir_fefo(...,
  tipo_movimiento=TipoMovimiento.SALIDA_VENTA, referencia=f"VENTA-{venta.id}")`
  — el mismo consumo FEFO real ya usado por `mermas_service.registrar_merma()`
  y por `produccion_service` al descontar insumos. No se creó ninguna función
  nueva de picking ni de costeo; se reutilizó `consumir_fefo()` tal cual
  existía, incluido el valor de enum `SALIDA_VENTA` que ya estaba declarado
  pero nunca se disparaba.
- `app/routers/ventas.py` (`POST /api/ventas`): resuelve el almacén de la
  sucursal con `inventario_service.obtener_o_crear_almacen()` (mismo patrón
  que `app/routers/mermas.py`, incluyendo el `db.commit()` separado de la
  creación del almacén) y envuelve la llamada al service en
  `try/except ValueError` → `HTTPException(400)` cuando no hay stock
  suficiente, en vez de dejar propagar un error 500.

**Archivos modificados:**
- `app/services/ventas_service.py`
- `app/routers/ventas.py`

**Alcance respetado:** no se modificó `rentabilidad_por_tienda()` (Hallazgo
N°2), `produccion_service.py` (Hallazgo N°1), `mermas.py`/`mermas_service.py`
(Hallazgo N°3), ni la estructura `backend/`/`frontend/`/`docs/` (Hallazgo
N°6). No se agregó `lote_id` a `Venta` ni a `MovimientoInventario`: la
trazabilidad venta→lote individual (cuando `consumir_fefo` reparte el consumo
entre varios lotes) queda como limitación conocida y documentada, igual que
ya ocurre hoy para mermas e insumos de producción — no es una regresión
introducida por esta corrección, es el mismo patrón preexistente en todo el
módulo de inventario.

**Pruebas ejecutadas (end-to-end, SQLite, servidor real vía `uvicorn`):**
1. Flujo completo producción → `EMPAQUE` (ingresa lote de 10 unidades de
   "Torta de Chocolate", costo unitario real S/ 3.7625) → venta de 4
   unidades: `LoteInventario.cantidad_disponible` bajó de 10 a 6;
   `valor_total` reportado por `/api/consultas/stock/{sucursal_id}` bajó de
   S/ 37.625 a S/ 22.575 (consistente: 4 × 3.7625 = 15.05).
2. Se verificó en `movimientos_inventario` la fila creada:
   `tipo=SALIDA_VENTA, cantidad=-4, costo_unitario=3.7625, costo_total=-15.05,
   referencia='VENTA-1'` (id de venta 1), confirmando el vínculo venta ↔
   kardex.
3. Venta con stock insuficiente (999 unidades solicitadas, 6 disponibles) →
   `400 Bad Request` con el mensaje de `consumir_fefo`; se confirmó que no
   quedó ninguna fila huérfana en `ventas` ni movimiento parcial en
   `movimientos_inventario`, y que el stock no se alteró.
4. Regresión Hallazgo N°2: `/api/ventas/rentabilidad-por-tienda` tras la
   venta real devolvió `costo_total_estimado=15.05`, `utilidad_real=64.95`,
   `margen_real_pct≈81.19`, `estado=CUMPLE_OBJETIVO` — coherente con el costo
   real del lote consumido.
5. Regresión Hallazgo N°3: usuario `gerencia` (solo lectura) siguió
   recibiendo `403` al intentar `POST /api/mermas`.
6. `python3 -m py_compile` sobre todo `backend/app/` sin errores;
   `uvicorn app.main:app` arrancó sin errores desde `backend/`,
   `GET /api/health` → `200 OK` (regresión Hallazgo N°6: estructura de
   carpetas intacta).

**Resultado:** ✅ Cerrado.

---

## Hallazgos pendientes

| N° | Descripción | Severidad | Estado |
|---|---|---|---|
| — | Ninguno. Los 6 hallazgos detectados están cerrados y documentados. | — | — |

*Nota histórica: el Hallazgo N°4 fue cerrado a nivel de código/documentación
desde la versión `ERP_Panaderia_Auditoria_Correccion_Hallazgo04_v1.zip`
(README.md y VERSION.txt ya lo reflejaban), pero este archivo
(`AUDITORIA_TRAZABILIDAD.md`) no había incorporado su sección técnica ni lo
había retirado de esta tabla. Esa inconsistencia de trazabilidad quedó
corregida en `ERP_Panaderia_Auditoria_Correccion_Hallazgo04_v2.zip` (ver
sección correspondiente arriba).*

---

## Resumen Ejecutivo

**Hallazgos detectados:** 6
**Hallazgos corregidos:** 6
**Hallazgos pendientes:** 0

**Versión estable actual:** `ERP_Panaderia_Auditoria_Correccion_Hallazgo04_v2.zip`
(documentación) — última corrección funcional: `ERP_Panaderia_Auditoria_Correccion_Hallazgo05_v1.zip`

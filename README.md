
# Core ERP — Pastelería Industrial (FastAPI + SQLAlchemy)

Este proyecto reconstruye y valida de punta a punta el backend que se había
diseñado en la sesión anterior (documentada en los Word adjuntos), esta vez
con acceso a red disponible para instalar dependencias y correr el flujo
completo.

## Estructura del proyecto

```
core_erp/
├── backend/                      ← todo el código y dependencias del backend
│   ├── app/                      ← paquete FastAPI (models, routers, schemas, services)
│   ├── seed.py
│   └── requirements.txt
├── frontend/
│   └── core_erp_dashboard.html   ← dashboard standalone, independiente del backend
├── docs/                         ← documentación de auditoría
├── README.md
├── VERSION.txt
└── AUDITORIA_TRAZABILIDAD.md
```

Backend y frontend están completamente separados: `frontend/` no depende de
ninguna ruta dentro de `backend/`, se comunica con la API únicamente por HTTP
(`fetch` contra `http://127.0.0.1:8000`).

## Verificado contra tus archivos de verificación

- **`recetas.py`** y **`mermas.py`**: copiados **tal cual los subiste**, sin
  ningún cambio (`app/routers/recetas.py`, `app/routers/mermas.py`). Encajan
  sin modificaciones sobre los modelos y servicios reconstruidos.
- **`erp_pasteleria.py`** (extraído del `.rar`, fuente real de la app
  Streamlit): se usó como referencia para portar la lógica real de negocio:
  picking PEPS/FEFO, costeo por producto, cálculo de mermas y rentabilidad
  real por tienda vs. margen objetivo.
- **`main.py` / `erp_laboral_pro.html`** (del `.zip`): confirmé que ese
  proyecto usa persistencia en JSON plano, muy distinto a la arquitectura
  SQLAlchemy documentada — se usó solo como referencia de convenciones de
  endpoints, no como base de código.

## Qué se construyó

- **Core:** `config.py`, `database.py` (SQLAlchemy), `security.py` (JWT +
  bcrypt), `deps.py` (autenticación, permisos por rol).
- **Modelos:** usuarios/roles/permisos, empresa/sucursal, productos,
  proveedores/clientes, inventario (almacenes, lotes con vencimiento,
  kardex de movimientos), órdenes de compra, recetas versionadas, órdenes de
  producción (máquina de **9 estados**), ventas, mermas.
- **Servicios:**
  - `inventario_service.py` → ingreso de lotes + consumo real **PEPS/FEFO**
    (vencimiento más próximo primero, luego más antiguo) + kardex.
  - `recetas_service.py` → versionamiento de recetas + costo estándar
    (costo de insumos al costo promedio actual + merma estimada).
  - `produccion_service.py` → ciclo de vida completo de la OP: `SOLICITADA →
    APROBADA → DOSIFICACION → PRODUCCION → HORNEADO → EMPAQUE → DESPACHO →
    RECEPCION → FACTURADO`. Dosificación consume insumos vía FEFO, empaque
    ingresa el producto terminado a almacén, facturado calcula el costo real
    total (insumos + mano de obra 15% + CIF 10%).
  - `compras_service.py` → flujo `SOLICITADA → APROBADA → RECIBIDA`
    (recepción ingresa lotes nuevos de inventario).
  - `ventas_service.py` → rentabilidad real por tienda (venta POS vs. costo
    real de producción) comparada contra el margen objetivo propio de cada
    sucursal.
  - `mermas_service.py` → baja de stock por merma vía FEFO, valorizada al
    costo del lote consumido.
- **Routers (18 en total, ver `main.py`):** `auth`, `organizacion`,
  `productos`, `compras`, `produccion`, `ventas`, `recetas`/`mermas`
  originales, `consultas`, `dashboard`, `lean`, `inteligencia`, `logistica`,
  `reportes`, `lean_captura`, `calidad`, `competencia` y `tributaria` (estos
  últimos cuatro descritos en la sección "Módulos: Calidad, Inteligencia
  Competitiva, Inteligencia Tributaria y Lean Captura" más abajo). En total
  suman 78 endpoints.
- `seed.py`: crea usuario `admin` / `admin123`, empresa demo (ECCLA S.A.C.),
  **5 sucursales** (Miraflores, San Isidro, Surco, La Molina, San Borja),
  insumos (harina, azúcar), un producto terminado (Torta de Chocolate) con
  receta activa, un proveedor y stock inicial.

## Validación end-to-end (ya ejecutada en este entorno)

A diferencia de la sesión anterior, aquí **sí hay salida a internet** para
instalar dependencias, así que pude instalar todo, levantar el servidor y
correr el flujo real:

1. `pip install -r backend/requirements.txt` → OK
2. `cd backend && python3 seed.py` → OK
3. Servidor levantado (`cd backend && uvicorn app.main:app`) → `/api/health` → `200 OK`
4. Flujo probado con `curl`:
   - Login → token JWT con permisos ✔
   - Receta activa + costo estándar del producto ✔
   - Orden de compra: solicitada → aprobada → recibida (ingresa lote) ✔
   - Orden de producción recorriendo **los 9 estados** hasta `FACTURADO`,
     con consumo FEFO real y costo real total calculado ✔
   - Transición inválida después de `FACTURADO` → rechazada correctamente
     con `400` ✔
   - Registro de merma con valorización FEFO ✔
   - Registro de venta + rentabilidad real por tienda vs. margen objetivo ✔

## Cómo correrlo tú

```bash
cd backend
pip install -r requirements.txt
python3 seed.py
uvicorn app.main:app --reload
# docs interactivas: http://127.0.0.1:8000/docs
# admin / admin123
```

> Todos los comandos anteriores se ejecutan **desde `backend/`**, para que
> `app/` sea siempre el paquete raíz y `core_erp.db` se cree siempre en el
> mismo directorio (ver Hallazgo N°6 en `AUDITORIA_TRAZABILIDAD.md`).

## Frontend: dashboard HTML de un solo archivo

`frontend/core_erp_dashboard.html` es un dashboard standalone (sidebar +
cards, identidad "pastelería industrial") que consume la API anterior vía
`fetch`. No necesita build ni servidor propio: se abre directamente en el
navegador (doble clic, o `file://`) mientras el backend está corriendo en
`http://127.0.0.1:8000`.

Incluye:
- Login contra `/api/auth/login` (JWT en memoria).
- Dashboard con KPIs, stock por sucursal y últimas OP.
- CRUD de productos, proveedores y recetas (con costo estándar).
- Compras: crear OC, aprobar, recibir.
- Producción: "fichas" visuales por OP con los 9 estados y avance paso a
  paso (dosificación, empaque, etc.), con enlace directo a su hoja de
  dosificación en PDF.
- Despacho / Recepción: responsable/vehículo al despachar, cantidad/merma
  de transporte al recepcionar.
- Registro de mermas y ventas (POS).
- Rentabilidad real por tienda vs. margen objetivo.
- Dashboard Ejecutivo (KPIs, Pareto y análisis XYZ de productos).
- Lean / Six Sigma / TOC (Kanban, cuello de botella, OEE, Cp/Cpk).
- Centro de Inteligencia (preguntas predefinidas resueltas con cálculo
  Python real).
- Lean Captura (5S/Kaizen/SMED/Jidoka/Andon/Heijunka/VSM).
- Six Sigma SPC (gráfico de control, histograma, Cp/Cpk por variable).
- Competencia (Inteligencia Competitiva: precios, elasticidad, precio
  recomendado, simulación de promociones).
- Tributaria SUNAT (Inteligencia Tributaria: documentos, ventas sin
  documento, reporte de mermas/desmedros).
- Reportes: exportes a Excel de producción y kardex.

Para que esto funcionara sin problemas de CORS al abrirse como archivo
local, se agregó `CORSMiddleware` (`allow_origins=["*"]`) en `backend/app/main.py`.

### Nuevos endpoints de solo lectura agregados para alimentar el dashboard

Estos no existían en el backend original y se agregaron sin tocar tus
archivos `recetas.py`/`mermas.py` verbatim:

- `GET /api/compras` — lista de órdenes de compra.
- `GET /api/produccion` — lista de órdenes de producción.
- `GET /api/ventas` — lista de ventas registradas.
- `GET /api/consultas/mermas` — mermas (para KPI y tabla).
- `GET /api/consultas/stock/{sucursal_id}` — stock disponible por sucursal.
- `GET /api/ventas/rentabilidad-por-tienda?sucursal_id=` — antes pedía
  `almacen_id`; ahora recibe `sucursal_id` (resuelve el almacén
  internamente vía `inventario_service.obtener_o_crear_almacen`), que es lo
  que el dashboard ya tiene disponible en sus selects.

## Lo que queda pendiente (fuera del alcance de este backend)

- Simulación Monte Carlo (precio harina/huevos/tipo de cambio, VaR/CVaR): no se construyó en esta sesión.
- Centro de Inteligencia Empresarial con lenguaje natural libre (aquí funciona por preguntas predefinidas resueltas con cálculo Python real, no por NLU).

## Módulos agregados en esta sesión: Dashboard Ejecutivo, Lean/Six Sigma/TOC, Centro de Inteligencia

Se agregó, sin tocar ninguna funcionalidad ni endpoint existente:

- **`app/models/produccion.py`**: nuevo modelo `HistorialEstadoOP`, que registra el
  timestamp real de cada transición de una OP. Es aditivo (no rompe nada existente)
  y es la base de datos real para las métricas Lean/TOC — sin él, OEE y cuello de
  botella tendrían que estimarse en vez de medirse.

- **`app/services/kpi_service.py` + `app/routers/dashboard.py`** (`GET
  /api/dashboard/resumen`, `GET /api/dashboard/pareto-productos`): ventas
  hoy/histórico, unidades producidas, pedidos pendientes, mermas valorizadas,
  utilidad y EBITDA aproximado (utilidad real, sin gastos financieros/depreciación
  que el ERP no modela todavía), margen %, semáforo por tienda (verde/amarillo/
  rojo/gris según cumplimiento del margen objetivo propio de cada sucursal),
  ranking de tiendas y productos, forecast simple (promedio diario de los
  últimos 7 días × 7), y ABC/Pareto de productos por venta acumulada.

- **`app/services/lean_service.py` + `app/routers/lean.py`** (`GET
  /api/lean/kanban`, `/cuello-de-botella`, `/oee`, `/capacidad-proceso`):
  - Kanban: conteo de OPs por etapa.
  - Cuello de botella (TOC): etapa con mayor tiempo promedio real de
    permanencia, calculado sobre `HistorialEstadoOP`.
  - OEE aproximado: Disponibilidad (tiempo de transformación real vs. lead
    time total del ciclo) × Rendimiento (cantidad producida/solicitada) ×
    Calidad (1 − valor de mermas / valor producido, a nivel planta, porque las
    mermas no están enlazadas a una OP específica en este modelo). Las
    aproximaciones están documentadas en el propio código.
  - Cp/Cpk (Six Sigma): sobre el rendimiento de producción, con límites de
    especificación configurables (±10% por defecto).

- **`app/services/inteligencia_service.py` + `app/routers/inteligencia.py`**
  (`GET /api/inteligencia/preguntas`, `POST /api/inteligencia/preguntar`):
  responde en Python puro (sin LLM) las 11 preguntas del prompt original —
  qué producir mañana, qué tienda vende/merma más, producto más rentable,
  impacto de faltante de un insumo, costo real de un producto, compra
  sugerida para la próxima semana, OP más eficiente, cuello de botella,
  producto a evaluar retirar, y ahorro por reducción de merma. Cada pregunta
  tiene un código fijo (no texto libre) para que el resultado sea
  determinístico y auditable.

- **Frontend**: se agregaron 3 vistas nuevas al sidebar del dashboard HTML
  existente (`Dashboard Ejecutivo`, `Lean / Six Sigma / TOC`, `Centro de
  Inteligencia`) reutilizando exactamente el mismo sistema de diseño (misma
  paleta, tipografías, tarjetas y tablas), sin modificar ninguna vista
  anterior.

Todo lo anterior fue probado end-to-end contra el backend real (login,
generación de OPs completas SOLICITADA→FACTURADO, ventas, mermas) antes de
entregarse, no sólo revisado en código.

## Sesión 3: Despacho/Recepción, aislamiento por tienda, reportes, XYZ, seguridad por roles

Excluido explícitamente por instrucción del cliente: **simulación Monte Carlo**
(precio harina/huevos/tipo de cambio, VaR/CVaR) — no se construyó.

⚠️ Este backend no se pudo instalar ni correr en este entorno (sin salida a
red para `pip install`). Se validó con `python3 -m py_compile` y análisis AST
de todos los archivos nuevos/modificados (sin errores de sintaxis), pero
**no se ejecutó el flujo real contra un servidor levantado**, a diferencia de
las sesiones anteriores. Instala dependencias y corre `seed.py` /
`cd backend && uvicorn app.main:app --reload` para validarlo end-to-end.

- **`app/models/logistica.py` + `app/services/logistica_service.py` +
  `app/routers/logistica.py`** (`POST /api/logistica/despachos`,
  `GET /api/logistica/despachos`, `POST /api/logistica/recepciones`):
  el despacho y la recepción en tienda pasan de ser simples *estados* de la
  OP a un módulo con datos propios — responsable, vehículo y hora de salida
  del despacho; cantidad recepcionada, merma de transporte (valorizada y
  descontada del almacén vía `mermas_service`), aceptación y observaciones de
  la recepción. Ambos endpoints validan el estado de la OP y la avanzan
  automáticamente (EMPAQUE→DESPACHO→RECEPCION) reutilizando
  `produccion_service.avanzar_estado`, sin duplicar la máquina de estados.

- **Aislamiento real por tienda** (`app/deps.py:sucursal_scope`,
  `verificar_acceso_sucursal`): el modelo `Usuario.sucursal_id` ya existía,
  pero ningún endpoint lo usaba para filtrar — cualquier usuario autenticado
  veía todas las tiendas. Ahora los listados de ventas, producción, mermas y
  stock (`/api/ventas`, `/api/produccion`, `/api/consultas/mermas`,
  `/api/consultas/stock/{id}`, `/api/ventas/rentabilidad-por-tienda`) filtran
  por la sucursal del usuario, salvo que tenga el permiso
  `organizacion.multisucursal` (admin/gerencia). Pedir la sucursal de otro
  responde `403`.

- **Seguridad por roles** (`seed.py`): se reemplazó el único rol "admin" por
  7 roles con permisos propios — administrador, gerencia, producción,
  almacén, compras, ventas y tienda — tal como pide el módulo de Seguridad
  del prompt original. Se crea un usuario por tienda
  (`tienda.<código>` / `tienda123`, ej. `tienda.mir`) que solo ve su propia
  sucursal, y un usuario `gerencia` / `gerencia123` multi-sucursal de solo
  lectura.

- **Reportes** (`app/services/reportes_service.py` + `app/routers/reportes.py`):
  - `GET /api/reportes/dosificacion/{op_id}.pdf`: hoja de dosificación real
    en PDF (ReportLab) con la cantidad requerida por insumo (según receta
    activa × cantidad solicitada), unidad y el lote FEFO que se sugeriría
    consumir (nueva función de solo lectura
    `inventario_service.sugerir_lote_fefo`, no descuenta stock), más espacio
    para firma de operario/supervisor.
  - `GET /api/reportes/produccion.xlsx` y `GET /api/reportes/kardex.xlsx`:
    exportes a Excel (Openpyxl) de las OPs y del kardex de movimientos.

- **Inteligencia Comercial** (`app/services/kpi_service.py`): se agregó
  **análisis XYZ** (`GET /api/dashboard/xyz-productos`) — clasifica cada
  producto por el coeficiente de variación de su demanda diaria de los
  últimos 30 días (X = estable ≤10%, Y = variable ≤25%, Z = errática >25%),
  complementando el ABC/Pareto que ya existía — y **ranking de tiendas por
  producto** (`GET /api/dashboard/ranking-tiendas/{producto_id}`), que
  resuelve directamente la pregunta "qué tienda vende más [producto]".

- **Frontend**: se agregaron las vistas "Despacho / Recepción" y "Reportes"
  al sidebar existente, reutilizando el mismo sistema de diseño. La ficha de
  cada OP (`opTicketHtml`) ahora captura responsable/vehículo al despachar y
  cantidad/merma al recepcionar (en vez del botón genérico de "avanzar
  estado"), y cada ficha tiene un enlace directo a su hoja de dosificación en
  PDF. El Dashboard Ejecutivo incorpora la tabla XYZ junto al Pareto
  existente.

## Sesión 4: cierre de brechas de aislamiento por tienda + verificación de errores

Se pidió explícitamente **no construir Monte Carlo** (confirmado: no existe
ninguna referencia a simulación Monte Carlo / VaR / CVaR en el código; ya
estaba fuera de alcance desde la Sesión 3) y **verificar errores** en todo
el proyecto. Verificación realizada:

- `python3 -m py_compile` sobre los 55 archivos `.py` → sin errores de sintaxis.
- Auditoría AST de rutas (`@router.get/post/...`) en los 14 routers → sin
  rutas duplicadas (40 endpoints únicos).
- Auditoría de imports internos de la capa `app/services/*` → es un DAG
  (grafo acíclico): `inventario_service` es la base, y ninguna cadena de
  dependencias vuelve sobre sí misma. No hay import circular.
- Cruce de cada llamada `fetch`/`api()` del frontend contra los endpoints
  reales del backend → todas resuelven a una ruta existente.

**Errores reales encontrados y corregidos** (brecha de aislamiento por
tienda que la Sesión 3 dejó incompleta: los *listados* ya filtraban por
sucursal, pero no los *endpoints de escritura* ni el Dashboard Ejecutivo):

1. `POST /api/produccion` (crear OP), `POST /api/mermas` (registrar merma) y
   `POST /api/ventas` (registrar venta) recibían `sucursal_id` directo del
   body sin validarlo contra la tienda del usuario autenticado — un usuario
   con rol "tienda" podía escribir datos a nombre de otra sucursal. Ahora los
   tres llaman a `verificar_acceso_sucursal(payload.sucursal_id, scope)`
   antes de ejecutar la operación (mismo mecanismo que ya usaban los
   listados), y responden `403` si la tienda no coincide.
2. `GET /api/dashboard/resumen`, `/pareto-productos` y `/xyz-productos`
   (Dashboard Ejecutivo) no filtraban por tienda en absoluto: cualquier
   usuario con `inventario.leer` veía el consolidado de las 5 sucursales,
   incluido un usuario de tienda. `kpi_service.resumen_ejecutivo`,
   `pareto_productos` y `xyz_productos` ahora aceptan `sucursal_id` opcional
   y el router lo resuelve desde `sucursal_scope` (un usuario de tienda ve
   solo su propio resumen; admin/gerencia sigue viendo el consolidado).
3. `GET /api/dashboard/ranking-tiendas/{producto_id}` compara ventas entre
   todas las tiendas por diseño (responde "qué tienda vende más X"), así que
   no tiene una versión "por tienda" con sentido — ahora responde `403` si lo
   llama un usuario sin `organizacion.multisucursal`, en vez de exponer sin
   querer el detalle de otras sucursales a un usuario de tienda.

No se tocó ninguna funcionalidad existente, ningún endpoint cambió de
firma pública salvo el parámetro nuevo (opcional) de los tres servicios de
KPI, y todo sigue compilando sin errores tras el cambio.

## Módulos: Calidad (SPC), Inteligencia Competitiva, Inteligencia Tributaria y Lean Captura

Cuatro módulos completos (modelo + servicio + schema + router + vista propia
en el dashboard) que estaban implementados en el código pero no descritos en
este README:

- **Calidad — Six Sigma SPC** (`app/models/calidad.py`,
  `app/services/spc_service.py`, `app/routers/calidad.py`, prefijo
  `/api/calidad`): registro de mediciones por variable de proceso, gráfico
  de control (X-bar), histograma y cálculo de Cp/Cpk sobre límites de
  especificación configurables. Vista del dashboard: **Six Sigma SPC**
  (`view-spc`).

- **Inteligencia Competitiva** (`app/models/competencia.py`,
  `app/services/competencia_service.py`, `app/routers/competencia.py`,
  prefijo `/api/competencia`): registro de precios de la competencia por
  producto, comparativo propio vs. competencia, elasticidad de demanda,
  precio recomendado y simulación de promociones. Vista del dashboard:
  **Competencia** (`view-competencia`).

- **Inteligencia Tributaria — control documental SUNAT**
  (`app/models/tributaria.py`, `app/services/tributaria_service.py`,
  `app/routers/tributaria.py`, prefijo `/api/tributaria`): emisión y
  anulación de documentos (boleta/factura), listado de documentos, ventas
  sin documento emitido y reporte de mermas/desmedros para sustento
  tributario. Vista del dashboard: **Tributaria SUNAT**
  (`view-tributaria`).

- **Lean Captura** (`app/models/lean_captura.py`,
  `app/services/lean_captura_service.py`, `app/routers/lean_captura.py`,
  prefijo `/api/lean-captura`): captura operativa de **5S, Kaizen, SMED,
  Jidoka, Andon, Heijunka y VSM** (checklists 5S, tarjetas Kaizen con
  avance de estado, registros SMED, eventos Jidoka con resolución, alertas
  Andon, plan vs. real de Heijunka y procesos VSM), cada uno con su propio
  resumen de solo lectura. Vista del dashboard: **Lean Captura
  (5S/Kaizen/SMED...)** (`view-lean-captura`).

Estos cuatro módulos elevan el total del backend a **18 routers y 78
endpoints** (ver conteo actualizado en la sección "Qué se construyó").

### Pendiente real para una próxima sesión (no simulado, no inventado)

- Forecast: hoy solo cubre ventas (promedio móvil 7 días). Extender a
  producción/compras/inventarios es la siguiente pieza natural sobre la
  misma base de `kpi_service.py`.
- Simulación Monte Carlo (precio harina/huevos/tipo de cambio, VaR/CVaR):
  excluida explícitamente por instrucción del cliente, sigue fuera de
  alcance.
- Validar el flujo completo (`pip install` + `seed.py` + `uvicorn`) en un
  entorno con salida a red, ya que este entorno no la tuvo en la Sesión 3.


# dashboard-panaderia

"""SPC (Statistical Process Control) sobre variables medidas en planta
(peso, temperatura, humedad, brix, etc.), registradas una a una en
`mediciones_spc`. Usa la carta de control Individuales-Rango Móvil (I-MR),
el esquema estándar cuando las mediciones no vienen en subgrupos fijos
(a diferencia de X-bar/R). Constantes D4=3.267 y d2=1.128 son las
constantes estándar de tablas de control para n=2 (rango móvil entre
mediciones consecutivas)."""
import statistics

from sqlalchemy.orm import Session

from app.models.calidad import MedicionSPC

D2_N2 = 1.128  # constante estándar de tablas SPC para subgrupo de 2 (rango móvil)
D4_N2 = 3.267


def registrar_medicion(
    db: Session, sucursal_id: int, variable: str, valor: float,
    producto_id: int | None = None, lote: str = "",
) -> MedicionSPC:
    medicion = MedicionSPC(
        sucursal_id=sucursal_id, producto_id=producto_id, variable=variable, valor=valor, lote=lote,
    )
    db.add(medicion)
    db.commit()
    db.refresh(medicion)
    return medicion


def listar_mediciones(
    db: Session, variable: str, sucursal_id: int | None = None, limite: int = 200
) -> list[MedicionSPC]:
    q = db.query(MedicionSPC).filter(MedicionSPC.variable == variable)
    if sucursal_id is not None:
        q = q.filter(MedicionSPC.sucursal_id == sucursal_id)
    return q.order_by(MedicionSPC.id.desc()).limit(limite).all()[::-1]  # orden cronológico


def variables_disponibles(db: Session, sucursal_id: int | None = None) -> list[str]:
    q = db.query(MedicionSPC.variable).distinct()
    if sucursal_id is not None:
        q = q.filter(MedicionSPC.sucursal_id == sucursal_id)
    return sorted({row[0] for row in q.all()})


def carta_control_imr(db: Session, variable: str, sucursal_id: int | None = None) -> dict:
    """Carta I-MR: carta de Individuales (X) + carta de Rango Móvil (MR).
    MRi = |Xi - Xi-1|. Límites: UCL_X = X̄ + 2.66*MR̄, LCL_X = X̄ - 2.66*MR̄
    (2.66 = 3/d2 con d2=1.128); UCL_MR = D4*MR̄ (D4=3.267 para n=2)."""
    mediciones = listar_mediciones(db, variable, sucursal_id)
    valores = [float(m.valor) for m in mediciones]
    if len(valores) < 3:
        return {
            "variable": variable, "puntos": [], "media": None, "ucl_x": None, "lcl_x": None,
            "mr_promedio": None, "ucl_mr": None, "fuera_de_control": [],
            "mensaje": "Se necesitan al menos 3 mediciones para calcular la carta de control.",
        }
    media = statistics.mean(valores)
    rangos_moviles = [abs(valores[i] - valores[i - 1]) for i in range(1, len(valores))]
    mr_promedio = statistics.mean(rangos_moviles)
    ucl_x = media + (3 / D2_N2) * mr_promedio
    lcl_x = media - (3 / D2_N2) * mr_promedio
    ucl_mr = D4_N2 * mr_promedio
    puntos = []
    fuera_de_control = []
    for i, m in enumerate(mediciones):
        valor = float(m.valor)
        fuera = valor > ucl_x or valor < lcl_x
        puntos.append({
            "id": m.id, "valor": valor, "fecha": m.creado_en.isoformat() if m.creado_en else None,
            "lote": m.lote, "fuera_de_control": fuera,
        })
        if fuera:
            fuera_de_control.append(m.id)
    return {
        "variable": variable,
        "puntos": puntos,
        "media": media,
        "ucl_x": ucl_x,
        "lcl_x": lcl_x,
        "mr_promedio": mr_promedio,
        "ucl_mr": ucl_mr,
        "fuera_de_control": fuera_de_control,
        "proceso_bajo_control": len(fuera_de_control) == 0,
    }


def histograma(db: Session, variable: str, sucursal_id: int | None = None, bins: int = 10) -> dict:
    valores = [float(m.valor) for m in listar_mediciones(db, variable, sucursal_id, limite=5000)]
    if not valores:
        return {"variable": variable, "bins": [], "muestras": 0}
    minimo, maximo = min(valores), max(valores)
    if minimo == maximo:
        return {
            "variable": variable, "muestras": len(valores),
            "bins": [{"desde": minimo, "hasta": maximo, "frecuencia": len(valores)}],
        }
    ancho = (maximo - minimo) / bins
    conteo = [0] * bins
    for v in valores:
        idx = min(int((v - minimo) / ancho), bins - 1)
        conteo[idx] += 1
    return {
        "variable": variable,
        "muestras": len(valores),
        "media": statistics.mean(valores),
        "desviacion_estandar": statistics.stdev(valores) if len(valores) > 1 else 0.0,
        "bins": [
            {"desde": minimo + i * ancho, "hasta": minimo + (i + 1) * ancho, "frecuencia": conteo[i]}
            for i in range(bins)
        ],
    }


def cp_cpk(
    db: Session, variable: str, lsl: float, usl: float, sucursal_id: int | None = None
) -> dict:
    """Cp/Cpk clásico de Six Sigma sobre una variable medida, con límites de
    especificación (LSL/USL) que el usuario indica según la ficha técnica del
    producto (ej. peso de la torta: 0.95 kg - 1.05 kg)."""
    valores = [float(m.valor) for m in listar_mediciones(db, variable, sucursal_id, limite=5000)]
    if len(valores) < 2:
        return {"cp": None, "cpk": None, "mensaje": "Se necesitan al menos 2 mediciones.", "muestras": len(valores)}
    media = statistics.mean(valores)
    desviacion = statistics.stdev(valores)
    if desviacion == 0:
        return {
            "cp": None, "cpk": None,
            "mensaje": "Desviación estándar es 0; Cp/Cpk no son calculables.",
            "media": media, "muestras": len(valores),
        }
    cp = (usl - lsl) / (6 * desviacion)
    cpk = min(usl - media, media - lsl) / (3 * desviacion)
    if cpk >= 1.33:
        interpretacion = "Proceso capaz (Cpk ≥ 1.33)"
    elif cpk >= 1.0:
        interpretacion = "Proceso marginalmente capaz (1.0 ≤ Cpk < 1.33)"
    else:
        interpretacion = "Proceso NO capaz (Cpk < 1.0): alta variabilidad frente a la tolerancia"
    return {
        "cp": cp, "cpk": cpk, "media": media, "desviacion_estandar": desviacion,
        "lsl": lsl, "usl": usl, "interpretacion": interpretacion, "muestras": len(valores),
    }

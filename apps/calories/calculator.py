# =========================================
# CALCULADORA DE CALORÍAS - BIO-FIT
# =========================================

def calcular_tmb(peso, altura, edad, sexo):
    """
    Calcula la Tasa Metabólica Basal (TMB)
    Fórmula Harris-Benedict
    """
    if sexo.lower() == "hombre":
        return 88.36 + (13.4 * peso) + (4.8 * altura) - (5.7 * edad)
    elif sexo.lower() == "mujer":
        return 447.6 + (9.2 * peso) + (3.1 * altura) - (4.3 * edad)
    else:
        raise ValueError("Sexo debe ser 'hombre' o 'mujer'")


def calcular_get(tmb, nivel_actividad):
    """
    Calcula el Gasto Energético Total (GET)
    """
    factores = {
        "sedentario": 1.2,
        "ligero": 1.375,
        "moderado": 1.55,
        "activo": 1.725,
        "muy_activo": 1.9
    }

    if nivel_actividad not in factores:
        raise ValueError("Nivel de actividad inválido")

    return tmb * factores[nivel_actividad]


def ajustar_objetivo(get, objetivo):
    """
    Ajusta calorías según objetivo
    """
    ajustes = {
        "perder_peso": -500,
        "mantener": 0,
        "ganar_masa": 300
    }

    if objetivo not in ajustes:
        raise ValueError("Objetivo inválido")

    return get + ajustes[objetivo]


def calcular_calorias_completas(data):
    """
    Función principal que calcula todo el flujo
    """

    try:
        # =============================
        # Validación de datos
        # =============================
        peso = float(data.get("peso", 0))
        altura = float(data.get("altura", 0))
        edad = int(data.get("edad", 0))
        sexo = data.get("sexo", "").lower()
        actividad = data.get("actividad", "").lower()
        objetivo = data.get("objetivo", "").lower()

        if not peso or not altura or not edad:
            return {"error": "Peso, altura y edad son obligatorios"}

        if sexo not in ["hombre", "mujer"]:
            return {"error": "Sexo debe ser 'hombre' o 'mujer'"}

        if actividad not in ["sedentario", "ligero", "moderado", "activo", "muy_activo"]:
            return {"error": "Nivel de actividad inválido"}

        if objetivo not in ["perder_peso", "mantener", "ganar_masa"]:
            return {"error": "Objetivo inválido"}

        # =============================
        # Cálculos
        # =============================
        tmb = calcular_tmb(peso, altura, edad, sexo)
        get = calcular_get(tmb, actividad)
        calorias_finales = ajustar_objetivo(get, objetivo)

        # =============================
        # Respuesta
        # =============================
        return {
            "tmb": round(tmb, 2),
            "get": round(get, 2),
            "calorias_recomendadas": round(calorias_finales, 2)
        }

    except Exception as e:
        return {"error": f"Error en cálculo: {str(e)}"}

from pathlib import Path
import os

import numpy as np
import pandas as pd
from joblib import dump
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

CARPETA = Path(__file__).resolve().parent

historico = pd.read_csv(
    CARPETA / "euroliga_dataset_entrenamiento_9_temporadas.csv"
)
actual = pd.read_csv(
    CARPETA / "2026_27_jornadas_metricas.csv"
)
# Número de equipos participantes en cada temporada
historico["num_teams"] = historico.groupby(
    "season"
)["team_code"].transform("nunique")

# Temporada actual: detectar los equipos reales
actual["num_teams"] = actual["team_code"].nunique()

print("\nEQUIPOS TEMPORADA ACTUAL:", actual["num_teams"].iloc[0])
print("TEMPORADAS HISTÓRICAS:", historico["season"].nunique())

VARIABLES = [
    "games_played",
    "win_pct",
    "net_rating",
    "offensive_rating",
    "defensive_rating",
    "three_point_pct",
    "efg_pct",
    "tov_ratio",
    "orb_pct",
    "dreb_pct",
    "num_teams"
]

OBJETIVOS = {
    "playoffs": "probabilidad_playoffs",
    "final_four": "probabilidad_final_four"
}

TEMPORADA_ACTUAL = "2026-27"

# Nunca entrenar con el resultado final de la temporada actual
if TEMPORADA_ACTUAL in historico["season"].unique():
    raise ValueError(
        "La temporada actual aparece en el histórico "
        "de entrenamiento."
    )

actual = actual[
    actual["season"] == TEMPORADA_ACTUAL
].copy()

if actual.empty:
    raise ValueError("No hay estadísticas de 2026-27")

if actual.duplicated(
    ["season", "team_code", "round"]
).any():
    raise ValueError("Hay equipos y jornadas duplicados")

actual["win_pct"] = (
    actual["wins"]
    / actual["games_played"].replace(0, np.nan)
)

predicciones = []
explicaciones = []

carpeta_modelos = CARPETA / "modelos_por_jornada"
carpeta_modelos.mkdir(exist_ok=True)

for jornada in sorted(actual["round"].unique()):

    jornada = int(jornada)

    # MODELO C: histórico acumulado hasta la jornada actual
    entrenamiento = historico[
        (historico["season"] < TEMPORADA_ACTUAL)
        & (historico["round"].between(1, jornada))
        & (historico["games_played"] > 0)
    ].copy()

    equipos_actuales = actual[
        actual["round"] == jornada
    ].copy()

    equipos_actuales = equipos_actuales[
        equipos_actuales["games_played"] > 0
    ].copy()

    # Mismo peso total para cada equipo-temporada
    conteos = entrenamiento.groupby(
        ["season", "team_code"]
    )["round"].transform("count")

    pesos = 1.0 / conteos

    print(
        f"\nJornada {jornada}: "
        f"{len(entrenamiento)} filas históricas, "
        f"{len(equipos_actuales)} equipos actuales"
    )

    for objetivo, columna_prob in OBJETIVOS.items():

        if entrenamiento[objetivo].nunique() != 2:
            raise ValueError(
                f"No hay ambas clases para {objetivo}"
            )

        modelo = make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            LogisticRegression(
                max_iter=2000,
                C=0.5
            )
        )

        modelo.fit(
            entrenamiento[VARIABLES],
            entrenamiento[objetivo],
            logisticregression__sample_weight=pesos
        )

        valores = equipos_actuales[VARIABLES]

        probabilidades = modelo.predict_proba(
            valores
        )[:, 1]

        equipos_actuales[columna_prob] = probabilidades

        # Guardar el modelo específico de esta jornada
        dump(
            {
                "modelo": modelo,
                "variables": VARIABLES,
                "jornada": jornada,
                "objetivo": objetivo
            },
            carpeta_modelos /
            f"{objetivo}_jornada_{jornada}.joblib"
        )

        # Explicación matemática del mismo modelo
        imputador = modelo.named_steps["simpleimputer"]
        escalador = modelo.named_steps["standardscaler"]
        regresion = modelo.named_steps["logisticregression"]

        transformados = escalador.transform(
            imputador.transform(valores)
        )

        contribuciones = (
            transformados * regresion.coef_[0]
        )

        logits = (
            regresion.intercept_[0]
            + contribuciones.sum(axis=1)
        )

        reconstruidas = 1 / (1 + np.exp(-logits))

        if not np.allclose(
            reconstruidas,
            probabilidades,
            atol=1e-6
        ):
            raise ValueError(
                f"Fallo al explicar {objetivo}, "
                f"jornada {jornada}"
            )

        for posicion, (_, equipo) in enumerate(
            equipos_actuales.iterrows()
        ):
            for indice, variable in enumerate(VARIABLES):

                explicaciones.append({
                    "season": TEMPORADA_ACTUAL,
                    "team_code": equipo["team_code"],
                    "round": jornada,
                    "objetivo": objetivo,
                    "variable": variable,
                    "valor": equipo[variable],
                    "contribucion_logit": (
                        contribuciones[posicion, indice]
                    ),
                    "probabilidad": (
                        probabilidades[posicion]
                    )
                })

    predicciones.append(equipos_actuales)

resultado = pd.concat(
    predicciones,
    ignore_index=True
)

explicaciones_df = pd.DataFrame(explicaciones)

# Comprobar que ambas salidas contienen todos los equipos
esperadas = len(resultado) * len(OBJETIVOS) * len(VARIABLES)

if len(explicaciones_df) != esperadas:
    raise ValueError("Faltan explicaciones")

# Guardar los CSV completos solo después de calcular todo
salidas = [
    (
        resultado,
        CARPETA / "predicciones_actuales_por_jornada.csv"
    ),
    (
        explicaciones_df,
        CARPETA / "explicaciones_modelos_por_jornada.csv"
    )
]

for tabla, destino in salidas:
    temporal = destino.with_suffix(".tmp")
    tabla.to_csv(temporal, index=False)
    os.replace(temporal, destino)

ultima_jornada = int(resultado["round"].max())

ultima = resultado[
    resultado["round"] == ultima_jornada
].sort_values(
    "probabilidad_playoffs",
    ascending=False
)

print("\nPREDICCIONES CON MODELO C")
print("------------------------")
print("Última jornada:", ultima_jornada)
print("Equipos:", len(ultima))

print(
    ultima[
        [
            "team_code",
            "wins",
            "losses",
            "probabilidad_playoffs",
            "probabilidad_final_four"
        ]
    ].round(3).to_string(index=False)
)

print("\nSuma de probabilidades:")
print(
    "Playoffs:",
    round(ultima["probabilidad_playoffs"].sum(), 3)
)
print(
    "Final Four:",
    round(ultima["probabilidad_final_four"].sum(), 3)
)

print("\nMODELOS Y EXPLICACIONES ACTUALIZADOS")


import pandas as pd

# Leer los partidos actuales
partidos = pd.read_csv("2026_27_partidos_actuales.csv")

# Estadísticas que necesitamos acumular
campos = [
    "timePlayed",
    "points",
    "fieldGoalsMade2",
    "fieldGoalsAttempted2",
    "fieldGoalsMade3",
    "fieldGoalsAttempted3",
    "freeThrowsMade",
    "freeThrowsAttempted",
    "offensiveRebounds",
    "defensiveRebounds",
    "turnovers",
    "assistances"
]

columnas = (
    ["stat_" + campo for campo in campos]
    + ["opp_" + campo for campo in campos]
)

# Comprobar los campos necesarios
faltantes = [
    campo for campo in columnas
    if campo not in partidos.columns
]

if faltantes:
    raise ValueError(f"Faltan columnas: {faltantes}")

# Sumar estadísticas de cada jornada
por_jornada = partidos.groupby(
    ["season", "team_code", "round"],
    as_index=False
)[columnas + ["win"]].sum()

# Contar partidos de cada equipo en cada jornada
conteo = partidos.groupby(
    ["season", "team_code", "round"]
).size().reset_index(name="partidos_jornada")

por_jornada = por_jornada.merge(
    conteo,
    on=["season", "team_code", "round"],
    validate="one_to_one"
)

por_jornada = por_jornada.sort_values(
    ["season", "team_code", "round"]
)

# Acumular hasta cada jornada
acumular = columnas + ["win", "partidos_jornada"]

por_jornada[acumular] = (
    por_jornada.groupby(
        ["season", "team_code"]
    )[acumular].cumsum()
)

por_jornada = por_jornada.rename(
    columns={
        "win": "wins",
        "partidos_jornada": "games_played"
    }
)

por_jornada["losses"] = (
    por_jornada["games_played"]
    - por_jornada["wins"]
)

# Mantener también las jornadas sin partido
jornada_maxima = int(partidos["round"].max())
bloques = []

for codigo in por_jornada["team_code"].unique():

    equipo = por_jornada[
        por_jornada["team_code"] == codigo
    ].copy()

    calendario = pd.DataFrame({
        "round": range(1, jornada_maxima + 1)
    })

    completo = calendario.merge(
        equipo, on="round", how="left"
    )

    completo["season"] = "2026-27"
    completo["team_code"] = codigo

    columnas_numericas = [
        c for c in equipo.select_dtypes(
            include="number"
        ).columns
        if c != "round"
    ]

    completo[columnas_numericas] = (
        completo[columnas_numericas]
        .ffill()
        .fillna(0)
    )

    bloques.append(completo)

actual = pd.concat(bloques, ignore_index=True)

# Validar los partidos, sin exigir que la temporada
# esté terminada ni que todas las jornadas tengan 10 partidos
if actual.duplicated(
    ["season", "team_code", "round"]
).any():
    raise ValueError("Hay filas duplicadas")

ultimo = actual[
    actual["round"] == jornada_maxima
]

if int(ultimo["games_played"].sum()) != len(partidos):
    raise ValueError(
        "El total de partidos acumulados no coincide"
    )

# Guardar las estadísticas acumuladas
actual.to_csv(
    "2026_27_acumulado_actual.csv",
    index=False
)

print("\nTEMPORADA ACTUAL PREPARADA")
print("-------------------------")
print("Jornadas:", jornada_maxima)
print("Equipos:", actual["team_code"].nunique())
print("Filas:", len(actual))
print("Columnas:", len(actual.columns))

print("\nREAL MADRID - EVOLUCIÓN ACTUAL")
print("------------------------------")

madrid = actual[
    actual["team_code"] == "MAD"
]

print(
    madrid[
        ["round", "games_played", "wins", "losses"]
    ].to_string(index=False)
)

print("\nArchivo: 2026_27_acumulado_actual.csv")
print("ACUMULACIÓN ACTUAL COMPLETADA")

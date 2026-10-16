
import numpy as np
import pandas as pd

# Leer las cinco temporadas acumuladas por jornada
df = pd.read_csv(
    "2026_27_acumulado_actual.csv"
)

def dividir(numerador, denominador):
    return numerador / denominador.replace(0, np.nan)

# Estadísticas acumuladas del equipo
fga = (
    df["stat_fieldGoalsAttempted2"]
    + df["stat_fieldGoalsAttempted3"]
)

fgm = (
    df["stat_fieldGoalsMade2"]
    + df["stat_fieldGoalsMade3"]
)

fta = df["stat_freeThrowsAttempted"]
orb = df["stat_offensiveRebounds"]
drb = df["stat_defensiveRebounds"]
tov = df["stat_turnovers"]
ast = df["stat_assistances"]

# Estadísticas acumuladas de los rivales
opp_fga = (
    df["opp_fieldGoalsAttempted2"]
    + df["opp_fieldGoalsAttempted3"]
)

opp_fgm = (
    df["opp_fieldGoalsMade2"]
    + df["opp_fieldGoalsMade3"]
)

opp_fta = df["opp_freeThrowsAttempted"]
opp_orb = df["opp_offensiveRebounds"]
opp_drb = df["opp_defensiveRebounds"]
opp_tov = df["opp_turnovers"]
opp_ast = df["opp_assistances"]

# Estimación ajustada de posesiones
rebotes_ajustados = (
    1.07 * dividir(orb, orb + opp_drb)
    * (fga - fgm)
)

opp_rebotes_ajustados = (
    1.07 * dividir(opp_orb, opp_orb + drb)
    * (opp_fga - opp_fgm)
)

posesiones_equipo = (
    fga + 0.40 * fta - rebotes_ajustados + tov
)

posesiones_rival = (
    opp_fga + 0.40 * opp_fta
    - opp_rebotes_ajustados + opp_tov
)

posesiones = (
    posesiones_equipo + posesiones_rival
) / 2

# Métricas de eficiencia
df["pace"] = dividir(
    posesiones * 2400,
    df["stat_timePlayed"]
)

df["offensive_rating"] = dividir(
    100 * df["stat_points"],
    posesiones
)

df["defensive_rating"] = dividir(
    100 * df["opp_points"],
    posesiones
)

df["net_rating"] = (
    df["offensive_rating"]
    - df["defensive_rating"]
)

# Porcentajes de tiro
df["two_point_pct"] = dividir(
    df["stat_fieldGoalsMade2"],
    df["stat_fieldGoalsAttempted2"]
)

df["three_point_pct"] = dividir(
    df["stat_fieldGoalsMade3"],
    df["stat_fieldGoalsAttempted3"]
)

df["free_throw_pct"] = dividir(
    df["stat_freeThrowsMade"],
    fta
)

df["efg_pct"] = dividir(
    fgm + 0.5 * df["stat_fieldGoalsMade3"],
    fga
)

df["ts_pct"] = dividir(
    df["stat_points"],
    2 * (fga + 0.44 * fta)
)

# Pérdidas, rebotes y tiros libres
df["tov_ratio"] = dividir(
    tov,
    fga + 0.44 * fta + ast + tov
)

df["orb_pct"] = dividir(
    orb, orb + opp_drb
)

df["dreb_pct"] = dividir(
    drb, drb + opp_orb
)

df["ftr"] = dividir(
    fta, fga
)

# Métricas de los rivales
df["opp_efg_pct"] = dividir(
    opp_fgm + 0.5 * df["opp_fieldGoalsMade3"],
    opp_fga
)

df["opp_ts_pct"] = dividir(
    df["opp_points"],
    2 * (opp_fga + 0.44 * opp_fta)
)

df["opp_tov_ratio"] = dividir(
    opp_tov,
    opp_fga + 0.44 * opp_fta
    + opp_ast + opp_tov
)

df["opp_orb_pct"] = dividir(
    opp_orb, opp_orb + drb
)

df["opp_dreb_pct"] = dividir(
    opp_drb, opp_drb + orb
)

df["opp_ftr"] = dividir(
    opp_fta, opp_fga
)

# Si un equipo aún no ha disputado partidos válidos,
# conservamos su fila pero sin métricas calculables.
metricas = [
    "pace", "offensive_rating",
    "defensive_rating", "net_rating",
    "two_point_pct", "three_point_pct",
    "free_throw_pct", "efg_pct", "ts_pct",
    "tov_ratio", "orb_pct", "dreb_pct",
    "ftr", "opp_efg_pct", "opp_ts_pct",
    "opp_tov_ratio", "opp_orb_pct",
    "opp_dreb_pct", "opp_ftr"
]

con_partidos = df["games_played"] > 0

if df.loc[con_partidos, metricas].isna().any().any():
    problemas = df.loc[
        con_partidos
        & df[metricas].isna().any(axis=1),
        ["season", "team_code", "round"]
    ]

    raise ValueError(
        "Hay métricas vacías en equipos con partidos:\n"
        + problemas.to_string(index=False)
    )

df[metricas] = df[metricas].round(4)

# Guardar resultado sin modificar los anteriores
df.to_csv(
    "2026_27_jornadas_metricas.csv",
    index=False
)

print("\nMÉTRICAS HISTÓRICAS CREADAS")
print("--------------------------")
print("Temporadas:", df["season"].nunique())
print("Equipos-temporada:",
      df.groupby(["season", "team_code"]).ngroups)
print("Filas:", len(df))
print("Columnas:", len(df.columns))
print(
    "Filas sin partidos todavía:",
    (df["games_played"] == 0).sum()
)
print("\nArchivo: 2026_27_jornadas_metricas.csv")
print("CÁLCULO COMPLETADO")

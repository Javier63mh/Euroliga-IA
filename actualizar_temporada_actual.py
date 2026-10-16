
from pathlib import Path
import pandas as pd
from euroleague import EuroleagueClient

SEASON_CODE = "E2026"
SEASON_NAME = "2026-27"

ARCHIVO = "2026_27_partidos_actuales.csv"

registros = []

with EuroleagueClient() as client:

    calendario = client.v2.games.list(
        "E",
        SEASON_CODE,
        phase_type_code="RS",
        limit=500
    )

    # Seleccionar únicamente partidos terminados
    partidos = [
        p for p in calendario["data"]
        if p.get("played") is True
        and p["local"].get("score") is not None
        and p["road"].get("score") is not None
    ]

    partidos.sort(
        key=lambda p: (p["round"], p["gameCode"])
    )

    print("\nACTUALIZANDO TEMPORADA 2026-27")
    print("-------------------------------")
    print("Partidos terminados:", len(partidos))

    for numero, partido in enumerate(partidos, 1):

        codigo = partido["gameCode"]

        estadisticas = client.v3.stats.get_game_stats(
            "E",
            SEASON_CODE,
            game_code=codigo
        )

        for lado, contrario in [
            ("local", "road"),
            ("road", "local")
        ]:

            datos = estadisticas[lado]["total"]
            datos_rival = estadisticas[contrario]["total"]

            puntos = partido[lado]["score"]
            puntos_rival = partido[contrario]["score"]

            if datos["points"] != puntos:
                raise ValueError(
                    f"Los puntos no coinciden: partido {codigo}"
                )

            fila = {
                "season": SEASON_NAME,
                "round": partido["round"],
                "game_code": codigo,
                "team_code": partido[lado]["club"]["code"],
                "opponent_code": partido[contrario]["club"]["code"],
                "win": int(puntos > puntos_rival)
            }

            for nombre, valor in datos.items():
                fila["stat_" + nombre] = valor

            for nombre, valor in datos_rival.items():
                fila["opp_" + nombre] = valor

            registros.append(fila)

        print(
            f"Descargados: {numero}/{len(partidos)}",
            end="\r"
        )

if not registros:
    raise ValueError(
        "Todavía no hay partidos con estadísticas disponibles"
    )

df = pd.DataFrame(registros)

# Comprobaciones de calidad
if len(df) != len(partidos) * 2:
    raise ValueError("Faltan registros de equipos")

if df.duplicated(["game_code", "team_code"]).any():
    raise ValueError("Hay equipos duplicados por partido")

if df["team_code"].nunique() != 20:
    raise ValueError(
        "No aparecen los 20 equipos. "
        "Comprueba si todos han disputado algún partido."
    )

# Guardar el archivo únicamente cuando esté validado
df.to_csv(ARCHIVO, index=False)

print("\n\nDATOS ACTUALES DESCARGADOS")
print("-------------------------")
print("Temporada:", SEASON_NAME)
print("Partidos:", df["game_code"].nunique())
print("Registros:", len(df))
print("Equipos:", df["team_code"].nunique())
print("Jornadas con partidos:", df["round"].nunique())
print("Archivo:", ARCHIVO)
print("\nACTUALIZACIÓN COMPLETADA")

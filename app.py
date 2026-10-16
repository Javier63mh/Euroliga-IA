
import pandas as pd
import streamlit as st
import subprocess
import sys
from pathlib import Path
import plotly.graph_objects as go
import os

MODO_PUBLICO = True

st.set_page_config(
    page_title="Euroliga IA | Temporada actual",
    page_icon="🏀",
    layout="wide"
)

NOMBRES = {
    "ASV": "LDLC ASVEL",
    "BAR": "FC Barcelona",
    "BAS": "Baskonia",
    "BES": "Besiktas",
    "DUB": "Dubai Basketball",
    "HTA": "Hapoel Tel Aviv",
    "IST": "Anadolu Efes",
    "MAD": "Real Madrid",
    "MIL": "Olimpia Milano",
    "MUN": "Bayern Múnich",
    "OLY": "Olympiacos",
    "PAM": "Valencia Basket",
    "PAN": "Panathinaikos",
    "PAR": "Partizan",
    "PRS": "Paris Basketball",
    "RED": "Estrella Roja",
    "TEL": "Maccabi Tel Aviv",
    "ULK": "Fenerbahçe",
    "VIR": "Virtus Bologna",
    "ZAL": "Zalgiris"
}

METRICAS = {
    "net_rating": "Diferencia de eficiencia",
    "offensive_rating": "Eficiencia ofensiva",
    "defensive_rating": "Eficiencia defensiva",
    "three_point_pct": "Acierto en triples",
    "efg_pct": "Eficiencia de tiro",
    "tov_ratio": "Ratio de pérdidas",
    "orb_pct": "Rebote ofensivo",
    "dreb_pct": "Rebote defensivo"
}

MENOR_ES_MEJOR = {
    "defensive_rating",
    "tov_ratio"
}

PORCENTAJES = {
    "three_point_pct",
    "efg_pct",
    "tov_ratio",
    "orb_pct",
    "dreb_pct"
}


@st.cache_data
def cargar_datos():
    actual = pd.read_csv(
    "predicciones_actuales_por_jornada.csv"
    )
    historico = pd.read_csv(
        "euroliga_dataset_entrenamiento.csv"
    )
    return actual, historico


# ACTUALIZAR RESULTADOS Y MODELOS
if not MODO_PUBLICO and st.button("🔄 Actualizar resultados y predicciones"):
    programas = [
        "actualizar_temporada_actual.py",
        "preparar_temporada_actual.py",
        "crear_metricas_actuales.py",
        "modelo_actual_por_jornada.py"
    ]

    carpeta = Path(__file__).resolve().parent

    with st.status(
        "Consultando Euroliga y recalculando la IA...",
        expanded=True
    ) as estado:

        try:
            for programa in programas:

                st.write(f"Ejecutando: {programa}")

                proceso = subprocess.run(
                    [sys.executable, str(carpeta / programa)],
                    cwd=carpeta,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    check=True
                )

            estado.update(
                label="Actualización completada",
                state="complete"
            )

        except subprocess.CalledProcessError as error:
            estado.update(
                label="Error durante la actualización",
                state="error"
            )

            st.error(
                f"Ha fallado el proceso: "
                f"{error.cmd}"
            )
            st.code(
                error.stderr or error.stdout
            )
            st.stop()

        except subprocess.TimeoutExpired:
            estado.update(
                label="Tiempo de espera agotado",
                state="error"
            )
            st.error(
                "La actualización ha tardado demasiado."
            )
            st.stop()

    # Evitar mostrar datos antiguos guardados en caché
    st.cache_data.clear()
    st.rerun()

actual, historico = cargar_datos()

# Validar los datos antes de mostrarlos
requeridas = [
    "season", "team_code", "round",
    "wins", "losses", "games_played",
    "net_rating", "probabilidad_playoffs"
] + list(METRICAS.keys())

faltantes = [
    c for c in requeridas
    if c not in actual.columns
]

if faltantes:
    st.error(f"Faltan columnas: {faltantes}")
    st.stop()

actual = actual[
    actual["season"] == "2026-27"
].copy()

if actual.empty:
    st.error("No hay datos para 2026-27.")
    st.stop()

jornada_maxima = int(actual["round"].max())

st.title("🏀 Euroliga IA")
st.subheader("Temporada actual · 2026-27")

st.caption(
    "Predicciones experimentales basadas en "
    "cinco temporadas históricas de Euroliga."
)

st.info(
    f"Datos disponibles hasta la jornada "
    f"{jornada_maxima}. "
    "Cada jornada utiliza el modelo C: "
    "entrenamiento con las jornadas históricas "
    "1 hasta la jornada analizada."
)

# SELECTORES
col1, col2 = st.columns(2)

codigos = sorted(actual["team_code"].unique())

with col1:
    codigo = st.selectbox(
        "Equipo",
        codigos,
        index=(
            codigos.index("MAD")
            if "MAD" in codigos else 0
        ),
        format_func=lambda x: NOMBRES.get(x, x)
    )

with col2:
    jornada = st.select_slider(
        "Jornada",
        options=sorted(actual["round"].unique()),
        value=jornada_maxima
    )

seleccion = actual[
    (actual["team_code"] == codigo)
    & (actual["round"] == jornada)
]

if seleccion.empty:
    st.warning("No hay datos para esa selección.")
    st.stop()

equipo = seleccion.iloc[0]

nombre_equipo = NOMBRES.get(codigo, codigo)

st.divider()
st.header(f"{nombre_equipo} · Jornada {jornada}")

# RESULTADOS PRINCIPALES
c1, c2, c3 = st.columns(3)

c1.metric(
    "Victorias",
    int(equipo["wins"])
)

c2.metric(
    "Derrotas",
    int(equipo["losses"])
)

c3.metric(
    "Net rating",
    f"{equipo['net_rating']:+.2f}"
)

st.subheader("🎯 Probabilidades estimadas")

p1, p2 = st.columns(2)

p1.metric(
    "🏀 Llegar a playoffs",
    f"{equipo['probabilidad_playoffs']:.1%}"
)

p2.metric(
    "🏆 Llegar a Final Four",
    f"{equipo['probabilidad_final_four']:.1%}"
)

if (
    equipo["probabilidad_final_four"]
    > equipo["probabilidad_playoffs"]
):
    st.warning(
        "Los modelos independientes han producido "
        "probabilidades incoherentes. Estas "
        "estimaciones necesitan revisión."
    )


if jornada <= 5:
    st.warning(
        "Estamos al principio de la temporada. "
        "Las probabilidades pueden cambiar mucho "
        "después de cada partido."
    )

if jornada > 8:
    st.caption(
        "Esta jornada utiliza el modelo C. "
        "La validación histórica que hemos realizado "
        "hasta ahora se centró en la jornada 4; "
        "su precisión aquí todavía debe evaluarse."
    )


# EXPLICACIÓN DE LAS PREDICCIONES DE LA IA
st.subheader("🧠 ¿Cómo se calculan estos porcentajes?")


with st.expander(
    "¿De dónde salen las probabilidades?",
    expanded=False
):
    st.write(
        "Euroliga IA utiliza dos modelos de regresión "
        "logística: uno para estimar la probabilidad "
        "de llegar a playoffs y otro para Final Four."
    )

    st.write(
        f"Para analizar la jornada {jornada} de "
        f"2026-27, entrenamos los modelos con las "
        f"estadísticas acumuladas de las jornadas "
        f"1 a {jornada} de las cinco temporadas "
        f"anteriores (2021-22 a 2025-26)."
    )

    st.write(
        "El modelo aprende qué características tenían "
        "los equipos que finalmente alcanzaron cada "
        "objetivo y los que no lo consiguieron. "
        "Después analiza las estadísticas actuales "
        "del equipo seleccionado hasta esa jornada."
    )

    st.write(
        "Se utilizan el porcentaje de victorias, "
        "las eficiencias ofensiva y defensiva, "
        "la diferencia de eficiencia, el acierto "
        "en tiros, las pérdidas, los rebotes y "
        "los partidos disputados."
    )

    st.caption(
        "Las estimaciones son experimentales y "
        "todavía necesitan más validación y "
        "calibración. Los factores que aparecen "
        "debajo indican su contribución matemática "
        "al modelo, no una relación causal."
    )


objetivo_ia = st.radio(
    "¿Qué predicción quieres explicar?",
    ["Playoffs", "Final Four"],
    horizontal=True,
    key="objetivo_explicacion_ia"
)

objetivo_codigo = (
    "playoffs"
    if objetivo_ia == "Playoffs"
    else "final_four"
)

NOMBRES_VARIABLES = {
    "games_played": "Partidos jugados",
    "win_pct": "Porcentaje de victorias",
    "net_rating": "Diferencia de eficiencia",
    "offensive_rating": "Eficiencia ofensiva",
    "defensive_rating": "Eficiencia defensiva",
    "three_point_pct": "Acierto en triples",
    "efg_pct": "Eficiencia de tiro",
    "tov_ratio": "Ratio de pérdidas",
    "orb_pct": "Rebote ofensivo",
    "dreb_pct": "Rebote defensivo",
    "num_teams": "Equipos participantes"
}

VARIABLES_PORCENTAJE = {
    "win_pct",
    "three_point_pct",
    "efg_pct",
    "tov_ratio",
    "orb_pct",
    "dreb_pct"
}

@st.cache_data
def cargar_explicaciones():
    return pd.read_csv(
        "explicaciones_modelos_por_jornada.csv"
    )

explicaciones = cargar_explicaciones()

explicacion = explicaciones[
    (explicaciones["team_code"] == codigo)
    & (explicaciones["round"] == jornada)
    & (explicaciones["objetivo"] == objetivo_codigo)
].copy()

if explicacion.empty:
    st.warning(
        "Todavía no hay una explicación disponible "
        "para esta selección."
    )
else:
    probabilidad = explicacion["probabilidad"].iloc[0]

    st.write(
        f"**Probabilidad estimada de {objetivo_ia}: "
        f"{probabilidad:.1%}**"
    )

    
    # RESUMEN AUTOMÁTICO DE LA PREDICCIÓN
    st.markdown("#### 📝 Resumen")

    # El número de equipos es una característica
    # de la competición, no del rendimiento deportivo.
    factores_deportivos = explicacion[
        ~explicacion["variable"].isin(
            ["num_teams", "games_played"]
        )
    ].copy()

    favorables = factores_deportivos[
        factores_deportivos["contribucion_logit"] > 0
    ].sort_values(
        "contribucion_logit",
        ascending=False
    )

    desfavorables = factores_deportivos[
        factores_deportivos["contribucion_logit"] < 0
    ].sort_values("contribucion_logit")

    def nombre_variable(variable):
        return NOMBRES_VARIABLES.get(
            variable, variable
        ).lower()

    def describir_factor(fila):
        variable = fila["variable"]
        valor = float(fila["valor"])

        if variable in VARIABLES_PORCENTAJE:
            valor_texto = f"{valor:.1%}"
        else:
            valor_texto = f"{valor:.2f}"

        return (
            f"{nombre_variable(variable)} "
            f"({valor_texto})"
        )

    factores_positivos = [
        describir_factor(fila)
        for _, fila in favorables.head(2).iterrows()
    ]

    factores_negativos = [
        describir_factor(fila)
        for _, fila in desfavorables.head(2).iterrows()
    ]

    texto = (
        f"En la jornada {jornada}, {nombre_equipo} "
        f"presenta una probabilidad experimental de "
        f"{objetivo_ia.lower()} del {probabilidad:.1%}. "
    )

    if factores_negativos:
        texto += (
            "Los factores deportivos que más reducen "
            "el cálculo del modelo son "
            + " y ".join(factores_negativos)
            + ". "
        )

    if factores_positivos:
        texto += (
            "Los factores que más favorecen la "
            "predicción son "
            + " y ".join(factores_positivos)
            + "."
        )

    st.write(texto)

    st.caption(
        "Este resumen describe las contribuciones "
        "matemáticas del modelo, no demuestra "
        "relaciones de causa y efecto."
    )

   
    # Separar las estadísticas deportivas del
    # contexto general de la competición
    explicacion_deportiva = explicacion[
        ~explicacion["variable"].isin(
            ["num_teams", "games_played"]
        )
    ].copy()

    # Principales factores favorables
    positivas = explicacion_deportiva[
        explicacion_deportiva["contribucion_logit"] > 0
    ].sort_values(
        "contribucion_logit",
        ascending=False
    ).head(3)

    # Principales factores desfavorables
    negativas = explicacion_deportiva[
        explicacion_deportiva["contribucion_logit"] < 0
    ].sort_values(
        "contribucion_logit"
    ).head(3)


    def mostrar_factor(fila):
        variable = fila["variable"]
        nombre = NOMBRES_VARIABLES.get(
            variable, variable
        )
        valor = fila["valor"]
        contribucion = fila["contribucion_logit"]

        if variable in VARIABLES_PORCENTAJE:
            valor_texto = f"{valor:.1%}"
        elif variable in {"games_played", "num_teams"}:
            valor_texto = f"{valor:.0f}"
        else:
            valor_texto = f"{valor:.2f}"

        st.write(
            f"**{nombre}: {valor_texto}**"
        )
        st.caption(
            "Contribución al modelo: "
            f"{contribucion:+.3f} (escala logit)"
        )

    izquierda_ia, derecha_ia = st.columns(2)

    with izquierda_ia:
        st.success("Factores que favorecen la predicción")

        if positivas.empty:
            st.write("No hay contribuciones positivas.")
        else:
            for _, fila in positivas.iterrows():
                mostrar_factor(fila)

    with derecha_ia:
        st.warning("Factores que reducen la predicción")

        if negativas.empty:
            st.write("No hay contribuciones negativas.")
        else:
            for _, fila in negativas.iterrows():
                mostrar_factor(fila)

    st.caption(
        "Las contribuciones se calculan respecto a "
        "la referencia interna del modelo. "
        "No equivalen a puntos porcentuales ni "
        "demuestran relaciones de causa y efecto. "
        "Algunas variables están relacionadas entre sí."
    )


st.subheader("📈 Evolución de las probabilidades")

evolucion = actual[
    actual["team_code"] == codigo
].sort_values("round")

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=evolucion["round"],
        y=evolucion["probabilidad_playoffs"],
        mode="lines+markers",
        name="Playoffs",
        line=dict(color="blue", width=3)
    )
)

fig.add_trace(
    go.Scatter(
        x=evolucion["round"],
        y=evolucion["probabilidad_final_four"],
        mode="lines+markers",
        name="Final Four",
        line=dict(color="red", width=3)
    )
)

fig.update_layout(
    xaxis_title="Jornada",
    yaxis_title="Probabilidad",
    yaxis=dict(
        tickformat=".0%",
        range=[0, 1]
    ),
    hovermode="x unified",
    legend_title="Objetivo"
)

st.plotly_chart(fig, use_container_width=True)

# COMPARACIÓN CON LOS PLAYOFFS HISTÓRICOS
st.subheader("📊 Comparación con equipos históricos")

objetivo = st.radio(
    "¿Qué objetivo quieres analizar?",
    ["Playoffs", "Final Four"],
    horizontal=True
)

if objetivo == "Playoffs":
    columna_objetivo = "playoffs"
else:
    columna_objetivo = "final_four"

st.write(
    f"Comparamos a {nombre_equipo} con los equipos "
    f"de las cinco temporadas anteriores que "
    f"alcanzaron {objetivo}."
)

referencia = historico[
    (historico["season"] < "2026-27")
    & (historico["round"] == jornada)
    & (historico["games_played"] > 0)
].copy()

clasificados = referencia[
    referencia[columna_objetivo] == 1
]

no_clasificados = referencia[
    referencia[columna_objetivo] == 0
]

filas = []
fortalezas = []
debilidades = []

for columna, nombre in METRICAS.items():

    valor = float(equipo[columna])

    media_si = clasificados[columna].mean()
    media_no = no_clasificados[columna].mean()

    desviacion = referencia[columna].std()

    diferencia = valor - media_si

    if columna in MENOR_ES_MEJOR:
        diferencia = -diferencia

    if pd.isna(desviacion) or desviacion == 0:
        distancia = 0
    else:
        distancia = diferencia / desviacion

    if distancia >= 0.25:
        estado = "Fortaleza"
        fortalezas.append((nombre, distancia))
    elif distancia <= -0.25:
        estado = "A mejorar"
        debilidades.append((nombre, distancia))
    else:
        estado = "Similar"

    if columna in PORCENTAJES:
        formato = lambda x: f"{x:.1%}"
    else:
        formato = lambda x: f"{x:.2f}"

    filas.append({
        "Estadística": nombre,
        "Equipo actual": formato(valor),
        f"{objetivo} históricos": formato(media_si),
        "Resto de equipos": formato(media_no),
        "Evaluación": estado
    })

st.dataframe(
    pd.DataFrame(filas),
    hide_index=True,
    use_container_width=True
)


# RECOMENDACIONES BASADAS EN EL HISTÓRICO
st.subheader("🎯 ¿Qué necesita mejorar el equipo?")

recomendaciones = []

for columna, nombre in METRICAS.items():

    valor = float(equipo[columna])
    referencia_media = float(
        clasificados[columna].mean()
    )

    if columna in MENOR_ES_MEJOR:
        diferencia = referencia_media - valor
    else:
        diferencia = valor - referencia_media

    desviacion = referencia[columna].std()

    if pd.isna(desviacion) or desviacion == 0:
        continue

    distancia = diferencia / desviacion

    if distancia < -0.25:
        recomendaciones.append({
            "nombre": nombre,
            "columna": columna,
            "valor": valor,
            "referencia": referencia_media,
            "distancia": distancia
        })

recomendaciones.sort(
    key=lambda x: x["distancia"]
)

if not recomendaciones:
    st.success(
        "El equipo no presenta grandes diferencias "
        "negativas frente al perfil histórico seleccionado."
    )
else:
    for item in recomendaciones[:3]:

        nombre = item["nombre"]
        valor = item["valor"]
        media = item["referencia"]
        columna = item["columna"]

        if columna in PORCENTAJES:
            texto_valor = f"{valor:.1%}"
            texto_media = f"{media:.1%}"
            diferencia = (
                f"{(valor - media) * 100:+.1f} "
                "puntos porcentuales"
            )
        else:
            texto_valor = f"{valor:.2f}"
            texto_media = f"{media:.2f}"
            diferencia = f"{valor - media:+.2f}"

        st.write(f"**⚠️ {nombre}**")

        st.write(
            f"Equipo: {texto_valor} | "
            f"Referencia de {objetivo}: {texto_media}"
        )

        st.caption(
            f"Diferencia respecto a la referencia: "
            f"{diferencia}. "
            "Es una comparación estadística, "
            "no una mejora garantizada de la probabilidad."
        )

# FORTALEZAS Y DEBILIDADES
st.subheader("🧠 Análisis del equipo")

fortalezas.sort(
    key=lambda x: x[1],
    reverse=True
)

debilidades.sort(
    key=lambda x: x[1]
)

izquierda, derecha = st.columns(2)

with izquierda:
    st.success("Fortalezas estadísticas")

    if fortalezas:
        for nombre, _ in fortalezas[:3]:
            st.write(f"✅ {nombre}")
    else:
        st.write("Sin fortalezas destacadas.")

with derecha:
    st.warning("Aspectos a mejorar")

    if debilidades:
        for nombre, _ in debilidades[:3]:
            st.write(f"⚠️ {nombre}")
    else:
        st.write("Sin debilidades destacadas.")

st.caption(
    f"Comparación descriptiva con los equipos "
    f"históricos que alcanzaron {objetivo}, "
    f"utilizando sus estadísticas hasta la jornada "
    f"{jornada}. Las diferencias no demuestran "
    f"causalidad ni representan las contribuciones "
    f"directas del modelo predictivo."
)

st.divider()

st.caption(
    "Euroliga IA · Versión experimental. "
    "Las probabilidades de playoffs y Final Four "
    "todavía no están calibradas completamente. "
    "No se ofrecen predicciones de campeón."
)

import dash
from dash import dcc, html, Input, Output, dash_table
import pandas as pd

# ————————————— Parámetros y datos —————————————
XLSX_PATH = "scrims_actualizado.xlsx"
xls = pd.ExcelFile(XLSX_PATH)

# Leer cada hoja, saltar 3 filas y tomar 14 columnas
sheets = {
    name: pd.read_excel(
        XLSX_PATH,
        sheet_name=name,
        header=None,
        skiprows=3,
        usecols=list(range(14))
    )
    for name in xls.sheet_names
}

def make_df(sheet_df):
    records = []
    for _, r in sheet_df.iterrows():
        t1, t2, w = list(r.iloc[0:3]), list(r.iloc[3:6]), r.iloc[6]
        records.append({"team1": t1, "team2": t2, "winner": w})
    return pd.DataFrame(records)

data = {name: make_df(df) for name, df in sheets.items()}

# Combina varios mapas
def get_multi_data(mapas):
    dfs = [data[m] for m in mapas if m in data]
    return pd.concat(dfs, ignore_index=True)

# Filtrado principal
def filter_df(df, main, comp1, comp2, rivals, exclude):
    d = df.copy()
    if exclude:
        d = d[d.apply(lambda r: all(b not in (r["team1"] + r["team2"]) for b in exclude), axis=1)]

    if main:
        mask = d.apply(lambda r: main in (r["team1"] + r["team2"]), axis=1)
        d = d[mask]
        def split(r):
            if main in r["team1"]:
                return pd.Series({"team": r["team1"], "opp": r["team2"], "win": r["winner"]=="Equipo 1"})
            else:
                return pd.Series({"team": r["team2"], "opp": r["team1"], "win": r["winner"]=="Equipo 2"})
        aux = d.apply(split, axis=1)
        d = pd.concat([d, aux], axis=1)
    else:
        d["team"] = None; d["opp"] = None; d["win"] = None

    if comp1:
        d = d[d["team"].apply(lambda t: comp1 in t)]
    if comp2:
        d = d[d["team"].apply(lambda t: comp2 in t)]

    for key in ("r1", "r2", "r3"):
        val = rivals.get(key)
        if val:
            d = d[d["opp"].apply(lambda o: val in o)]
    return d

app = dash.Dash(__name__)
server = app.server

# ————————————— Layout —————————————
app.layout = html.Div(style={"margin":"20px"}, children=[
    html.H1("Winrate Analyzer por Mapa"),

    html.Div([
        html.Label("1) Selecciona uno o más mapas"),
        dcc.Dropdown(
            id="map-dropdown",
            options=[{"label": m, "value": m} for m in data],
            value=[list(data.keys())[0]],
            multi=True,
            style={"width":"400px"}
        )
    ]),

    html.Div([
        html.Label("8) Excluir brawlers de análisis"),
        dcc.Dropdown(id="excluded-dropdown", multi=True, style={"width":"400px"})
    ]),

    html.H2("Winrate global de brawlers en los mapas seleccionados"),
    html.Div(id="winrate-global"),
    
    html.Hr(),

    html.Div([
        html.Div([
            html.Label("2) Brawler principal"),
            dcc.Dropdown(id="main-dropdown", clearable=True, style={"width":"250px"})
        ], style={"display":"inline-block", "marginRight":"40px"}),

        html.Div([
            html.Label("3) Compañero 1"),
            dcc.Dropdown(id="comp1-dropdown", clearable=True, style={"width":"250px"})
        ], style={"display":"inline-block", "marginRight":"40px"}),

        html.Div([
            html.Label("4) Compañero 2"),
            dcc.Dropdown(id="comp2-dropdown", clearable=True, style={"width":"250px"})
        ], style={"display":"inline-block"})
    ]),

    html.Div(style={"marginTop":"20px"}, children=[
        html.Div([
            html.Label("5) Rival 1"),
            dcc.Dropdown(id="r1-dropdown", clearable=True, style={"width":"250px"})
        ], style={"display":"inline-block", "marginRight":"40px"}),
        html.Div([
            html.Label("6) Rival 2"),
            dcc.Dropdown(id="r2-dropdown", clearable=True, style={"width":"250px"})
        ], style={"display":"inline-block", "marginRight":"40px"}),
        html.Div([
            html.Label("7) Rival 3"),
            dcc.Dropdown(id="r3-dropdown", clearable=True, style={"width":"250px"})
        ], style={"display":"inline-block"}),
        html.Div([
            html.Label("9) Brawlers baneados"),
            dcc.Dropdown(id="baneados-dropdown",
                options=[{"label": b, "value": b} for b in sorted({b for df in data.values() for r in df.itertuples() for b in r[1] + r[2]})],
                multi=True,
                placeholder="Selecciona los brawlers baneados",
                style={"width": "400px"}
            )
        ]),
        html.H2("🧠 Sugerencia de primer pick"),
        html.Div(id="primer-pick-sugerido", style={"fontWeight": "bold", "fontSize": "20px", "marginTop": "10px"})

        
    ]),

    html.H2("Winrate del brawler principal en el subconjunto"),
    html.Div(id="main-winrate"),

    html.H2("Tabla de Compañeros"),
    dash_table.DataTable(
        id="companions-table",
        columns=[
            {"name":"Compañero", "id":"brawler"},
            {"name":"Partidas juntos", "id":"games"},
            {"name":"Victorias juntos", "id":"wins"},
            {"name":"Winrate (%)", "id":"wr"}
        ],
        style_cell={"textAlign":"center"},
        style_header={"fontWeight":"bold"},
        page_size=10,
        style_data_conditional=[
            {"if":{"column_id":"wr","filter_query":"{wr} < 25"},
            "backgroundColor":"#8B0000","color":"white"},
            {"if":{"column_id":"wr","filter_query":"{wr} >= 25 && {wr} < 45"},
            "backgroundColor":"#FF6347","color":"black"},
            {"if":{"column_id":"wr","filter_query":"{wr} >= 45 && {wr} < 55"},
            "backgroundColor":"#FFFF00","color":"black"},
            {"if":{"column_id":"wr","filter_query":"{wr} >= 55 && {wr} < 70"},
            "backgroundColor":"#90EE90","color":"black"},
            {"if":{"column_id":"wr","filter_query":"{wr} >= 70"},
            "backgroundColor":"#006400","color":"white"},
        ]
    ),

    html.H2("Tabla de Rivales"),
    dash_table.DataTable(
        id="rivals-table",
        columns=[
            {"name":"Rival", "id":"brawler"},
            {"name":"Partidas vs", "id":"games"},
            {"name":"Victorias vs", "id":"wins_vs"},
            {"name":"Winrate (%)", "id":"wr_vs"}
        ],
        style_cell={"textAlign":"center"},
        style_header={"fontWeight":"bold"},
        page_size=10,
        style_data_conditional=[
            {"if": {"column_id": "wr_vs", "filter_query": "{wr_vs} < 25"},
             "backgroundColor": "#8B0000", "color": "white"},
            {"if": {"column_id": "wr_vs", "filter_query": "{wr_vs} >= 25 && {wr_vs} < 45"},
             "backgroundColor": "#FF6347", "color": "black"},
            {"if": {"column_id": "wr_vs", "filter_query": "{wr_vs} >= 45 && {wr_vs} < 55"},
             "backgroundColor": "#FFFF00", "color": "black"},
            {"if": {"column_id": "wr_vs", "filter_query": "{wr_vs} >= 55 && {wr_vs} < 70"},
             "backgroundColor": "#90EE90", "color": "black"},
            {"if": {"column_id": "wr_vs", "filter_query": "{wr_vs} >= 70"},
             "backgroundColor": "#006400", "color": "white"},
        ]
    ),

    html.H2("Comparativa por Mapa"),
    html.Div(id="map-comparison-table")
])
from itertools import combinations
import math

def ajustar_confianza(winrate, partidas):
    if partidas < 5:
        return winrate * 0.5
    elif partidas < 20:
        return winrate * 0.75
    else:
        return winrate

def calcular_peso(combo, partidas, wr_combo, wr_global):
    profundidad = (len(combo) / 6) ** 1.2
    volumen = min(math.sqrt(partidas), 10) / 10
    impacto = max((wr_combo - wr_global) / wr_global, 0)
    return profundidad * volumen * (1 + impacto)

def wr_ponderado_contextual(brawler, mapas, banned, df_global):
    combos = [c for i in range(1, len(banned)+1) for c in combinations(banned, i)]
    total_wr = 0
    total_peso = 0

    df_multi = get_multi_data(mapas)
    wr_global = df_global.get(brawler, {}).get("wr", 0)

    for combo in combos:
        df_filtrado = df_multi[df_multi.apply(lambda r: all(x not in r["team1"] + r["team2"] for x in combo), axis=1)]
        partidas = df_filtrado.apply(lambda r: brawler in r["team1"] + r["team2"], axis=1).sum()
        victorias = df_filtrado.apply(lambda r: (
            (r["winner"] == "Equipo 1" and brawler in r["team1"]) or
            (r["winner"] == "Equipo 2" and brawler in r["team2"])
        ), axis=1).sum()
        if partidas == 0:
            continue
        wr_combo = victorias / partidas * 100
        peso = calcular_peso(combo, partidas, wr_combo, wr_global)

        total_wr += wr_combo * peso
        total_peso += peso

    return total_wr / total_peso if total_peso > 0 else wr_global

@app.callback(
    Output("excluded-dropdown", "options"),
    Input("map-dropdown", "value")
)
def update_excluded_options(mapas):
    df = get_multi_data(mapas)
    brawlers = sorted({b for _, r in df.iterrows() for b in r["team1"] + r["team2"]})
    return [{"label": b, "value": b} for b in brawlers]

@app.callback(
    Output("comp1-dropdown", "options"),
    Output("comp1-dropdown", "value"),
    Input("map-dropdown", "value"),
    Input("main-dropdown", "value"),
    Input("excluded-dropdown", "value")
)
def update_comp1(mapas, main, exclude):
    if not mapas or not main:
        return [], None

    df = get_multi_data(mapas)
    df1 = filter_df(df, main, None, None, {}, exclude or [])
    comps = sorted({b for lst in df1["team"].dropna() for b in lst if b != main})
    return [{"label": b, "value": b} for b in comps], None

@app.callback(
    Output("comp2-dropdown", "options"),
    Output("comp2-dropdown", "value"),
    Input("map-dropdown", "value"),
    Input("main-dropdown", "value"),
    Input("excluded-dropdown", "value")
)
def update_comp2(mapas, main, exclude):
    if not mapas or not main:
        return [], None

    df = get_multi_data(mapas)
    df1 = filter_df(df, main, None, None, {}, exclude or [])
    comps = sorted({b for lst in df1["team"].dropna() for b in lst if b != main})
    return [{"label": b, "value": b} for b in comps], None

@app.callback(
    Output("r1-dropdown", "options"),
    Output("r1-dropdown", "value"),
    Input("map-dropdown", "value"),
    Input("main-dropdown", "value"),
    Input("excluded-dropdown", "value")
)
def update_r1(mapas, main, exclude):
    if not mapas or not main:
        return [], None

    df = get_multi_data(mapas)
    df1 = filter_df(df, main, None, None, {}, exclude or [])
    rivals = sorted({b for lst in df1["opp"].dropna() for b in lst})
    return [{"label": b, "value": b} for b in rivals], None

@app.callback(
    Output("r2-dropdown", "options"),
    Output("r2-dropdown", "value"),
    Input("map-dropdown", "value"),
    Input("main-dropdown", "value"),
    Input("excluded-dropdown", "value")
)
def update_r2(mapas, main, exclude):
    if not mapas or not main:
        return [], None

    df = get_multi_data(mapas)
    df1 = filter_df(df, main, None, None, {}, exclude or [])
    rivals = sorted({b for lst in df1["opp"].dropna() for b in lst})
    return [{"label": b, "value": b} for b in rivals], None

@app.callback(
    Output("r3-dropdown", "options"),
    Output("r3-dropdown", "value"),
    Input("map-dropdown", "value"),
    Input("main-dropdown", "value"),
    Input("excluded-dropdown", "value")
)
def update_r3(mapas, main, exclude):
    if not mapas or not main:
        return [], None

    df = get_multi_data(mapas)
    df1 = filter_df(df, main, None, None, {}, exclude or [])
    rivals = sorted({b for lst in df1["opp"].dropna() for b in lst})
    return [{"label": b, "value": b} for b in rivals], None



@app.callback(
    Output("main-dropdown","options"),
    Output("main-dropdown","value"),
    Output("winrate-global","children"),
    Input("map-dropdown","value"),
    Input("excluded-dropdown","value")
)
def update_main_and_global(mapas, exclude):
    df = get_multi_data(mapas)
    if exclude:
        df = df[df.apply(lambda r: all(b not in (r["team1"] + r["team2"]) for b in exclude), axis=1)]

    df2 = df[df["winner"]!="Empate"]
    counts = {}
    for _, r in df2.iterrows():
        for b in r["team1"] + r["team2"]:
            counts.setdefault(b, {"g":0,"v":0})
            counts[b]["g"] += 1
        if r["winner"] == "Equipo 1":
            for b in r["team1"]: counts[b]["v"] += 1
        elif r["winner"] == "Equipo 2":
            for b in r["team2"]: counts[b]["v"] += 1

    gl = pd.DataFrame([
        {"Brawler": b, "Partidas": v["g"], "Victorias": v["v"],
         "WR": 0 if v["g"]==0 else v["v"]/v["g"]*100}
        for b, v in counts.items()
    ])
    gl = gl.sort_values(["Partidas","WR"], ascending=[False,False]).reset_index(drop=True)

    tabla = dash_table.DataTable(
        columns=[
            {"name":"Brawler","id":"Brawler"},
            {"name":"Partidas","id":"Partidas"},
            {"name":"Victorias","id":"Victorias"},
            {"name":"Winrate (%)","id":"WR","type":"numeric","format":{"specifier":".1f"}}
        ],
        data=gl.to_dict("records"),
        style_cell={"textAlign":"center"},
        style_header={"fontWeight":"bold"},
        page_size=10,
        style_data_conditional=[
            {"if":{"column_id":"WR","filter_query":"{WR} < 25"},
             "backgroundColor":"#8B0000","color":"white"},
            {"if":{"column_id":"WR","filter_query":"{WR} >= 25 && {WR} < 45"},
             "backgroundColor":"#FF6347","color":"black"},
            {"if":{"column_id":"WR","filter_query":"{WR} >= 45 && {WR} < 55"},
             "backgroundColor":"#FFFF00","color":"black"},
            {"if":{"column_id":"WR","filter_query":"{WR} >= 55 && {WR} < 70"},
             "backgroundColor":"#90EE90","color":"black"},
            {"if":{"column_id":"WR","filter_query":"{WR} >= 70"},
             "backgroundColor":"#006400","color":"white"},
        ]
    )

    opts = [{"label": b, "value": b} for b in gl["Brawler"]]
    return opts, None, tabla

@app.callback(
    Output("main-winrate", "children"),
    Output("companions-table", "data"),
    Output("rivals-table", "data"),
    Input("map-dropdown", "value"),
    Input("main-dropdown", "value"),
    Input("comp1-dropdown", "value"),
    Input("comp2-dropdown", "value"),
    Input("r1-dropdown", "value"),
    Input("r2-dropdown", "value"),
    Input("r3-dropdown", "value"),
    Input("excluded-dropdown", "value")
)
def update_tables(mapas, main, c1, c2, r1, r2, r3, exclude):
    df_sub = filter_df(get_multi_data(mapas), main, c1, c2,
                       {"r1": r1, "r2": r2, "r3": r3}, exclude or [])
    df_nd = df_sub[df_sub["winner"] != "Empate"]

    if main:
        total = len(df_nd)
        wins = df_nd["win"].sum()
        wr = 0 if total == 0 else wins / total * 100
        wr_text = f"{main}: {wins}/{total} = {wr:.1f}%"
    else:
        wr_text = "Selecciona un brawler principal"

    comp_data = []
    if main:
        comps = sorted({b for t in df_nd["team"].dropna() for b in t if b not in (main, c1, c2)})
        for b in comps:
            games = df_nd["team"].apply(lambda t: b in t).sum()
            wins_ = df_nd.apply(lambda r: b in r["team"] and r["win"], axis=1).sum()
            wr_ = 0 if games == 0 else wins_ / games * 100
            comp_data.append({"brawler": b, "games": int(games),
                              "wins": int(wins_), "wr": round(wr_, 1)})
        comp_data = sorted(comp_data, key=lambda x: (-x["games"], -x["wr"]))

    riv_data = []
    if main:
        rivs = sorted({b for o in df_nd["opp"].dropna() for b in o})
        for b in rivs:
            games = df_nd["opp"].apply(lambda o: b in o).sum()
            wins_vs = df_nd.apply(lambda r: b in r["opp"] and r["win"], axis=1).sum()
            wr_vs = 0 if games == 0 else wins_vs / games * 100
            riv_data.append({"brawler": b, "games": int(games),
                             "wins_vs": int(wins_vs), "wr_vs": round(wr_vs, 1)})
        riv_data = sorted(riv_data, key=lambda x: (-x["games"], -x["wr_vs"]))

    return wr_text, comp_data, riv_data

@app.callback(
    Output("map-comparison-table", "children"),
    Input("map-dropdown", "value"),
    Input("main-dropdown", "value"),
    Input("comp1-dropdown", "value"),
    Input("comp2-dropdown", "value"),
    Input("r1-dropdown", "value"),
    Input("r2-dropdown", "value"),
    Input("r3-dropdown", "value"),
    Input("excluded-dropdown", "value")
)
def update_map_comparison(mapas, main, c1, c2, r1, r2, r3, exclude):
    if not mapas or not main:
        return ""

    tabla = []
    for m in mapas:
        try:
            df = data.get(m)
            if df is None or df.empty:
                continue

            df_filtered = filter_df(df, main, c1, c2,
                                    {"r1": r1, "r2": r2, "r3": r3},
                                    exclude or [])

            df_nd = df_filtered[df_filtered["winner"] != "Empate"]
            total = len(df_nd)
            wins = df_nd["win"].sum() if "win" in df_nd.columns else 0
            wr = 0.0 if total == 0 else wins / total * 100

            tabla.append({
                "mapa": m,
                "partidas": total,
                "victorias": int(wins),
                "winrate": round(wr, 1)
            })
        except Exception as e:
            print(f"⚠️ Error en mapa {m}: {e}")
            continue

    if not tabla:
        return html.Div("No hay datos suficientes para mostrar la comparativa.")

    df_tabla = pd.DataFrame(tabla).sort_values(["partidas", "winrate"], ascending=[False, False])
    return dash_table.DataTable(
        columns=[
            {"name": "Mapa", "id": "mapa"},
            {"name": "Partidas", "id": "partidas"},
            {"name": "Victorias", "id": "victorias"},
            {"name": "Winrate (%)", "id": "winrate"}
        ],
        data=df_tabla.to_dict("records"),
        style_cell={"textAlign": "center"},
        style_header={"fontWeight": "bold"},
        page_size=10,
        style_data_conditional=[
            {"if": {"column_id": "winrate", "filter_query": "{partidas} = 0"},
             "backgroundColor": "#A9A9A9", "color": "white"},
            {"if": {"column_id": "winrate", "filter_query": "{winrate} < 25 && {partidas} > 0"},
             "backgroundColor": "#8B0000", "color": "white"},
            {"if": {"column_id": "winrate", "filter_query": "{winrate} >= 25 && {winrate} < 45"},
             "backgroundColor": "#FF6347", "color": "black"},
            {"if": {"column_id": "winrate", "filter_query": "{winrate} >= 45 && {winrate} < 55"},
             "backgroundColor": "#FFFF00", "color": "black"},
            {"if": {"column_id": "winrate", "filter_query": "{winrate} >= 55 && {winrate} < 70"},
             "backgroundColor": "#90EE90", "color": "black"},
            {"if": {"column_id": "winrate", "filter_query": "{winrate} >= 70"},
             "backgroundColor": "#006400", "color": "white"},
        ]
    )

@app.callback(
    Output("primer-pick-sugerido", "children"),
    Input("map-dropdown", "value"),
    Input("baneados-dropdown", "value"),
    Input("excluded-dropdown", "value")
)
@app.callback(
    Output("primer-pick-sugerido", "children"),
    Input("map-dropdown", "value"),
    Input("baneados-dropdown", "value"),
    Input("excluded-dropdown", "value")
)
def sugerir_primer_pick(mapas, baneados, excluidos):
    df = get_multi_data(mapas)
    df2 = df[df["winner"] != "Empate"]
    brawlers = sorted({b for _, r in df2.iterrows() for b in r["team1"] + r["team2"]
                       if b not in (baneados or []) + (excluidos or [])})

    # Diccionario con WR global y partidas
    counts = {}
    for _, r in df2.iterrows():
        for b in r["team1"] + r["team2"]:
            if b in (baneados or []) + (excluidos or []):
                continue
            counts.setdefault(b, {"g": 0, "v": 0})
            counts[b]["g"] += 1
            if r["winner"] == "Equipo 1" and b in r["team1"]:
                counts[b]["v"] += 1
            elif r["winner"] == "Equipo 2" and b in r["team2"]:
                counts[b]["v"] += 1

    df_global = {
        b: {"wr": v["v"] / v["g"] * 100 if v["g"] > 0 else 0, "games": v["g"]}
        for b, v in counts.items()
    }

    ranking = []
    for b in brawlers:
        wr_mapa = df_global[b]["wr"]
        partidas_mapa = df_global[b]["games"]
        wr_mapa_conf = ajustar_confianza(wr_mapa, partidas_mapa)
        wr_contextual = wr_ponderado_contextual(b, mapas, baneados or [], df_global)

        score = 0.4 * wr_mapa_conf + 0.6 * wr_contextual  # Puedes ajustar la ponderación
        ranking.append((b, round(score, 2)))

    top5 = sorted(ranking, key=lambda x: -x[1])[:5]

    if top5:
        resultado = "🔍 **Top 5 brawlers sugeridos para primer pick:**\n\n"
        resultado += "\n".join(
            [f"{i+1}. **{b}** → {score}%" for i, (b, score) in enumerate(top5)]
        )
        return resultado
    else:
        return "No hay datos suficientes para sugerir un primer pick."

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8080)

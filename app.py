import dash
from dash import dcc, html, Input, Output, dash_table
import pandas as pd

# ————————————— Parámetros y datos —————————————
XLSX_PATH = "scrims_actualizado.xlsx"
xls = pd.ExcelFile(XLSX_PATH)

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

def get_multi_data(mapas):
    dfs = [data[m] for m in mapas if m in data]
    return pd.concat(dfs, ignore_index=True)

def filter_df(df, main, comp1, comp2, rivals, excluded=None):
    d = df.copy()

    if excluded:
        d = d[~d.apply(lambda r: any(b in (r["team1"] + r["team2"]) for b in excluded), axis=1)]

    if main:
        mask = d.apply(lambda r: main in (r["team1"] + r["team2"]), axis=1)
        d = d[mask]
        def split(r):
            if main in r["team1"]:
                return pd.Series({"team": r["team1"], "opp": r["team2"], "win": r["winner"] == "Equipo 1"})
            else:
                return pd.Series({"team": r["team2"], "opp": r["team1"], "win": r["winner"] == "Equipo 2"})
        aux = d.apply(split, axis=1)
        d = pd.concat([d, aux], axis=1)
    else:
        d["team"], d["opp"], d["win"] = None, None, None

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
app.layout = html.Div(style={"margin": "20px"}, children=[
    html.H1("Winrate Analyzer por Mapa"),

    html.Label("1) Selecciona uno o más mapas"),
    dcc.Dropdown(id="map-dropdown", multi=True, style={"width": "400px"}),

    html.H2("Winrate global de brawlers en los mapas seleccionados"),
    html.Div(id="winrate-global"),

    html.Hr(),

    html.Label("2) Brawler principal"),
    dcc.Dropdown(id="main-dropdown", clearable=True, style={"width": "250px"}),

    html.Label("3) Compañero 1"),
    dcc.Dropdown(id="comp1-dropdown", clearable=True, style={"width": "250px"}),

    html.Label("4) Compañero 2"),
    dcc.Dropdown(id="comp2-dropdown", clearable=True, style={"width": "250px"}),

    html.Label("5) Rival 1"),
    dcc.Dropdown(id="r1-dropdown", clearable=True, style={"width": "250px"}),

    html.Label("6) Rival 2"),
    dcc.Dropdown(id="r2-dropdown", clearable=True, style={"width": "250px"}),

    html.Label("7) Rival 3"),
    dcc.Dropdown(id="r3-dropdown", clearable=True, style={"width": "250px"}),

    html.Label("8) Brawlers a excluir"),
    dcc.Dropdown(id="exclude-dropdown", multi=True, style={"width": "400px"}),

    html.H2("Winrate del brawler principal en el subconjunto"),
    html.Div(id="main-winrate"),

    html.H2("Tabla de Compañeros"),
    dash_table.DataTable(id="companions-table", page_size=10),

    html.H2("Tabla de Rivales"),
    dash_table.DataTable(id="rivals-table", page_size=10),

    html.H2("Comparativa por Mapa"),
    html.Div(id="map-comparison-table")
])

# ————————————— Callbacks —————————————

@app.callback(
    Output("main-dropdown", "options"),
    Output("main-dropdown", "value"),
    Output("winrate-global", "children"),
    Output("exclude-dropdown", "options"),
    Input("map-dropdown", "value")
)
def update_main_and_global(mapas):
    if not mapas: return [], None, "", []
    df = get_multi_data(mapas)
    df2 = df[df["winner"] != "Empate"]
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
    gl = gl.sort_values(["Partidas", "WR"], ascending=[False, False]).reset_index(drop=True)

    tabla = dash_table.DataTable(
        columns=[{"name": col, "id": col} for col in gl.columns],
        data=gl.to_dict("records"),
        page_size=10,
        style_cell={"textAlign": "center"},
        style_header={"fontWeight": "bold"}
    )

    opts = [{"label": b, "value": b} for b in gl["Brawler"]]
    return opts, None, tabla, opts

@app.callback(
    Output("comp1-dropdown", "options"),
    Output("comp1-dropdown", "value"),
    Input("map-dropdown", "value"),
    Input("main-dropdown", "value"),
    Input("exclude-dropdown", "value")
)
def update_comp1(mapas, main, excluded):
    df = filter_df(get_multi_data(mapas), main, None, None, {}, excluded or [])
    comps = sorted({b for lst in df["team"].dropna() for b in lst if b != main})
    return [{"label": b, "value": b} for b in comps], None

@app.callback(
    Output("comp2-dropdown", "options"),
    Output("comp2-dropdown", "value"),
    Input("map-dropdown", "value"),
    Input("main-dropdown", "value"),
    Input("comp1-dropdown", "value"),
    Input("exclude-dropdown", "value")
)
def update_comp2(mapas, main, c1, excluded):
    df = filter_df(get_multi_data(mapas), main, c1, None, {}, excluded or [])
    comps = sorted({b for lst in df["team"].dropna() for b in lst if b not in (main, c1)})
    return [{"label": b, "value": b} for b in comps], None

@app.callback(
    Output("r1-dropdown", "options"),
    Output("r1-dropdown", "value"),
    Input("map-dropdown", "value"),
    Input("main-dropdown", "value"),
    Input("comp1-dropdown", "value"),
    Input("comp2-dropdown", "value"),
    Input("exclude-dropdown", "value")
)
def update_r1(mapas, main, c1, c2, excluded):
    df = filter_df(get_multi_data(mapas), main, c1, c2, {}, excluded or [])
    rivs = sorted({b for lst in df["opp"].dropna() for b in lst})
    return [{"label": b, "value": b} for b in rivs], None

@app.callback(
    Output("r3-dropdown", "options"),
    Output("r3-dropdown", "value"),
    Input("map-dropdown", "value"),
    Input("main-dropdown", "value"),
    Input("comp1-dropdown", "value"),
    Input("comp2-dropdown", "value"),
    Input("r1-dropdown", "value"),
    Input("r2-dropdown", "value"),
    Input("exclude-dropdown", "value")
)
def update_r3(mapas, main, c1, c2, r1, r2, excluded):
    df = filter_df(get_multi_data(mapas), main, c1, c2,
                   {"r1": r1, "r2": r2}, excluded or [])
    rivs = sorted({b for lst in df["opp"].dropna() for b in lst if b not in (r1, r2)})
    return [{"label": b, "value": b} for b in rivs], None

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
    Input("exclude-dropdown", "value")
)
def update_tables(mapas, main, c1, c2, r1, r2, r3, excluded):
    df = filter_df(get_multi_data(mapas), main, c1, c2,
                   {"r1": r1, "r2": r2, "r3": r3}, excluded or [])
    df = df[df["winner"] != "Empate"]

    if main:
        total = len(df)
        wins = df["win"].sum()
        wr = f"{main}: {wins}/{total} = {wins/total:.1%}" if total else "0%"
    else:
        wr = "Selecciona un brawler principal"

    companions = []
    rivals = []

    if main:
        comps = sorted({b for t in df["team"].dropna() for b in t if b not in (main, c1, c2)})
        for b in comps:
            games = df["team"].apply(lambda t: b in t).sum()
            wins_ = df.apply(lambda r: b in r["team"] and r["win"], axis=1).sum()
            wr_ = round(100 * wins_ / games, 1) if games else 0.0
            companions.append({"brawler": b, "games": int(games), "wins": int(wins_), "wr": wr_})

        rivs = sorted({b for o in df["opp"].dropna() for b in o})
        for b in rivs:
            games = df["opp"].apply(lambda o: b in o).sum()
            wins_vs = df.apply(lambda r: b in r["opp"] and r["win"], axis=1).sum()
            wr_vs = round(100 * wins_vs / games, 1) if games else 0.0
            rivals.append({"brawler": b, "games": int(games), "wins_vs": int(wins_vs), "wr_vs": wr_vs})

    return wr, companions, rivals

@app.callback(
    Output("map-comparison-table", "children"),
    Input("map-dropdown", "value"),
    Input("main-dropdown", "value"),
    Input("comp1-dropdown", "value"),
    Input("comp2-dropdown", "value"),
    Input("r1-dropdown", "value"),
    Input("r2-dropdown", "value"),
    Input("r3-dropdown", "value"),
    Input("exclude-dropdown", "value")
)
def update_map_comparison(mapas, main, c1, c2, r1, r2, r3, excluded):
    if not mapas or len(mapas) < 2 or not main or main.strip() == "":
        return ""

    tabla = []
    for m in mapas:
        try:
            df = filter_df(data[m], main, c1, c2,
                           {"r1": r1, "r2": r2, "r3": r3}, excluded or [])
            df = df[df["winner"] != "Empate"]
            total = len(df)
            wins = df["win"].sum() if "win" in df.columns else 0
            wr = round(100 * wins / total, 1) if total else 0.0

            tabla.append({
                "mapa": m,
                "partidas": total,
                "victorias": int(wins),
                "winrate": wr
            })
        except Exception as e:
            print(f"Error en mapa {m}: {e}")

    df_tabla = pd.DataFrame(tabla).sort_values(["partidas", "winrate"], ascending=[False, False])
    return dash_table.DataTable(
        columns=[
            {"name": "Mapa", "id": "mapa"},
            {"name": "Partidas", "id": "partidas"},
            {"name": "Victorias", "id": "victorias"},
            {"name": "Winrate (%)", "id": "winrate"}
        ],
        data=df_tabla.to_dict("records"),
        page_size=10,
        style_cell={"textAlign": "center"},
        style_header={"fontWeight": "bold"}
    )

# ————————————— Lanzar servidor —————————————
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8080)

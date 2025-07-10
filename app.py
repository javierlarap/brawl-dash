import dash
from dash import dcc, html, Input, Output, dash_table
import pandas as pd

# ————————————— Parámetros y carga de datos —————————————
XLSX_PATH = "scrims_actualizado.xlsx"
xls = pd.ExcelFile(XLSX_PATH)

# Leemos cada hoja, saltando 3 filas de cabecera y tomando 14 columnas
sheets = {
    name: pd.read_excel(XLSX_PATH,
                       sheet_name=name,
                       header=None,
                       skiprows=3,
                       usecols=list(range(14)))
    for name in xls.sheet_names
}

# Para cada hoja construimos un DataFrame estándar con columnas:
# team1 (lista), team2 (lista), winner (Equipo 1/2/Empate)
def make_df(sheet_df):
    records = []
    for _, r in sheet_df.iterrows():
        t1 = list(r.iloc[0:3])
        t2 = list(r.iloc[3:6])
        w = r.iloc[6]
        records.append({"team1": t1, "team2": t2, "winner": w})
    return pd.DataFrame(records)

data = {name: make_df(df) for name, df in sheets.items()}

# Helper: filtrar partidas según main, comps y rivals
def filter_df(df, main, comp1, comp2, rivals):
    d = df.copy()
    # 1) Filtrar por main
    if main:
        mask_main = d.apply(lambda r: main in r["team1"]+r["team2"], axis=1)
        d = d[mask_main]
        # crear columnas team/opp/win
        def split(r):
            if main in r["team1"]:
                return pd.Series({
                    "team": r["team1"],
                    "opp":  r["team2"],
                    "win":  r["winner"] == "Equipo 1"
                })
            else:
                return pd.Series({
                    "team": r["team2"],
                    "opp":  r["team1"],
                    "win":  r["winner"] == "Equipo 2"
                })
        aux = d.apply(split, axis=1)
        d = pd.concat([d, aux], axis=1)
    else:
        # sin main, no hay team/opp
        d["team"] = None
        d["opp"]  = None
        d["win"]  = None

    # 2) Compañeros
    if comp1:
        d = d[d["team"].apply(lambda t: comp1 in t)]
    if comp2:
        d = d[d["team"].apply(lambda t: comp2 in t)]

    # 3) Rivales encadenados
    for r in [rivals.get("r1"), rivals.get("r2"), rivals.get("r3")]:
        if r:
            d = d[d["opp"].apply(lambda o: r in o)]
    return d

# ————————————— Inicializamos la app —————————————
app = dash.Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("Winrate Analyzer por Mapa"),

    # Selección de mapa
    html.Div([
        html.Label("1) Selecciona un mapa"),
        dcc.Dropdown(
            id="map-dropdown",
            options=[{"label": m, "value": m} for m in data],
            value=list(data.keys())[0],
            clearable=False
        )
    ], style={"width": "30%", "display": "inline-block"}),

    html.H2("Winrate global de brawlers en el mapa"),
    html.Div(id="winrate-global"),

    html.Hr(),

    # Filtros encadenados
    html.Div([
        html.Div([
            html.Label("2) Brawler principal"),
            dcc.Dropdown(id="main-dropdown", clearable=True)
        ], style={"width": "30%", "display": "inline-block"}),

        html.Div([
            html.Label("3) Compañero 1"),
            dcc.Dropdown(id="comp1-dropdown", clearable=True)
        ], style={"width": "30%", "display": "inline-block"}),

        html.Div([
            html.Label("4) Compañero 2"),
            dcc.Dropdown(id="comp2-dropdown", clearable=True)
        ], style={"width": "30%", "display": "inline-block"})
    ]),

    html.Div([
        html.Div([
            html.Label("5) Rival 1"),
            dcc.Dropdown(id="r1-dropdown", clearable=True)
        ], style={"width": "30%", "display": "inline-block"}),

        html.Div([
            html.Label("6) Rival 2"),
            dcc.Dropdown(id="r2-dropdown", clearable=True)
        ], style={"width": "30%", "display": "inline-block"}),

        html.Div([
            html.Label("7) Rival 3"),
            dcc.Dropdown(id="r3-dropdown", clearable=True)
        ], style={"width": "30%", "display": "inline-block"})
    ]),

    html.H2("Winrate del brawler principal en el subconjunto"),
    html.Div(id="main-winrate"),

    html.H2("Tabla de Compañeros"),
    dash_table.DataTable(
        id="companions-table",
        columns=[
            {"name": "Compañero",       "id": "brawler"},
            {"name": "Partidas juntos", "id": "games"},
            {"name": "Victorias juntos","id": "wins"},
            {"name": "Winrate (%)",     "id": "wr"}
        ],
        style_cell={"textAlign":"center"},
        style_header={"fontWeight":"bold"},
    ),

    html.H2("Tabla de Rivales"),
    dash_table.DataTable(
        id="rivals-table",
        columns=[
            {"name": "Rival",           "id": "brawler"},
            {"name": "Partidas vs",     "id": "games"},
            {"name": "Victorias de A",  "id": "wins"},
            {"name": "Winrate (%)",     "id": "wr"}
        ],
        style_cell={"textAlign":"center"},
        style_header={"fontWeight":"bold"},
    )
], style={"margin":"20px"})

# ————————————— Callbacks de opciones dinámicas —————————————

# 1) Cuando cambia el mapa, rellenar main-dropdown y winrate-global
@app.callback(
    Output("main-dropdown", "options"),
    Output("main-dropdown", "value"),
    Output("winrate-global", "children"),
    Input("map-dropdown", "value")
)
def update_main_and_global_winrate(mapa):
    df = data[mapa]
    # winrate global
    counts = {}
    for _, r in df.iterrows():
        t1, t2, w = r["team1"], r["team2"], r["winner"]
        for b in t1+t2:
            counts.setdefault(b, {"g":0,"v":0})
            counts[b]["g"] += 1
        if w=="Equipo 1":
            for b in t1: counts[b]["v"]+=1
        elif w=="Equipo 2":
            for b in t2: counts[b]["v"]+=1

    gl = pd.DataFrame([
        {"Brawler": b,
         "Partidas": v["g"],
         "Victorias": v["v"],
         "WR": 0 if v["g"]==0 else v["v"]/v["g"]*100}
        for b,v in counts.items()
    ]).sort_values("Partidas", ascending=False).reset_index(drop=True)

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
    )

    opts = [{"label": b, "value": b} for b in gl["Brawler"].unique()]
    return opts, None, tabla


# 2) Comp1 options: mapa + main
@app.callback(
    Output("comp1-dropdown", "options"),
    Output("comp1-dropdown", "value"),
    Input("map-dropdown", "value"),
    Input("main-dropdown", "value"),
)
def update_comp1_opts(mapa, main):
    df0 = data[mapa]
    df1 = filter_df(df0, main, None, None, {})
    comps = sorted({b for team in df1["team"].dropna() for b in team if b!=main})
    opts = [{"label": b, "value": b} for b in comps]
    return opts, None


# 3) Comp2 options: mapa + main + comp1
@app.callback(
    Output("comp2-dropdown", "options"),
    Output("comp2-dropdown", "value"),
    Input("map-dropdown", "value"),
    Input("main-dropdown", "value"),
    Input("comp1-dropdown", "value"),
)
def update_comp2_opts(mapa, main, c1):
    df2 = filter_df(data[mapa], main, c1, None, {})
    comps = sorted({b for team in df2["team"].dropna() for b in team if b not in (main,c1)})
    opts = [{"label": b, "value": b} for b in comps]
    return opts, None


# 4) R1 options: mapa + main + c1 + c2
@app.callback(
    Output("r1-dropdown", "options"),
    Output("r1-dropdown", "value"),
    Input("map-dropdown", "value"),
    Input("main-dropdown", "value"),
    Input("comp1-dropdown", "value"),
    Input("comp2-dropdown", "value"),
)
def update_r1_opts(mapa, main, c1, c2):
    df3 = filter_df(data[mapa], main, c1, c2, {})
    opps = sorted({b for o in df3["opp"].dropna() for b in o})
    opts = [{"label": b, "value": b} for b in opps]
    return opts, None


# 5) R2 options: mapa + main + c1 + c2 + r1
@app.callback(
    Output("r2-dropdown", "options"),
    Output("r2-dropdown", "value"),
    Input("map-dropdown", "value"),
    Input("main-dropdown", "value"),
    Input("comp1-dropdown", "value"),
    Input("comp2-dropdown", "value"),
    Input("r1-dropdown",    "value"),
)
def update_r2_opts(mapa, main, c1, c2, r1):
    df4 = filter_df(data[mapa], main, c1, c2, {"r1":r1})
    opps = sorted({b for o in df4["opp"].dropna() for b in o if b!=r1})
    opts = [{"label": b, "value": b} for b in opps]
    return opts, None


# 6) R3 options: mapa + main + c1 + c2 + r1 + r2
@app.callback(
    Output("r3-dropdown", "options"),
    Output("r3-dropdown", "value"),
    Input("map-dropdown", "value"),
    Input("main-dropdown", "value"),
    Input("comp1-dropdown", "value"),
    Input("comp2-dropdown", "value"),
    Input("r1-dropdown",    "value"),
    Input("r2-dropdown",    "value"),
)
def update_r3_opts(mapa, main, c1, c2, r1, r2):
    df5 = filter_df(data[mapa], main, c1, c2, {"r1":r1, "r2":r2})
    opps = sorted({b for o in df5["opp"].dropna() for b in o if b not in (r1,r2)})
    opts = [{"label": b, "value": b} for b in opps]
    return opts, None


# ————————————— Callback final: tablas y winrate principal —————————————
@app.callback(
    Output("main-winrate",     "children"),
    Output("companions-table",  "data"),
    Output("rivals-table",      "data"),
    Input("map-dropdown",       "value"),
    Input("main-dropdown",      "value"),
    Input("comp1-dropdown",     "value"),
    Input("comp2-dropdown",     "value"),
    Input("r1-dropdown",        "value"),
    Input("r2-dropdown",        "value"),
    Input("r3-dropdown",        "value"),
)
def update_tables(mapa, main, c1, c2, r1, r2, r3):
    df_sub = filter_df(
        data[mapa], main, c1, c2, {"r1":r1, "r2":r2, "r3":r3}
    )

    # Winrate principal en el subconjunto
    if main:
        total = len(df_sub)
        wins  = df_sub["win"].sum()
        wr    = 0 if total==0 else wins/total*100
        wr_text = f"{main}: {wins}/{total} = {wr:.1f}%"
    else:
        wr_text = "Selecciona un brawler principal"

    # Tabla Compañeros
    comp_data = []
    if main:
        comps = sorted({b for team in df_sub["team"].dropna() for b in team
                        if b not in (main,c1,c2)})
        for b in comps:
            games = df_sub["team"].apply(lambda t: b in t).sum()
            wins_ = df_sub.apply(lambda r: b in r["team"] and r["win"], axis=1).sum()
            comp_data.append({
                "brawler": b, "games": int(games),
                "wins": int(wins_), "wr": round((wins_/games*100) if games else 0,1)
            })

    # Tabla Rivales
    riv_data = []
    if main:
        rivs = sorted({b for o in df_sub["opp"].dropna() for b in o})
        for b in rivs:
            games = df_sub["opp"].apply(lambda o: b in o).sum()
            wins_ = df_sub.apply(lambda r: b in r["opp"] and not r["win"], axis=1).sum()
            riv_data.append({
                "brawler": b, "games": int(games),
                "wins": int(wins_), "wr": round((wins_/games*100) if games else 0,1)
            })

    return wr_text, comp_data, riv_data

# ————————————— Arranque —————————————
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8080)

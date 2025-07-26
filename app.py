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
def filter_df(df, main, comp1, comp2, rivals):
    d = df.copy()
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
        ], style={"display":"inline-block"})
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

def get_multi_data(mapas):
    dfs = [data[m] for m in mapas if m in data]
    return pd.concat(dfs, ignore_index=True)

def filter_df(df, main, comp1, comp2, rivals, excluded=None):
    d = df.copy()

    # Excluir partidas con brawlers seleccionados
    if excluded:
        d = d[~d.apply(lambda r: any(b in (r["team1"] + r["team2"]) for b in excluded), axis=1)]

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
        ], style={"display":"inline-block"})
    ]),

    html.Div([
        html.Label("8) Brawlers a excluir"),
        dcc.Dropdown(id="exclude-dropdown", multi=True, style={"width": "400px"})
    ], style={"marginTop": "20px"}),

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

# ————————————— Callbacks —————————————

@app.callback(
    Output("main-dropdown", "options"),
    Output("main-dropdown", "value"),
    Output("winrate-global", "children"),
    Output("exclude-dropdown", "options"),
    Input("map-dropdown", "value")
)
def update_main_and_global(mapas):
    df = get_multi_data(mapas)
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
    return opts, None, tabla, opts

# ————————————— Lanzar servidor —————————————
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8080)

# app.py

import math
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

def filter_df(df, main, comp1, comp2, rivals):
    d = df.copy()
    if main:
        mask = d.apply(lambda r: main in (r["team1"] + r["team2"]), axis=1)
        d = d[mask]
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

# ————————————— Wilson score —————————————
def score_wilson(wins, games, z=1.96):
    if games == 0:
        return 0
    p = wins / games
    denom = 1 + (z**2)/games
    centre = p + (z**2)/(2*games)
    adj = z * math.sqrt((p*(1-p)/games) + (z**2)/(4*games**2))
    return (centre - adj) / denom

app = dash.Dash(__name__)
server = app.server

# ————————————— Layout —————————————
app.layout = html.Div(style={"margin":"20px"}, children=[

    html.H1("Winrate Analyzer por Mapa"),

    # Selección de mapa
    html.Div([
        html.Label("1) Selecciona un mapa"),
        dcc.Dropdown(
            id="map-dropdown",
            options=[{"label": m, "value": m} for m in data],
            value=list(data.keys())[0],
            clearable=False,
            style={"width":"300px"}
        )
    ]),

    html.H2("Winrate global de brawlers en el mapa"),
    html.Div(id="winrate-global"),
    html.Hr(),

    # Filtros principal y compañeros
    html.Div([
        html.Div([
            html.Label("2) Brawler principal"),
            dcc.Dropdown(id="main-dropdown", clearable=True, style={"width":"250px"})
        ], style={"display":"inline-block","marginRight":"40px"}),

        html.Div([
            html.Label("3) Compañero 1"),
            dcc.Dropdown(id="comp1-dropdown", clearable=True, style={"width":"250px"})
        ], style={"display":"inline-block","marginRight":"40px"}),

        html.Div([
            html.Label("4) Compañero 2"),
            dcc.Dropdown(id="comp2-dropdown", clearable=True, style={"width":"250px"})
        ], style={"display":"inline-block"})
    ]),

    # Filtros rivales
    html.Div(style={"marginTop":"20px"}, children=[
        html.Div([
            html.Label("5) Rival 1"),
            dcc.Dropdown(id="r1-dropdown", clearable=True, style={"width":"250px"})
        ], style={"display":"inline-block","marginRight":"40px"}),
        html.Div([
            html.Label("6) Rival 2"),
            dcc.Dropdown(id="r2-dropdown", clearable=True, style={"width":"250px"})
        ], style={"display":"inline-block","marginRight":"40px"}),
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
            {"name":"Compañero",       "id":"brawler"},
            {"name":"Partidas juntos", "id":"games"},
            {"name":"Victorias juntos","id":"wins"},
            {"name":"Winrate (%)",     "id":"wr"}
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
            {"name":"Rival",        "id":"brawler"},
            {"name":"Partidas vs",  "id":"games"},
            {"name":"Victorias vs", "id":"wins_vs"},
            {"name":"Winrate (%)",  "id":"wr_vs"}
        ],
        style_cell={"textAlign":"center"},
        style_header={"fontWeight":"bold"},
        page_size=10,
        style_data_conditional=[
            {"if":{"column_id":"wr_vs","filter_query":"{wr_vs} < 25"},
             "backgroundColor":"#8B0000","color":"white"},
            {"if":{"column_id":"wr_vs","filter_query":"{wr_vs} >= 25 && {wr_vs} < 45"},
             "backgroundColor":"#FF6347","color":"black"},
            {"if":{"column_id":"wr_vs","filter_query":"{wr_vs} >= 45 && {wr_vs} < 55"},
             "backgroundColor":"#FFFF00","color":"black"},
            {"if":{"column_id":"wr_vs","filter_query":"{wr_vs} >= 55 && {wr_vs} < 70"},
             "backgroundColor":"#90EE90","color":"black"},
            {"if":{"column_id":"wr_vs","filter_query":"{wr_vs} >= 70"},
             "backgroundColor":"#006400","color":"white"},
        ]
    ),

    html.Hr(),

    # ————— Draft Assistant —————
    html.H2("Draft Assistant"),

    html.Div([
        html.Label("A) Orden de picks"),
        dcc.RadioItems(
            id="dl-pick-order",
            options=[
                {"label":"First Pick", "value":"first"},
                {"label":"Last Pick",  "value":"last"}
            ],
            value="first",
            inline=True
        )
    ], style={"marginBottom":"20px"}),

    html.Div([
        html.Div([
            html.Label("Bans Equipo A"),
            dcc.Dropdown(id="dl-ban-a", options=[], multi=True,
                         placeholder="3 bans")
        ], style={"width":"45%","display":"inline-block"}),

        html.Div([
            html.Label("Bans Equipo B"),
            dcc.Dropdown(id="dl-ban-b", options=[], multi=True,
                         placeholder="3 bans")
        ], style={"width":"45%","display":"inline-block","marginLeft":"5%"})
    ], style={"marginBottom":"30px"}),

    html.H3("Sugerencia First Pick"),
    html.Div(id="dl-first-pick-suggestion", style={"marginBottom":"20px"}),

    html.H3("Rival elige First Pick"),
    dcc.Dropdown(id="dl-rival-first-pick", options=[], placeholder="Escoge rival pick"),

    html.H3("Counter-picks recomendados"),
    html.Div(id="dl-counterpick-suggestion")
])

# ————————————— Callbacks dinámicos —————————————

# 1) Mapa → main-options + winrate-global
@app.callback(
    Output("main-dropdown","options"),
    Output("main-dropdown","value"),
    Output("winrate-global","children"),
    Input("map-dropdown","value")
)
def update_main_and_global(mapa):
    df = data[mapa]
    df2 = df[df["winner"]!="Empate"]
    counts = {}
    for _, r in df2.iterrows():
        t1, t2, w = r["team1"], r["team2"], r["winner"]
        for b in t1+t2:
            counts.setdefault(b,{"g":0,"v":0})
            counts[b]["g"]+=1
        if w=="Equipo 1":
            for b in t1: counts[b]["v"]+=1
        elif w=="Equipo 2":
            for b in t2: counts[b]["v"]+=1

    gl = pd.DataFrame([
        {"Brawler":b,"Partidas":v["g"],"Victorias":v["v"],
         "WR":0 if v["g"]==0 else v["v"]/v["g"]*100}
        for b,v in counts.items()
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
    opts = [{"label":b,"value":b} for b in gl["Brawler"]]
    return opts, None, tabla

# 2–6) Encadenar comp1, comp2, r1, r2, r3 (igual que antes)
@app.callback(Output("comp1-dropdown","options"),
              Output("comp1-dropdown","value"),
              Input("map-dropdown","value"),
              Input("main-dropdown","value"))
def update_comp1(mapa, main):
    df1 = filter_df(data[mapa], main, None, None, {})
    comps = sorted({b for lst in df1["team"].dropna() for b in lst if b!=main})
    return [{"label":b,"value":b} for b in comps], None

@app.callback(Output("comp2-dropdown","options"),
              Output("comp2-dropdown","value"),
              Input("map-dropdown","value"),
              Input("main-dropdown","value"),
              Input("comp1-dropdown","value"))
def update_comp2(mapa, main, c1):
    df2 = filter_df(data[mapa], main, c1, None, {})
    comps = sorted({b for lst in df2["team"].dropna() for b in lst if b not in (main,c1)})
    return [{"label":b,"value":b} for b in comps], None

@app.callback(Output("r1-dropdown","options"),
              Output("r1-dropdown","value"),
              Input("map-dropdown","value"),
              Input("main-dropdown","value"),
              Input("comp1-dropdown","value"),
              Input("comp2-dropdown","value"))
def update_r1(mapa, main, c1, c2):
    df3 = filter_df(data[mapa], main, c1, c2, {})
    opps = sorted({b for o in df3["opp"].dropna() for b in o})
    return [{"label":b,"value":b} for b in opps], None

@app.callback(Output("r2-dropdown","options"),
              Output("r2-dropdown","value"),
              Input("map-dropdown","value"),
              Input("main-dropdown","value"),
              Input("comp1-dropdown","value"),
              Input("comp2-dropdown","value"),
              Input("r1-dropdown","value"))
def update_r2(mapa, main, c1, c2, r1):
    df4 = filter_df(data[mapa], main, c1, c2, {"r1":r1})
    opps = sorted({b for o in df4["opp"].dropna() for b in o if b!=r1})
    return [{"label":b,"value":b} for b in opps], None

@app.callback(Output("r3-dropdown","options"),
              Output("r3-dropdown","value"),
              Input("map-dropdown","value"),
              Input("main-dropdown","value"),
              Input("comp1-dropdown","value"),
              Input("comp2-dropdown","value"),
              Input("r1-dropdown","value"),
              Input("r2-dropdown","value"))
def update_r3(mapa, main, c1, c2, r1, r2):
    df5 = filter_df(data[mapa], main, c1, c2, {"r1":r1,"r2":r2})
    opps = sorted({b for o in df5["opp"].dropna() for b in o if b not in (r1,r2)})
    return [{"label":b,"value":b} for b in opps], None

# 7) Tablas principales
@app.callback(
    Output("main-winrate","children"),
    Output("companions-table","data"),
    Output("rivals-table","data"),
    Input("map-dropdown","value"),
    Input("main-dropdown","value"),
    Input("comp1-dropdown","value"),
    Input("comp2-dropdown","value"),
    Input("r1-dropdown","value"),
    Input("r2-dropdown","value"),
    Input("r3-dropdown","value"),
)
def update_tables(mapa, main, c1, c2, r1, r2, r3):
    df_sub = filter_df(data[mapa], main, c1, c2, {"r1":r1,"r2":r2,"r3":r3})
    df_nd = df_sub[df_sub["winner"]!="Empate"]

    if main:
        total = len(df_nd)
        wins  = df_nd["win"].sum()
        wr    = 0 if total==0 else wins/total*100
        wr_text = f"{main}: {wins}/{total} = {wr:.1f}%"
    else:
        wr_text = "Selecciona un brawler principal"

    comp_data = []
    if main:
        comps = sorted({b for t in df_nd["team"].dropna() for b in t if b not in (main,c1,c2)})
        for b in comps:
            g = df_nd["team"].apply(lambda t: b in t).sum()
            v = df_nd.apply(lambda r: b in r["team"] and r["win"], axis=1).sum()
            wr_ = 0 if g==0 else v/g*100
            comp_data.append({"brawler":b,"games":int(g),
                              "wins":int(v),"wr":round(wr_,1)})
        comp_data = sorted(comp_data, key=lambda x:(-x["games"],-x["wr"]))

    riv_data = []
    if main:
        rivs = sorted({b for o in df_nd["opp"].dropna() for b in o})
        for b in rivs:
            g = df_nd["opp"].apply(lambda o: b in o).sum()
            v = df_nd.apply(lambda r: b in r["opp"] and r["win"], axis=1).sum()
            wrv = 0 if g==0 else v/g*100
            riv_data.append({"brawler":b,"games":int(g),
                             "wins_vs":int(v),"wr_vs":round(wrv,1)})
        riv_data = sorted(riv_data, key=lambda x:(-x["games"],-x["wr_vs"]))

    return wr_text, comp_data, riv_data

# ————————————— Draft Assistant Callbacks —————————————

# Inicializar bans y rival-first-pick opciones
@app.callback(
    Output("dl-ban-a","options"),
    Output("dl-ban-b","options"),
    Output("dl-rival-first-pick","options"),
    Input("map-dropdown","value")
)
def init_draft(mapa):
    df = data[mapa]
    df2 = df[df["winner"]!="Empate"]
    counts = {}
    for _, r in df2.iterrows():
        for team, side in (("team1","Equipo 1"),("team2","Equipo 2")):
            for b in r[team]:
                counts.setdefault(b,0)
    opts = [{"label":b,"value":b} for b in sorted(counts)]
    return opts, opts, opts

# Sugerir First Pick usando Wilson
@app.callback(
    Output("dl-first-pick-suggestion","children"),
    Input("map-dropdown","value"),
    Input("dl-ban-a","value"),
    Input("dl-ban-b","value")
)
def suggest_first_pick(mapa, bans_a, bans_b):
    df = data[mapa]
    df2 = df[df["winner"]!="Empate"]
    banned = set(bans_a or []) | set(bans_b or [])
    stats = {}
    for _, r in df2.iterrows():
        for team, side in (("team1","Equipo 1"),("team2","Equipo 2")):
            for b in r[team]:
                if b in banned: continue
                rec = stats.setdefault(b,{"games":0,"wins":0})
                rec["games"] += 1
                if r["winner"]==side:
                    rec["wins"] += 1

    scored = [
        (b, score_wilson(v["wins"], v["games"]), v["games"])
        for b,v in stats.items()
    ]
    top5 = sorted(scored, key=lambda x: x[1], reverse=True)[:5]
    if not top5:
        return "No quedan picks disponibles"
    return html.Ul([
        html.Li(f"{i+1}. {b} → score {sc*100:.1f}% ({g} partidas)")
        for i,(b,sc,g) in enumerate(top5)
    ])

# Sugerir counter-picks tras rival-first-pick
@app.callback(
    Output("dl-counterpick-suggestion","children"),
    Input("map-dropdown","value"),
    Input("dl-ban-a","value"),
    Input("dl-ban-b","value"),
    Input("dl-rival-first-pick","value")
)
def suggest_counters(mapa, bans_a, bans_b, rival_pick):
    if not rival_pick:
        return "Selecciona primero el pick del rival"
    df = data[mapa]
    df2 = df[
        (df["winner"]!="Empate") &
        df.apply(lambda r: rival_pick in (r["team1"]+r["team2"]), axis=1)
    ]
    banned = set(bans_a or []) | set(bans_b or []) | {rival_pick}
    stats = {}
    for _, r in df2.iterrows():
        if rival_pick in r["team1"]:
            opp, win_side = r["team2"], (r["winner"]=="Equipo 2")
        else:
            opp, win_side = r["team1"], (r["winner"]=="Equipo 1")
        for b in opp:
            if b in banned: continue
            rec = stats.setdefault(b,{"games":0,"wins":0})
            rec["games"] += 1
            if win_side:
                rec["wins"] += 1

    scored = [
        (b, score_wilson(v["wins"], v["games"]), v["games"])
        for b,v in stats.items()
    ]
    top5 = sorted(scored, key=lambda x: x[1], reverse=True)[:5]
    if not top5:
        return "No hay counter-picks disponibles"
    return html.Ul([
        html.Li(f"{i+1}. {b} → score {sc*100:.1f}% ({g} partidas)")
        for i,(b,sc,g) in enumerate(top5)
    ])


if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8080)

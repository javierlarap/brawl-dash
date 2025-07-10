# app.py

import math
import dash
from dash import dcc, html, Input, Output, dash_table
import pandas as pd

# ————————————— Parámetros y carga de datos —————————————
XLSX_PATH = "scrims_actualizado.xlsx"
xls = pd.ExcelFile(XLSX_PATH)

# Leemos cada hoja saltando 3 filas y usando las primeras 14 columnas
def make_df(sheet):
    rows = []
    for _, r in sheet.iterrows():
        rows.append({
            "team1": list(r.iloc[0:3]),
            "team2": list(r.iloc[3:6]),
            "winner": r.iloc[6]
        })
    return pd.DataFrame(rows)

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
data = {name: make_df(df) for name, df in sheets.items()}

# Todos los brawlers usados en cualquier scrim (para bans)
ALL_BRAWLERS = sorted({
    b
    for df in data.values()
    for _, r in df.iterrows()
    for b in (r["team1"] + r["team2"])
})

# ————————————— Auxiliares —————————————
def filter_df(df, main, c1, c2, rivals):
    d = df.copy()
    if main:
        mask = d.apply(lambda r: main in (r["team1"] + r["team2"]), axis=1)
        d = d[mask]
        def split(r):
            if main in r["team1"]:
                return pd.Series({"team": r["team1"], "opp": r["team2"], "win": r["winner"]=="Equipo 1"})
            else:
                return pd.Series({"team": r["team2"], "opp": r["team1"], "win": r["winner"]=="Equipo 2"})
        d = pd.concat([d, d.apply(split, axis=1)], axis=1)
    else:
        d["team"], d["opp"], d["win"] = None, None, None

    if c1:
        d = d[d["team"].apply(lambda t: c1 in t)]
    if c2:
        d = d[d["team"].apply(lambda t: c2 in t)]
    for k, v in rivals.items():
        if v:
            d = d[d["opp"].apply(lambda o: v in o)]
    return d

def score_wilson(w, n, z=1.96):
    if n == 0:
        return 0
    p = w/n
    denom = 1 + (z**2)/n
    centre = p + (z**2)/(2*n)
    adj = z * math.sqrt((p*(1-p)/n) + (z**2)/(4*n*n))
    return (centre - adj) / denom

# ————————————— App y Layout —————————————
app = dash.Dash(__name__)
server = app.server

app.layout = html.Div(style={"margin":"20px"}, children=[

    html.H1("Winrate Analyzer por Mapa"),

    # Mapa
    html.Div([
        html.Label("1) Selecciona un mapa"),
        dcc.Dropdown(
            id="map-dropdown",
            options=[{"label":m,"value":m} for m in data],
            value=list(data.keys())[0],
            clearable=False,
            style={"width":"300px"}
        )
    ]),

    # Winrate global
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

    # Winrate subconjunto y tablas
    html.H2("Winrate del brawler principal en el subconjunto"),
    html.Div(id="main-winrate"),

    html.H2("Tabla de Compañeros"),
    dash_table.DataTable(
        id="companions-table", page_size=10,
        columns=[
            {"name":"Compañero","id":"brawler"},
            {"name":"Partidas","id":"games"},
            {"name":"Victorias","id":"wins"},
            {"name":"Winrate (%)","id":"wr"}
        ],
        style_cell={"textAlign":"center"}, style_header={"fontWeight":"bold"},
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
             "backgroundColor":"#006400","color":"white"}
        ]
    ),

    html.H2("Tabla de Rivales"),
    dash_table.DataTable(
        id="rivals-table", page_size=10,
        columns=[
            {"name":"Rival","id":"brawler"},
            {"name":"Partidas vs","id":"games"},
            {"name":"Victorias vs","id":"wins_vs"},
            {"name":"Winrate (%)","id":"wr_vs"}
        ],
        style_cell={"textAlign":"center"}, style_header={"fontWeight":"bold"},
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
             "backgroundColor":"#006400","color":"white"}
        ]
    ),

    html.Hr(),

    # ————— Draft Assistant —————————————
    html.H2("Draft Assistant"),

    # Bans (visuales, no filtran datos de tablas)
    html.Div([
        html.Label("Bans Equipo A"),
        dcc.Dropdown(
            id="ban-a",
            options=[{"label":b,"value":b} for b in ALL_BRAWLERS],
            multi=True, placeholder="3 bans"
        )
    ], style={"width":"45%","display":"inline-block"}),
    html.Div([
        html.Label("Bans Equipo B"),
        dcc.Dropdown(
            id="ban-b",
            options=[{"label":b,"value":b} for b in ALL_BRAWLERS],
            multi=True, placeholder="3 bans"
        )
    ], style={"width":"45%","display":"inline-block","marginLeft":"5%"}),

    # 1) First Pick
    html.H3("1) Sugerencia First Pick"),
    html.Div(id="sug-first", style={"marginBottom":"10px"}),
    html.Label("Elige First Pick"),
    dcc.Dropdown(id="pick-1", options=[], placeholder="First Pick"),

    # 2) Second & Third Picks
    html.H3("2) Sugerencia 2nd & 3rd Picks"),
    html.Div(id="sug-2-3", style={"marginBottom":"10px"}),
    html.Label("Elige 2 & 3 Picks"),
    dcc.Dropdown(id="pick-2-3", multi=True, options=[], placeholder="Second & Third"),

    # 3) Fourth & Fifth Picks
    html.H3("3) Sugerencia 4th & 5th Picks"),
    html.Div(id="sug-4-5", style={"marginBottom":"10px"}),
    html.Label("Elige 4 & 5 Picks"),
    dcc.Dropdown(id="pick-4-5", multi=True, options=[], placeholder="Fourth & Fifth"),

    # 4) Last Pick
    html.H3("4) Sugerencia Last Pick"),
    html.Div(id="sug-last")
])

# ————————————— Callbacks: tablas y filtros —————————————

@app.callback(
    Output("main-dropdown","options"),
    Output("main-dropdown","value"),
    Output("winrate-global","children"),
    Input("map-dropdown","value")
)
def update_global(m):
    df  = data[m]
    df2 = df[df["winner"]!="Empate"]
    cnt = {}
    for _, r in df2.iterrows():
        t1,t2,w = r["team1"], r["team2"], r["winner"]
        for b in t1+t2:
            cnt.setdefault(b,{"g":0,"v":0})["g"] += 1
        if w=="Equipo 1":
            for b in t1: cnt[b]["v"] += 1
        else:
            for b in t2: cnt[b]["v"] += 1

    gl = pd.DataFrame([
        {"Brawler":b, "Partidas":v["g"], "Victorias":v["v"],
         "WR":0 if v["g"]==0 else v["v"]/v["g"]*100}
        for b,v in cnt.items()
    ]).sort_values(["Partidas","WR"], ascending=[False,False]).reset_index(drop=True)

    table = dash_table.DataTable(
        columns=[
            {"name":"Brawler","id":"Brawler"},
            {"name":"Partidas","id":"Partidas"},
            {"name":"Victorias","id":"Victorias"},
            {"name":"Winrate (%)","id":"WR","type":"numeric","format":{"specifier":".1f"}}
        ],
        data=gl.to_dict("records"),
        style_cell={"textAlign":"center"}, style_header={"fontWeight":"bold"},
        page_size=10,
        style_data_conditional=[
            {"if":{"column_id":"WR","filter_query":"{WR}<25"},
             "backgroundColor":"#8B0000","color":"white"},
            {"if":{"column_id":"WR","filter_query":"{WR}>=25 && {WR}<45"},
             "backgroundColor":"#FF6347","color":"black"},
            {"if":{"column_id":"WR","filter_query":"{WR}>=45 && {WR}<55"},
             "backgroundColor":"#FFFF00","color":"black"},
            {"if":{"column_id":"WR","filter_query":"{WR}>=55 && {WR}<70"},
             "backgroundColor":"#90EE90","color":"black"},
            {"if":{"column_id":"WR","filter_query":"{WR}>=70"},
             "backgroundColor":"#006400","color":"white"}
        ]
    )
    opts = [{"label":b,"value":b} for b in gl["Brawler"]]
    return opts, None, table

@app.callback(
    Output("comp1-dropdown","options"), Output("comp1-dropdown","value"),
    Input("map-dropdown","value"), Input("main-dropdown","value")
)
def update_comp1(m, main):
    df1 = filter_df(data[m], main, None, None, {})
    cs  = sorted({b for t in df1["team"].dropna() for b in t if b!=main})
    return [{"label":b,"value":b} for b in cs], None

@app.callback(
    Output("comp2-dropdown","options"), Output("comp2-dropdown","value"),
    Input("map-dropdown","value"), Input("main-dropdown","value"),
    Input("comp1-dropdown","value")
)
def update_comp2(m, main, c1):
    df2 = filter_df(data[m], main, c1, None, {})
    cs  = sorted({b for t in df2["team"].dropna() for b in t if b not in (main,c1)})
    return [{"label":b,"value":b} for b in cs], None

@app.callback(
    Output("r1-dropdown","options"), Output("r1-dropdown","value"),
    Input("map-dropdown","value"), Input("main-dropdown","value"),
    Input("comp1-dropdown","value"), Input("comp2-dropdown","value")
)
def update_r1(m, main, c1, c2):
    df3 = filter_df(data[m], main, c1, c2, {})
    rs  = sorted({b for o in df3["opp"].dropna() for b in o})
    return [{"label":b,"value":b} for b in rs], None

@app.callback(
    Output("r2-dropdown","options"), Output("r2-dropdown","value"),
    Input("map-dropdown","value"), Input("main-dropdown","value"),
    Input("comp1-dropdown","value"), Input("comp2-dropdown","value"),
    Input("r1-dropdown","value")
)
def update_r2(m, main, c1, c2, r1):
    df4 = filter_df(data[m], main, c1, c2, {"r1":r1})
    rs  = sorted({b for o in df4["opp"].dropna() for b in o if b!=r1})
    return [{"label":b,"value":b} for b in rs], None

@app.callback(
    Output("r3-dropdown","options"), Output("r3-dropdown","value"),
    Input("map-dropdown","value"), Input("main-dropdown","value"),
    Input("comp1-dropdown","value"), Input("comp2-dropdown","value"),
    Input("r1-dropdown","value"), Input("r2-dropdown","value")
)
def update_r3(m, main, c1, c2, r1, r2):
    df5 = filter_df(data[m], main, c1, c2, {"r1":r1,"r2":r2})
    rs  = sorted({b for o in df5["opp"].dropna() for b in o if b not in (r1,r2)})
    return [{"label":b,"value":b} for b in rs], None

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
    Input("r3-dropdown","value")
)
def update_tables(m, main, c1, c2, r1, r2, r3):
    df_sub = filter_df(data[m], main, c1, c2, {"r1":r1,"r2":r2,"r3":r3})
    df_nd  = df_sub[df_sub["winner"]!="Empate"]

    if main:
        total = len(df_nd); wins = df_nd["win"].sum()
        wr    = 0 if total==0 else wins/total*100
        mw    = f"{main}: {wins}/{total} = {wr:.1f}%"
    else:
        mw = "Selecciona un brawler principal"

    comp_data, riv_data = [], []
    if main:
        comps = sorted({b for t in df_nd["team"].dropna() for b in t if b not in (main,c1,c2)})
        for b in comps:
            g = df_nd["team"].apply(lambda t: b in t).sum()
            v = df_nd.apply(lambda r: b in r["team"] and r["win"], axis=1).sum()
            comp_data.append({"brawler":b,"games":int(g),"wins":int(v),"wr":round(0 if g==0 else v/g*100,1)})
        comp_data.sort(key=lambda x:(-x["games"],-x["wr"]))

        rivs = sorted({b for o in df_nd["opp"].dropna() for b in o})
        for b in rivs:
            g = df_nd["opp"].apply(lambda o: b in o).sum()
            v = df_nd.apply(lambda r: b in r["opp"] and r["win"], axis=1).sum()
            riv_data.append({"brawler":b,"games":int(g),"wins_vs":int(v),"wr_vs":round(0 if g==0 else v/g*100,1)})
        riv_data.sort(key=lambda x:(-x["games"],-x["wr_vs"]))

    return mw, comp_data, riv_data

# ————————————— Draft Assistant Callbacks —————————————
# Cada callback excluye de df las scrims donde aparezca
# cualquiera de los baneados antes de calcular estadísticas.

@app.callback(
    Output("sug-first","children"),
    Output("pick-1","options"),
    Input("map-dropdown","value"),
    Input("ban-a","value"),
    Input("ban-b","value")
)
def suggest_first(m, ba, bb):
    df = data[m]
    # sin empates
    df2 = df[df["winner"]!="Empate"]
    # quitamos scrims con bans
    banned = set(ba or []) | set(bb or [])
    df2 = df2[~df2.apply(lambda r: any(b in banned for b in r["team1"]+r["team2"]), axis=1)]

    stats = {}
    for _, r in df2.iterrows():
        for team, side in (("team1","Equipo 1"),("team2","Equipo 2")):
            for b in r[team]:
                rec = stats.setdefault(b, {"g":0,"v":0})
                rec["g"] += 1
                if r["winner"]==side:
                    rec["v"] += 1

    scored = [(b, score_wilson(v["v"],v["g"]), v["g"]) for b,v in stats.items()]
    top5   = sorted(scored, key=lambda x:x[1], reverse=True)[:5]
    if not top5:
        return "No quedan picks disponibles", []
    suger = html.Ul([html.Li(f"{i+1}. {b} → {sc*100:.1f}% ({g} partidas)")
                     for i,(b,sc,g) in enumerate(top5)])
    opts  = [{"label":b,"value":b} for b,_,_ in scored]
    return suger, opts

@app.callback(
    Output("sug-2-3","children"),
    Output("pick-2-3","options"),
    Input("map-dropdown","value"),
    Input("ban-a","value"),
    Input("ban-b","value"),
    Input("pick-1","value")
)
def suggest_23(m, ba, bb, p1):
    if not p1:
        return "Elige primero el First Pick", []
    df = data[m]
    df2 = df[df["winner"]!="Empate"]
    banned = set(ba or []) | set(bb or [])
    df2 = df2[~df2.apply(lambda r: any(b in banned for b in r["team1"]+r["team2"]), axis=1)]
    # solo scrims donde jugó p1
    df2 = df2[df2.apply(lambda r: p1 in (r["team1"]+r["team2"]), axis=1)]

    stats = {}
    for _, r in df2.iterrows():
        if p1 in r["team1"]:
            opp, win = r["team2"], (r["winner"]=="Equipo 2")
        else:
            opp, win = r["team1"], (r["winner"]=="Equipo 1")
        for b in opp:
            rec = stats.setdefault(b, {"g":0,"v":0})
            rec["g"] += 1
            if win:
                rec["v"] += 1

    scored = [(b, score_wilson(v["v"],v["g"]), v["g"]) for b,v in stats.items()]
    top5   = sorted(scored, key=lambda x:x[1], reverse=True)[:5]
    if not top5:
        return "No hay sugerencias para 2nd & 3rd", []
    suger = html.Ul([html.Li(f"{i+1}. {b} → {sc*100:.1f}% ({g} partidas)")
                     for i,(b,sc,g) in enumerate(top5)])
    opts  = [{"label":b,"value":b} for b,_,_ in scored]
    return suger, opts

@app.callback(
    Output("sug-4-5","children"),
    Output("pick-4-5","options"),
    Input("map-dropdown","value"),
    Input("ban-a","value"),
    Input("ban-b","value"),
    Input("pick-1","value"),
    Input("pick-2-3","value")
)
def suggest_45(m, ba, bb, p1, p23):
    if not p23 or len(p23)<2:
        return "Elige antes los 2nd & 3rd picks", []
    last = p23[-1]
    df = data[m]
    df2 = df[df["winner"]!="Empate"]
    banned = set(ba or []) | set(bb or [])
    df2 = df2[~df2.apply(lambda r: any(b in banned for b in r["team1"]+r["team2"]), axis=1)]
    df2 = df2[df2.apply(lambda r: last in (r["team1"]+r["team2"]), axis=1)]

    stats = {}
    for _, r in df2.iterrows():
        if last in r["team1"]:
            opp, win = r["team2"], (r["winner"]=="Equipo 2")
        else:
            opp, win = r["team1"], (r["winner"]=="Equipo 1")
        for b in opp:
            rec = stats.setdefault(b, {"g":0,"v":0})
            rec["g"] += 1
            if win:
                rec["v"] += 1

    scored = [(b, score_wilson(v["v"],v["g"]), v["g"]) for b,v in stats.items()]
    top5   = sorted(scored, key=lambda x:x[1], reverse=True)[:5]
    if not top5:
        return "No hay sugerencias para 4th & 5th", []
    suger = html.Ul([html.Li(f"{i+1}. {b} → {sc*100:.1f}% ({g} partidas)")
                     for i,(b,sc,g) in enumerate(top5)])
    opts  = [{"label":b,"value":b} for b,_,_ in scored]
    return suger, opts

@app.callback(
    Output("sug-last","children"),
    Input("map-dropdown","value"),
    Input("ban-a","value"),
    Input("ban-b","value"),
    Input("pick-1","value"),
    Input("pick-2-3","value"),
    Input("pick-4-5","value")
)
def suggest_last(m, ba, bb, p1, p23, p45):
    picks = [p1] + (p23 or []) + (p45 or [])
    if len(picks) < 5:
        return "Completa los 5 picks"
    df = data[m]
    df2 = df[df["winner"]!="Empate"]
    banned = set(ba or []) | set(bb or [])
    df2 = df2[~df2.apply(lambda r: any(b in banned for b in r["team1"]+r["team2"]), axis=1)]
    df2 = df2[~df2.apply(lambda r: any(p in (r["team1"]+r["team2"]) for p in picks), axis=1)]

    stats = {}
    for _, r in df2.iterrows():
        for team, side in (("team1","Equipo 1"),("team2","Equipo 2")):
            for b in r[team]:
                rec = stats.setdefault(b, {"g":0,"v":0})
                rec["g"] += 1
                if r["winner"] == side:
                    rec["v"] += 1

    scored = [(b, score_wilson(v["v"],v["g"]), v["g"]) for b,v in stats.items()]
    top5   = sorted(scored, key=lambda x:x[1], reverse=True)[:5]
    if not top5:
        return "No hay sugerencias para Last Pick"
    return html.Ul([html.Li(f"{i+1}. {b} → {sc*100:.1f}% ({g} partidas)")
                    for i,(b,sc,g) in enumerate(top5)])

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8080)

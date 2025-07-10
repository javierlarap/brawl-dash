# app.py

import math
import dash
from dash import dcc, html, Input, Output, dash_table
import pandas as pd

# ————————————— Parámetros y datos —————————————
XLSX_PATH = "scrims_actualizado.xlsx"
xls = pd.ExcelFile(XLSX_PATH)

# Leer cada hoja
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
    rows = []
    for _, r in sheet_df.iterrows():
        t1, t2, w = list(r.iloc[0:3]), list(r.iloc[3:6]), r.iloc[6]
        rows.append({"team1": t1, "team2": t2, "winner": w})
    return pd.DataFrame(rows)

data = {name: make_df(df) for name, df in sheets.items()}

def filter_df(df, main, comp1, comp2, rivals):
    d = df.copy()
    if main:
        mask = d.apply(lambda r: main in r["team1"]+r["team2"], axis=1)
        d = d[mask]
        def split(r):
            if main in r["team1"]:
                return pd.Series({"team": r["team1"], "opp": r["team2"], "win": r["winner"]=="Equipo 1"})
            else:
                return pd.Series({"team": r["team2"], "opp": r["team1"], "win": r["winner"]=="Equipo 2"})
        aux = d.apply(split, axis=1)
        d = pd.concat([d, aux], axis=1)
    else:
        d["team"], d["opp"], d["win"] = None, None, None

    if comp1:
        d = d[d["team"].apply(lambda t: comp1 in t)]
    if comp2:
        d = d[d["team"].apply(lambda t: comp2 in t)]
    for k in ("r1","r2","r3"):
        v = rivals.get(k)
        if v:
            d = d[d["opp"].apply(lambda o: v in o)]
    return d

def score_wilson(w, n, z=1.96):
    if n == 0: return 0
    p = w/n
    denom = 1 + z*z/n
    cen = p + z*z/(2*n)
    adj = z*math.sqrt((p*(1-p)/n)+(z*z/(4*n*n)))
    return (cen - adj)/denom

app = dash.Dash(__name__)
server = app.server

# ————————————— Layout —————————————
app.layout = html.Div(style={"margin":"20px"}, children=[

    html.H1("Winrate Analyzer por Mapa"),

    # mapa
    html.Div([
        html.Label("1) Selecciona mapa"),
        dcc.Dropdown(
            id="map-dropdown",
            options=[{"label": m, "value": m} for m in data],
            value=list(data.keys())[0],
            clearable=False,
            style={"width":"300px"}
        )
    ]),

    html.H2("Winrate global"),
    html.Div(id="winrate-global"),
    html.Hr(),

    # filtros
    html.Div([
        html.Div([
            html.Label("2) Principal"),
            dcc.Dropdown(id="main-dropdown", clearable=True, style={"width":"200px"})
        ], style={"display":"inline-block","marginRight":"30px"}),
        html.Div([
            html.Label("3) Comp1"),
            dcc.Dropdown(id="comp1-dropdown", clearable=True, style={"width":"200px"})
        ], style={"display":"inline-block","marginRight":"30px"}),
        html.Div([
            html.Label("4) Comp2"),
            dcc.Dropdown(id="comp2-dropdown", clearable=True, style={"width":"200px"})
        ], style={"display":"inline-block"})
    ]),
    html.Div(style={"marginTop":"20px"}, children=[
        html.Div([
            html.Label("5) Rival1"),
            dcc.Dropdown(id="r1-dropdown", clearable=True, style={"width":"200px"})
        ], style={"display":"inline-block","marginRight":"30px"}),
        html.Div([
            html.Label("6) Rival2"),
            dcc.Dropdown(id="r2-dropdown", clearable=True, style={"width":"200px"})
        ], style={"display":"inline-block","marginRight":"30px"}),
        html.Div([
            html.Label("7) Rival3"),
            dcc.Dropdown(id="r3-dropdown", clearable=True, style={"width":"200px"})
        ], style={"display":"inline-block"})
    ]),

    html.H2("Winrate subconjunto"),
    html.Div(id="main-winrate"),

    html.H2("Tabla Compañeros"),
    dash_table.DataTable(
        id="companions-table", page_size=10,
        columns=[
            {"name":"Comp","id":"brawler"},
            {"name":"Games","id":"games"},
            {"name":"Wins","id":"wins"},
            {"name":"WR (%)","id":"wr"}
        ],
        style_cell={"textAlign":"center"},
        style_header={"fontWeight":"bold"},
        style_data_conditional=[
            {"if":{"column_id":"wr","filter_query":"{wr}<25"},
             "backgroundColor":"#8B0000","color":"white"},
            {"if":{"column_id":"wr","filter_query":"{wr}>=25 && {wr}<45"},
             "backgroundColor":"#FF6347"},
            {"if":{"column_id":"wr","filter_query":"{wr}>=45 && {wr}<55"},
             "backgroundColor":"#FFFF00"},
            {"if":{"column_id":"wr","filter_query":"{wr}>=55 && {wr}<70"},
             "backgroundColor":"#90EE90"},
            {"if":{"column_id":"wr","filter_query":"{wr}>=70"},
             "backgroundColor":"#006400","color":"white"},
        ]
    ),

    html.H2("Tabla Rivales"),
    dash_table.DataTable(
        id="rivals-table", page_size=10,
        columns=[
            {"name":"Rival","id":"brawler"},
            {"name":"Games vs","id":"games"},
            {"name":"Wins vs","id":"wins_vs"},
            {"name":"WR (%)","id":"wr_vs"}
        ],
        style_cell={"textAlign":"center"},
        style_header={"fontWeight":"bold"},
        style_data_conditional=[
            {"if":{"column_id":"wr_vs","filter_query":"{wr_vs}<25"},
             "backgroundColor":"#8B0000","color":"white"},
            {"if":{"column_id":"wr_vs","filter_query":"{wr_vs}>=25 && {wr_vs}<45"},
             "backgroundColor":"#FF6347"},
            {"if":{"column_id":"wr_vs","filter_query":"{wr_vs}>=45 && {wr_vs}<55"},
             "backgroundColor":"#FFFF00"},
            {"if":{"column_id":"wr_vs","filter_query":"{wr_vs}>=55 && {wr_vs}<70"},
             "backgroundColor":"#90EE90"},
            {"if":{"column_id":"wr_vs","filter_query":"{wr_vs}>=70"},
             "backgroundColor":"#006400","color":"white"},
        ]
    ),

    html.Hr(),

    # — Draft Assistant —

    html.H2("Draft Assistant"),

    # A) bans
    html.Div([
        html.Label("Bans Equipo A"),
        dcc.Dropdown(id="ban-a", multi=True, placeholder="3 bans"),
    ], style={"width":"40%"}),

    html.Div([
        html.Label("Bans Equipo B"),
        dcc.Dropdown(id="ban-b", multi=True, placeholder="3 bans"),
    ], style={"width":"40%","marginTop":"10px"}),

    html.H3("1) Sugiere First Pick"),
    html.Div(id="sug-first", style={"marginBottom":"10px"}),

    html.Label("Elige First Pick"),
    dcc.Dropdown(id="pick-1", placeholder="First Pick"),

    html.H3("2) Sugiere 2nd & 3rd Picks"),
    html.Div(id="sug-2-3", style={"marginBottom":"10px"}),
    html.Label("Elige 2nd & 3rd Picks"),
    dcc.Dropdown(id="pick-2-3", multi=True, placeholder="Second & Third"),

    html.H3("3) Sugiere 4th & 5th Picks"),
    html.Div(id="sug-4-5", style={"marginBottom":"10px"}),
    html.Label("Elige 4th & 5th Picks"),
    dcc.Dropdown(id="pick-4-5", multi=True, placeholder="Fourth & Fifth"),

    html.H3("4) Sugiere Last Pick"),
    html.Div(id="sug-last")
])

# — Callbacks tablas y globales —

# 1) main & global
@app.callback(
    Output("main-dropdown","options"),
    Output("main-dropdown","value"),
    Output("winrate-global","children"),
    Input("map-dropdown","value")
)
def cb_main(m):
    df = data[m]; df2 = df[df["winner"]!="Empate"]
    cnt = {}
    for _,r in df2.iterrows():
        t1,t2,w = r["team1"],r["team2"],r["winner"]
        for b in t1+t2:
            cnt.setdefault(b,{"g":0,"v":0})["g"]+=1
        if w=="Equipo 1":
            for b in t1: cnt[b]["v"]+=1
        else:
            for b in t2: cnt[b]["v"]+=1
    gl = pd.DataFrame([
        {"Brawler":b,"Games":v["g"],"Wins":v["v"],
         "WR":0 if v["g"]==0 else v["v"]/v["g"]*100}
        for b,v in cnt.items()
    ]).sort_values(["Games","WR"],ascending=[False,False])
    table = dash_table.DataTable(
        columns=[
            {"name":"Brawler","id":"Brawler"},
            {"name":"Games","id":"Games"},
            {"name":"Wins","id":"Wins"},
            {"name":"WR (%)","id":"WR","type":"numeric","format":{"specifier":".1f"}}
        ],
        data=gl.to_dict("records"),
        style_cell={"textAlign":"center"}, style_header={"fontWeight":"bold"},
        page_size=10,
        style_data_conditional=[
            {"if":{"column_id":"WR","filter_query":"{WR}<25"},
             "backgroundColor":"#8B0000","color":"white"},
            {"if":{"column_id":"WR","filter_query":"{WR}>=25 && {WR}<45"},
             "backgroundColor":"#FF6347"},
            {"if":{"column_id":"WR","filter_query":"{WR}>=45 && {WR}<55"},
             "backgroundColor":"#FFFF00"},
            {"if":{"column_id":"WR","filter_query":"{WR}>=55 && {WR}<70"},
             "backgroundColor":"#90EE90"},
            {"if":{"column_id":"WR","filter_query":"{WR}>=70"},
             "backgroundColor":"#006400","color":"white"},
        ]
    )
    opts = [{"label":b,"value":b} for b in gl["Brawler"]]
    return opts, None, table

# 2–6) companions & rivals
@app.callback(
    Output("comp1-dropdown","options"), Output("comp1-dropdown","value"),
    Input("map-dropdown","value"), Input("main-dropdown","value")
)
def cb_c1(m,ma):
    df1=filter_df(data[m],ma,None,None,{})
    cs=sorted({x for t in df1["team"].dropna() for x in t if x!=ma})
    return [{"label":x,"value":x} for x in cs], None

@app.callback(
    Output("comp2-dropdown","options"), Output("comp2-dropdown","value"),
    Input("map-dropdown","value"), Input("main-dropdown","value"),
    Input("comp1-dropdown","value")
)
def cb_c2(m,ma,c1):
    df2=filter_df(data[m],ma,c1,None,{})
    cs=sorted({x for t in df2["team"].dropna() for x in t if x not in (ma,c1)})
    return [{"label":x,"value":x} for x in cs], None

@app.callback(
    Output("r1-dropdown","options"), Output("r1-dropdown","value"),
    Input("map-dropdown","value"), Input("main-dropdown","value"),
    Input("comp1-dropdown","value"), Input("comp2-dropdown","value")
)
def cb_r1(m,ma,c1,c2):
    df3=filter_df(data[m],ma,c1,c2,{})
    rs=sorted({x for o in df3["opp"].dropna() for x in o})
    return [{"label":x,"value":x} for x in rs], None

@app.callback(
    Output("r2-dropdown","options"), Output("r2-dropdown","value"),
    Input("map-dropdown","value"), Input("main-dropdown","value"),
    Input("comp1-dropdown","value"), Input("comp2-dropdown","value"),
    Input("r1-dropdown","value")
)
def cb_r2(m,ma,c1,c2,r1):
    df4=filter_df(data[m],ma,c1,c2,{"r1":r1})
    rs=sorted({x for o in df4["opp"].dropna() for x in o if x!=r1})
    return [{"label":x,"value":x} for x in rs], None

@app.callback(
    Output("r3-dropdown","options"), Output("r3-dropdown","value"),
    Input("map-dropdown","value"), Input("main-dropdown","value"),
    Input("comp1-dropdown","value"), Input("comp2-dropdown","value"),
    Input("r1-dropdown","value"), Input("r2-dropdown","value")
)
def cb_r3(m,ma,c1,c2,r1,r2):
    df5=filter_df(data[m],ma,c1,c2,{"r1":r1,"r2":r2})
    rs=sorted({x for o in df5["opp"].dropna() for x in o if x not in (r1,r2)})
    return [{"label":x,"value":x} for x in rs], None

@app.callback(
    Output("main-winrate","children"),
    Output("companions-table","data"),
    Output("rivals-table","data"),
    Input("map-dropdown","value"), Input("main-dropdown","value"),
    Input("comp1-dropdown","value"), Input("comp2-dropdown","value"),
    Input("r1-dropdown","value"), Input("r2-dropdown","value"),
    Input("r3-dropdown","value")
)
def cb_tables(m,ma,c1,c2,r1,r2,r3):
    df_sub=filter_df(data[m],ma,c1,c2,{"r1":r1,"r2":r2,"r3":r3})
    df_nd=df_sub[df_sub["winner"]!="Empate"]
    if ma:
        t=len(df_nd); w=df_nd["win"].sum()
        wr=0 if t==0 else w/t*100
        mw=f"{ma}: {w}/{t} = {wr:.1f}%"
    else:
        mw="Selecciona principal"
    comp=[]; riv=[]
    if ma:
        comps=sorted({x for t in df_nd["team"].dropna() for x in t if x not in (ma,c1,c2)})
        for b in comps:
            g=df_nd["team"].apply(lambda t: b in t).sum()
            v=df_nd.apply(lambda r: b in r["team"] and r["win"],axis=1).sum()
            comp.append({"brawler":b,"games":int(g),
                         "wins":int(v),"wr":round(0 if g==0 else v/g*100,1)})
        comp.sort(key=lambda x:(-x["games"],-x["wr"]))
        rivs=sorted({x for o in df_nd["opp"].dropna() for x in o})
        for b in rivs:
            g=df_nd["opp"].apply(lambda t: b in t).sum()
            v=df_nd.apply(lambda r: b in r["opp"] and r["win"],axis=1).sum()
            riv.append({"brawler":b,"games":int(g),
                        "wins_vs":int(v),"wr_vs":round(0 if g==0 else v/g*100,1)})
        riv.sort(key=lambda x:(-x["games"],-x["wr_vs"]))
    return mw, comp, riv

# — Callbacks Draft Assistant —

# init bans & picks pool
@app.callback(
    Output("ban-a","options"), Output("ban-b","options"),
    Input("map-dropdown","value")
)
def init_bans(m):
    df=data[m]; df2=df[df["winner"]!="Empate"]
    bs=set()
    for _,r in df2.iterrows():
        bs.update(r["team1"]+r["team2"])
    opts=[{"label":b,"value":b} for b in sorted(bs)]
    return opts, opts

# 1) First pick suggestion
@app.callback(
    Output("sug-first","children"),
    Output("pick-1","options"),
    Input("map-dropdown","value"),
    Input("ban-a","value"), Input("ban-b","value")
)
def cb_first(m,ba,bb):
    df=data[m]; df2=df[df["winner"]!="Empate"]
    banned=set(ba or [])|set(bb or [])
    st={}
    for _,r in df2.iterrows():
        for team,side in (("team1","Equipo 1"),("team2","Equipo 2")):
            for b in r[team]:
                if b in banned: continue
                rec=st.setdefault(b,{"g":0,"v":0})
                rec["g"]+=1
                if r["winner"]==side: rec["v"]+=1
    scored=[(b,score_wilson(v["v"],v["g"]),v["g"]) for b,v in st.items()]
    top=sorted(scored,key=lambda x:x[1],reverse=True)[:5]
    if not top: return "No picks", []
    sug=html.Ul([html.Li(f"{i+1}. {b} → {sc*100:.1f}% ({g} games)")
                 for i,(b,sc,g) in enumerate(top)])
    opts=[{"label":b,"value":b} for b,_,_ in scored]
    return sug, opts

# 2) Suggest 2nd & 3rd
@app.callback(
    Output("sug-2-3","children"),
    Output("pick-2-3","options"),
    Input("map-dropdown","value"),
    Input("ban-a","value"), Input("ban-b","value"),
    Input("pick-1","value")
)
def cb_23(m,ba,bb,p1):
    if not p1: return "Elige primero pick1", []
    df=data[m]; df2=df[(df["winner"]!="Empate")&
                      df.apply(lambda r: p1 in r["team1"]+r["team2"],axis=1)]
    banned=set(ba or [])|set(bb or [])|{p1}
    st={}
    for _,r in df2.iterrows():
        if p1 in r["team1"]:
            opp,win=r["team2"],(r["winner"]=="Equipo 2")
        else:
            opp,win=r["team1"],(r["winner"]=="Equipo 1")
        for b in opp:
            if b in banned: continue
            rec=st.setdefault(b,{"g":0,"v":0})
            rec["g"]+=1
            if win: rec["v"]+=1
    scored=[(b,score_wilson(v["v"],v["g"]),v["g"]) for b,v in st.items()]
    top=sorted(scored,key=lambda x:x[1],reverse=True)[:5]
    if not top: return "No counter", []
    sug=html.Ul([html.Li(f"{i+1}. {b} → {sc*100:.1f}% ({g} games)")
                 for i,(b,sc,g) in enumerate(top)])
    opts=[{"label":b,"value":b} for b,_,_ in scored]
    return sug, opts

# 3) Suggest 4th & 5th
@app.callback(
    Output("sug-4-5","children"),
    Output("pick-4-5","options"),
    Input("map-dropdown","value"),
    Input("ban-a","value"), Input("ban-b","value"),
    Input("pick-1","value"), Input("pick-2-3","value")
)
def cb_45(m,ba,bb,p1,p23):
    if not p23 or len(p23)<2: return "Elige picks 2&3", []
    last = p23[-1]
    df=data[m]; df2=df[(df["winner"]!="Empate")&
                      df.apply(lambda r: last in r["team1"]+r["team2"],axis=1)]
    banned=set(ba or [])|set(bb or [])|{p1}|set(p23)
    st={}
    for _,r in df2.iterrows():
        if last in r["team1"]:
            opp,win=r["team2"],(r["winner"]=="Equipo 2")
        else:
            opp,win=r["team1"],(r["winner"]=="Equipo 1")
        for b in opp:
            if b in banned: continue
            rec=st.setdefault(b,{"g":0,"v":0})
            rec["g"]+=1
            if win: rec["v"]+=1
    scored=[(b,score_wilson(v["v"],v["g"]),v["g"]) for b,v in st.items()]
    top=sorted(scored,key=lambda x:x[1],reverse=True)[:5]
    if not top: return "No picks 4-5", []
    sug=html.Ul([html.Li(f"{i+1}. {b} → {sc*100:.1f}% ({g} games)")
                 for i,(b,sc,g) in enumerate(top)])
    opts=[{"label":b,"value":b} for b,_,_ in scored]
    return sug, opts

# 4) Suggest Last
@app.callback(
    Output("sug-last","children"),
    Input("map-dropdown","value"),
    Input("ban-a","value"), Input("ban-b","value"),
    Input("pick-1","value"), Input("pick-2-3","value"),
    Input("pick-4-5","value")
)
def cb_last(m,ba,bb,p1,p23,p45):
    picks = [p1] + (p23 or []) + (p45 or [])
    if len(picks)<5: return "Completa los 5 picks"
    df=data[m]; df2=df[df["winner"]!="Empate"]
    banned=set(ba or [])|set(bb or [])|set(picks)
    st={}
    for _,r in df2.iterrows():
        for team,side in (("team1","Equipo 1"),("team2","Equipo 2")):
            for b in r[team]:
                if b in banned: continue
                rec=st.setdefault(b,{"g":0,"v":0})
                rec["g"]+=1
                if r["winner"]==side: rec["v"]+=1
    scored=[(b,score_wilson(v["v"],v["g"]),v["g"]) for b,v in st.items()]
    top=sorted(scored,key=lambda x:x[1],reverse=True)[:5]
    if not top: return "No last pick"
    return html.Ul([html.Li(f"{i+1}. {b} → {sc*100:.1f}% ({g} games)")
                    for i,(b,sc,g) in enumerate(top)])

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8080)

import dash
from dash import dcc, html, Input, Output, dash_table
import pandas as pd
from itertools import combinations

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

def ajustar_confianza(winrate, partidas):
    if partidas < 5:
        return winrate * 0.6
    elif partidas < 10:
        return winrate * 0.8
    return winrate

def calcular_peso(combo, partidas, wr_combo, wr_global):
    profundidad = len(combo)
    volumen = min(partidas, 10)
    impacto = abs(wr_combo - wr_global)
    return profundidad * volumen * (1 + impacto / 100)

def wr_ponderado_contextual(brawler, mapas, baneados, df_global):
    df = get_multi_data(mapas)
    if baneados:
        df = df[df.apply(lambda r: all(b not in (r["team1"] + r["team2"]) for b in baneados), axis=1)]

    combos = [()]  # Ya están filtradas las partidas con baneados

    total_peso = 0
    suma = 0
    wr_global = df_global.get(brawler, {}).get("wr", 0)

    for combo in combos:
        df_combo = df
        df_combo = df_combo[df_combo["winner"] != "Empate"]
        games = 0
        wins = 0
        for _, r in df_combo.iterrows():
            if brawler in r["team1"] + r["team2"]:
                games += 1
                if (brawler in r["team1"] and r["winner"] == "Equipo 1") or (brawler in r["team2"] and r["winner"] == "Equipo 2"):
                    wins += 1
        if games == 0:
            continue
        wr = wins / games * 100
        peso = calcular_peso(combo, games, wr, wr_global)
        suma += peso * wr
        total_peso += peso

    if total_peso == 0:
        return wr_global
    return suma / total_peso

app = dash.Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("Sugerencia de Primer Pick"),
    html.Label("Mapas seleccionados"),
    dcc.Dropdown(
        id="map-dropdown",
        options=[{"label": m, "value": m} for m in data],
        value=[list(data.keys())[0]],
        multi=True
    ),
    html.Label("Brawlers excluidos"),
    dcc.Dropdown(id="excluded-dropdown", multi=True),
    html.Label("Brawlers baneados"),
    dcc.Dropdown(id="baneados-dropdown", multi=True),
    html.H2("🧠 Top 5 picks sugeridos"),
    html.Div(id="primer-pick-sugerido", style={"whiteSpace": "pre-line", "fontSize": "18px"})
])

@app.callback(
    Output("excluded-dropdown", "options"),
    Input("map-dropdown", "value")
)
def update_excluded_options(mapas):
    df = get_multi_data(mapas)
    brawlers = sorted({b for _, r in df.iterrows() for b in r["team1"] + r["team2"]})
    return [{"label": b, "value": b} for b in brawlers]

@app.callback(
    Output("primer-pick-sugerido", "children"),
    Input("map-dropdown", "value"),
    Input("excluded-dropdown", "value"),
    Input("baneados-dropdown", "value")
)
def sugerir_primer_pick(mapas, excluidos, baneados):
    df = get_multi_data(mapas)
    df = df[df["winner"] != "Empate"]

    counts = {}
    for _, r in df.iterrows():
        for b in r["team1"] + r["team2"]:
            counts.setdefault(b, {"games": 0, "wins": 0})
            counts[b]["games"] += 1
        if r["winner"] == "Equipo 1":
            for b in r["team1"]:
                counts[b]["wins"] += 1
        elif r["winner"] == "Equipo 2":
            for b in r["team2"]:
                counts[b]["wins"] += 1

    df_global = {
        b: {
            "wr": (v["wins"] / v["games"] * 100) if v["games"] > 0 else 0,
            "games": v["games"]
        }
        for b, v in counts.items()
    }

    disponibles = sorted({
        b for b in counts
        if b not in (baneados or []) + (excluidos or []) and counts[b]["games"] >= 5
    })

    if not disponibles:
        return "⚠️ No hay suficientes datos para sugerir un primer pick."

    scores = []
    for b in disponibles:
        wr_global = ajustar_confianza(df_global[b]["wr"], df_global[b]["games"])
        wr_contextual = wr_ponderado_contextual(b, mapas, baneados or [], df_global)
        score = 0.4 * wr_global + 0.6 * wr_contextual
        scores.append((b, round(score, 1)))

    scores.sort(key=lambda x: x[1], reverse=True)
    top5 = scores[:5]

    texto = ""
    for i, (b, s) in enumerate(top5, 1):
        texto += f"{i}) {b}: {s}%\n"

    return texto

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8080)

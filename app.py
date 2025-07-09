import dash
from dash import dcc, html, Input, Output
import pandas as pd

# Cargar el archivo Excel con todas las hojas (una por mapa)
xlsx_path = "scrims_actualizado.xlsx"
mapas = pd.read_excel(xlsx_path, sheet_name=None)
mapa_names = list(mapas.keys())

# Inicializar la app Dash
app = dash.Dash(__name__)
app.title = "Winrate Analyzer"

# Layout de la app
app.layout = html.Div([
    html.H1("Análisis de Winrates por Mapa"),

    html.Label("Selecciona un mapa:"),
    dcc.Dropdown(id="mapa-dropdown", options=[{"label": m, "value": m} for m in mapa_names], value=mapa_names[0]),

    html.Br(),
    html.Div(id="tabla-winrates")
])

# Callback para mostrar la tabla de winrates
@app.callback(
    Output("tabla-winrates", "children"),
    Input("mapa-dropdown", "value")
)
def mostrar_winrates(mapa):
    df = mapas[mapa]
    win_counts = {}

    for _, row in df.iterrows():
        equipo1 = row.iloc[0:3].tolist()
        equipo2 = row.iloc[3:6].tolist()
        ganador = row["Ganador"]

        for b in equipo1 + equipo2:
            if b not in win_counts:
                win_counts[b] = {"partidas": 0, "victorias": 0}
            win_counts[b]["partidas"] += 1

        if ganador == "Equipo 1":
            for b in equipo1:
                win_counts[b]["victorias"] += 1
        elif ganador == "Equipo 2":
            for b in equipo2:
                win_counts[b]["victorias"] += 1

    resumen = pd.DataFrame([
        {"Brawler": b, "Partidas": v["partidas"], "Victorias": v["victorias"],
         "Winrate (%)": round(100 * v["victorias"] / v["partidas"], 2)}
        for b, v in win_counts.items()
    ]).sort_values(by="Partidas", ascending=False)

    return html.Table([
        html.Thead(html.Tr([html.Th(col) for col in resumen.columns])),
        html.Tbody([
            html.Tr([html.Td(resumen.iloc[i][col]) for col in resumen.columns])
            for i in range(len(resumen))
        ])
    ])

# Necesario para Render
server = app.server

# Ejecutar localmente
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8080)

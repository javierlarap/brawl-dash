import dash
from dash import dcc, html, Input, Output, State, dash_table
import pandas as pd
from itertools import combinations

# ——————————————————————————————
# Parámetros y Umbrales
# ——————————————————————————————
XLSX_PATH                 = "scrims_actualizado.xlsx"
COUNTER_MIN_MATCHES       = 4
COUNTER_MIN_WINRATE       = 0.55
SUPERCOUNTER_MIN_MATCHES  = 6
SUPER_THRESHOLD_HIGH      = 0.75
SUPER_THRESHOLD_LOW       = 0.70
SYNERGY_MIN_MATCHES       = 4
SYNERGY_MIN_WINRATE       = 0.60

ALLOWED_LOSSES_COUNTER = {
    4: 0, 5: 1, 6: 2, 7: 3, 8: 3
}
ALLOWED_LOSSES_SUPER = {
    6: 0, 7: 1, 8: 2, 9: 2
}

# ——————————————————————————————
# 1. Leer Excel y preparar scrims
# ——————————————————————————————
df_raw = pd.read_excel(
    XLSX_PATH,
    header=None,
    skiprows=3,
    usecols=list(range(14)),
    names=[
        'team1_b1','team1_b2','team1_b3',
        'team2_b1','team2_b2','team2_b3',
        'team1_score','team2_score',
        'b1_extra','b2_extra','b3_extra',
        'winner_team','meta_info'
    ]
)

# Generar DataFrame head-to-head
records = []
for _, r in df_raw.iterrows():
    t1 = [r['team1_b1'], r['team1_b2'], r['team1_b3']]
    t2 = [r['team2_b1'], r['team2_b2'], r['team2_b3']]
    win1 = (r['winner_team'] == 'Equipo 1')
    for a in t1:
        for b in t2:
            winner = a if win1 else b
            records.append({'b1': a, 'b2': b, 'winner': winner})
df_h2h = pd.DataFrame(records)

def build_head2head(df):
    h2h = {}
    for (a, b), g in df.groupby(['b1','b2']):
        wins_a = (g['winner'] == a).sum()
        total  = len(g)
        h2h.setdefault(a, {})[b] = {'wins': wins_a, 'total': total}
        h2h.setdefault(b, {})[a] = {'wins': total - wins_a, 'total': total}
    return h2h

h2h = build_head2head(df_h2h)

# Construir conteo de sinergias
def build_synergy(df):
    syn = {}
    for _, r in df.iterrows():
        teams = [
            ([r['team1_b1'],r['team1_b2'],r['team1_b3']], r['winner_team']=="Equipo 1"),
            ([r['team2_b1'],r['team2_b2'],r['team2_b3']], r['winner_team']=="Equipo 2")
        ]
        for team, did_win in teams:
            for x, y in combinations(team, 2):
                src, tgt = sorted([x, y])
                ent = syn.setdefault(src, {}).setdefault(tgt, {'wins':0,'total':0})
                ent['total'] += 1
                if did_win:
                    ent['wins'] += 1
    return syn

syn_counts = build_synergy(df_raw)

# ——————————————————————————————
# 2. Clasificación counters / supercounters / sinergias
# ——————————————————————————————
def is_counter(rec):
    w, t = rec['wins'], rec['total']
    if t < COUNTER_MIN_MATCHES:
        return False
    allowed = ALLOWED_LOSSES_COUNTER.get(t, int((1 - COUNTER_MIN_WINRATE)*t))
    return (t - w) <= allowed and (w/t) >= COUNTER_MIN_WINRATE

def is_supercounter(rec):
    w, t = rec['wins'], rec['total']
    if t < SUPERCOUNTER_MIN_MATCHES:
        return False
    allowed = ALLOWED_LOSSES_SUPER.get(t, int((1 - SUPER_THRESHOLD_LOW)*t))
    threshold = SUPER_THRESHOLD_HIGH if t in ALLOWED_LOSSES_SUPER else SUPER_THRESHOLD_LOW
    return (t - w) <= allowed and (w/t) >= threshold

def is_synergy(rec):
    w, t = rec['wins'], rec['total']
    if t < SYNERGY_MIN_MATCHES:
        return False
    return (w/t) >= SYNERGY_MIN_WINRATE

def classify_maps(h2h, syn_counts):
    counter_map, super_map, syn_map = {}, {}, {}
    # head-to-head → counter / supercounter
    for a, opps in h2h.items():
        for b, rec in opps.items():
            if is_supercounter(rec):
                super_map.setdefault(b, []).append(a)
            elif is_counter(rec):
                counter_map.setdefault(b, []).append(a)
    # sinergias de equipo
    for x, opps in syn_counts.items():
        for y, rec in opps.items():
            if is_synergy(rec):
                syn_map.setdefault(x, []).append(y)
                syn_map.setdefault(y, []).append(x)
    return counter_map, super_map, syn_map

counter_map, super_map, syn_map = classify_maps(h2h, syn_counts)
brawlers = sorted(set(df_h2h['b1']) | set(df_h2h['b2']))

# ——————————————————————————————
# 3. Funciones de puntuación
# ——————————————————————————————
def score_vs_rival(b, rival):
    if rival in super_map.get(b, []):
        return 4 if rival in syn_map.get(b, []) else 3
    if rival in counter_map.get(b, []):
        return 2 if rival in syn_map.get(b, []) else 1
    return 0 if rival in syn_map.get(b, []) else -1

def score_from_rival(b, rival):
    allies = syn_map.get(rival, [])
    src = [rival] + allies
    c = sum(b in counter_map.get(x, []) for x in src)
    s = sum(b in super_map.get(x, []) for x in src)
    if s >= 2 and c >= 0:           return -8
    if s >= 2 and c >= 1:           return -7
    if s >= 1 and c >= 1:           return -6
    if s >= 1 and c == 0:           return -4
    if c >= 2:                      return -4
    if c == 1 and s == 0:           return -2
    return 0

def score_available_counters(b, rival, available):
    c_av = [x for x in available if b in counter_map.get(x, [])]
    s_av = [x for x in available if b in super_map.get(x, [])]
    cnt_c, cnt_s = len(c_av), len(s_av)
    cnt_c_sy = sum(rival in syn_map.get(x, []) for x in c_av)
    cnt_s_sy = sum(rival in syn_map.get(x, []) for x in s_av)

    if cnt_s >= 2 and cnt_s_sy >= 2:   return -8
    if cnt_s >= 2 and cnt_s_sy >= 1:   return -7
    if cnt_s >= 1 and cnt_c >= 1 and cnt_s_sy >= 1 and cnt_c_sy >= 1: return -7
    if cnt_s >= 1 and cnt_c >= 1 and cnt_s_sy >= 1: return -6
    if cnt_s >= 1 and cnt_c >= 1:     return -5
    if cnt_s >= 2:                     return -5
    if cnt_s == 1 and cnt_s_sy == 1:  return -4
    if cnt_s == 1 and cnt_c >= 1:     return -4
    if cnt_c >= 2 and cnt_c_sy >= 2:  return -4
    if cnt_c >= 2 and cnt_c_sy >= 1:  return -3
    if cnt_c >= 2:                     return -2
    if cnt_c == 1 and cnt_c_sy == 1:  return -2
    if cnt_c == 1:                     return -1
    return 0

def synergy_bonus(b1, b2):
    if b2 in super_map.get(b1, []) or b1 in super_map.get(b2, []):
        return 4 if b2 in syn_map.get(b1, []) else 0
    if b2 in counter_map.get(b1, []) or b1 in counter_map.get(b2, []):
        return 3 if b2 in syn_map.get(b1, []) else 0
    return 2 if b2 in syn_map.get(b1, []) else 0

def recommend_brawlers(rival, banned):
    available = [b for b in brawlers if b not in banned and b != rival]
    scores = {}
    for b in available:
        s1 = score_vs_rival(b, rival)
        s2 = score_from_rival(b, rival)
        s3 = score_available_counters(b, rival, available)
        total = s1 + s2 + s3
        if total != 0:
            scores[b] = total

    recs = []
    for b1, b2 in combinations(scores, 2):
        bonus = synergy_bonus(b1, b2)
        recs.append({'Pair': f"{b1} + {b2}",
                     'Score': scores[b1] + scores[b2] + bonus})
    return pd.DataFrame(recs).sort_values('Score', ascending=False).reset_index(drop=True)

# ——————————————————————————————
# 4. Dash App
# ——————————————————————————————
app = dash.Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("Draft Assistant — Winrates Dinámicos"),
    html.Div([
        html.Label("Rival:"), 
        dcc.Dropdown(id='rival', options=[{'label': b,'value': b} for b in brawlers]),
        html.Label("Baneados:"), 
        dcc.Dropdown(id='banned', options=[{'label': b,'value': b} for b in brawlers], multi=True),
        html.Button('Generar', id='go', n_clicks=0, style={'margin':'10px 0'})
    ], style={'width':'30%'}),
    dash_table.DataTable(
        id='table',
        columns=[{"name":"Pair","id":"Pair"},{"name":"Score","id":"Score"}],
        style_table={'overflowX':'auto'}, style_cell={'textAlign':'center'}
    )
])

@app.callback(
    Output('table','data'),
    Input('go','n_clicks'),
    State('rival','value'),
    State('banned','value')
)
def update_table(n, rival, banned):
    if n == 0 or not rival:
        return []
    df = recommend_brawlers(rival, banned or [])
    return df.to_dict('records')

if __name__ == '__main__':
    app.run_server(debug=True)

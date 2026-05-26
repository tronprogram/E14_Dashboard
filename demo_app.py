import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="E14 — CR-ASI-CJL", layout="wide")
st.title("E14 · Cámara de Representantes — Santander")
st.caption("CR-ASI-CJL · Lista 3048 · Fila 101")

@st.cache_data
def load():
    con = sqlite3.connect("output/e14_votes.db")
    df = pd.read_sql("SELECT * FROM votes", con)
    con.close()
    return df

raw = load()

# ── Sidebar: filtros en cascada ───────────────────────────────────────────────
st.sidebar.title("Filtros")

munis  = ["Todos"] + sorted(raw["muni_name"].unique())
sel_muni = st.sidebar.selectbox("Municipio", munis)

df = raw.copy()
if sel_muni != "Todos":
    df = df[df["muni_name"] == sel_muni]

zonas = ["Todas"] + sorted(df["zona"].unique())
sel_zona = st.sidebar.selectbox("Zona", zonas)
if sel_zona != "Todas":
    df = df[df["zona"] == sel_zona]

puestos = ["Todos"] + sorted(df["puesto"].unique())
sel_puesto = st.sidebar.selectbox("Puesto", puestos)
if sel_puesto != "Todos":
    df = df[df["puesto"] == sel_puesto]

# ── KPIs ──────────────────────────────────────────────────────────────────────
total_votos    = int(df["votos"].sum(skipna=True))
total_mesas    = len(df)
tachados       = int(df["tachado"].sum())
mesas_cero     = int((df["votos"] == 0).sum())
promedio       = df["votos"].mean()
mediana        = df["votos"].median()
max_mesa       = df.loc[df["votos"].idxmax()] if df["votos"].notna().any() else None
municipios_n   = df["muni_name"].nunique()
zonas_n        = df["zona"].nunique()
puestos_n      = df["puesto"].nunique()

st.subheader("Resumen general")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Votos totales",       f"{total_votos:,}")
c2.metric("Mesas relevadas",     f"{total_mesas:,}")
c3.metric("Promedio / mesa",     f"{promedio:.1f}")
c4.metric("Mediana / mesa",      f"{mediana:.0f}")
c5.metric("Mesas con 0 votos",   f"{mesas_cero:,}")

c6, c7, c8, c9, c10 = st.columns(5)
c6.metric("Municipios",   f"{municipios_n:,}")
c7.metric("Zonas",        f"{zonas_n:,}")
c8.metric("Puestos",      f"{puestos_n:,}")
c9.metric("Tachados",     f"{tachados:,}")
if max_mesa is not None:
    c10.metric("Máximo en una mesa", f"{int(max_mesa['votos'])} — {max_mesa['muni_name']}")

st.divider()

# ── Gráficos ──────────────────────────────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Votos por municipio")
    by_muni = (
        df.groupby("muni_name")["votos"].sum()
        .reset_index().sort_values("votos", ascending=False)
    )
    fig = px.bar(by_muni, x="muni_name", y="votos",
                 labels={"muni_name": "", "votos": "Votos"},
                 color="votos", color_continuous_scale="Blues")
    fig.update_layout(xaxis_tickangle=-45, coloraxis_showscale=False, height=380)
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("Distribución de votos por mesa (histograma)")
    fig2 = px.histogram(df[df["tachado"] == 0], x="votos", nbins=30,
                        labels={"votos": "Votos", "count": "Mesas"},
                        color_discrete_sequence=["#1f77b4"])
    fig2.update_layout(height=380)
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Participación por municipio")
by_muni_pie = (
    df.groupby("muni_name")["votos"].sum()
    .reset_index().sort_values("votos", ascending=False)
)
total_v = by_muni_pie["votos"].sum()
threshold = st.slider("Agrupar municipios con menos de % del total", 0.5, 5.0, 1.5, 0.5)
mask = (by_muni_pie["votos"] / total_v * 100) >= threshold
big   = by_muni_pie[mask].copy()
small = by_muni_pie[~mask].copy()
if not small.empty:
    otros = pd.DataFrame([{"muni_name": f"Otros ({len(small)})", "votos": small["votos"].sum()}])
    big = pd.concat([big, otros], ignore_index=True)
if threshold <= 0.5:
    import plotly.colors as pc
    palette = pc.qualitative.Plotly + pc.qualitative.D3 + pc.qualitative.G10
    colors  = [palette[i % len(palette)] for i in range(len(big))]
    color_map = dict(zip(big["muni_name"], colors))

    dcol1, dcol2 = st.columns([2, 1])
    with dcol1:
        fig_donut = px.pie(big, names="muni_name", values="votos", hole=0.4,
                           color="muni_name",
                           color_discrete_map=color_map)
        fig_donut.update_traces(textinfo="none",
                                hovertemplate="<b>%{label}</b><br>Votos: %{value}<br>%{percent}")
        fig_donut.update_layout(showlegend=False, height=600,
                                margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_donut, use_container_width=True)
    with dcol2:
        st.markdown("**Municipio · Votos · %**")
        tabla = by_muni_pie.copy()  # todos los municipios, sin agrupar
        tabla["%"] = (tabla["votos"] / total_v * 100).round(2).astype(str) + "%"
        rows_html = ""
        for _, row in tabla.iterrows():
            c = color_map.get(row["muni_name"], "#888")
            rows_html += (
                f'<tr>'
                f'<td><span style="display:inline-block;width:12px;height:12px;'
                f'border-radius:3px;background:{c};margin-right:8px;vertical-align:middle"></span>'
                f'{row["muni_name"]}</td>'
                f'<td style="text-align:right">{int(row["votos"]):,}</td>'
                f'<td style="text-align:right">{row["%"]}</td>'
                f'</tr>'
            )
        st.markdown(
            f'<div style="height:580px;overflow-y:auto">'
            f'<table style="width:100%;border-collapse:collapse;font-size:13px">'
            f'<thead><tr><th style="text-align:left">Municipio</th>'
            f'<th style="text-align:right">Votos</th>'
            f'<th style="text-align:right">%</th></tr></thead>'
            f'<tbody>{rows_html}</tbody></table></div>',
            unsafe_allow_html=True
        )
else:
    fig_donut = px.pie(big, names="muni_name", values="votos", hole=0.4)
    fig_donut.update_traces(textposition="inside", textinfo="percent+label", textfont_size=13)
    fig_donut.update_layout(showlegend=False, height=600,
                            margin=dict(t=40, b=40, l=40, r=40))
    st.plotly_chart(fig_donut, use_container_width=True)

st.divider()

col_c, col_d = st.columns(2)

with col_c:
    st.subheader("Votos por zona")
    by_zona = (
        df.groupby(["muni_name", "zona"])["votos"].sum()
        .reset_index().sort_values("votos", ascending=False)
    )
    by_zona["label"] = by_zona["muni_name"] + " · " + by_zona["zona"]
    fig3 = px.bar(by_zona, x="label", y="votos",
                  labels={"label": "", "votos": "Votos"},
                  color="votos", color_continuous_scale="Teal")
    fig3.update_layout(xaxis_tickangle=-45, coloraxis_showscale=False, height=360)
    st.plotly_chart(fig3, use_container_width=True)

with col_d:
    st.subheader("Top 15 puestos por votos")
    by_puesto = (
        df.groupby(["muni_name", "zona", "puesto"])["votos"].sum()
        .reset_index().sort_values("votos", ascending=False).head(15)
    )
    puesto_clean = by_puesto["puesto"].str.replace(r"Puesto_\d+_", "", regex=True).str.replace("_", " ")
    by_puesto["label"] = by_puesto["muni_name"] + " · " + by_puesto["zona"] + " · " + puesto_clean
    fig4 = px.bar(by_puesto, x="votos", y="label", orientation="h",
                  labels={"votos": "Votos", "label": ""},
                  color="votos", color_continuous_scale="Oranges")
    fig4.update_layout(coloraxis_showscale=False, height=420, yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig4, use_container_width=True)

st.divider()

# ── Mapa de calor ─────────────────────────────────────────────────────────────
st.subheader("Mapa de calor — votos por mesa y puesto")
if sel_muni == "Todos":
    st.info("Seleccioná un municipio en el filtro lateral para ver el mapa de calor.")
else:
    hm_data = df[df["tachado"] == 0].copy()
    hm_data["puesto_short"] = hm_data["puesto"].str.replace(r"Puesto_\d+_", "", regex=True).str.replace("_", " ")
    pivot = hm_data.pivot_table(index="mesa", columns="puesto_short", values="votos", aggfunc="sum")
    fig_hm = px.imshow(
        pivot,
        labels=dict(x="Puesto", y="Mesa", color="Votos"),
        color_continuous_scale="Blues",
        aspect="auto",
        text_auto=True,
    )
    fig_hm.update_traces(textfont_size=11)
    fig_hm.update_layout(
        height=max(300, len(pivot) * 28 + 80),
        xaxis_tickangle=-35,
        coloraxis_showscale=True,
        margin=dict(t=20, b=20, l=60, r=20),
    )
    st.plotly_chart(fig_hm, use_container_width=True)

st.divider()

# ── Mesas outliers ────────────────────────────────────────────────────────────
st.subheader("Mesas destacadas")
col_e, col_f = st.columns(2)

with col_e:
    st.markdown("**Top 10 mesas con más votos**")
    top10 = df.nlargest(10, "votos")[["muni_name","zona","puesto","mesa","votos"]]
    top10["puesto"] = top10["puesto"].str.replace(r"Puesto_\d+_", "", regex=True).str.replace("_", " ")
    st.dataframe(top10, use_container_width=True, hide_index=True)

with col_f:
    st.markdown("**Mesas tachadas**")
    tach_df = df[df["tachado"] == 1][["muni_name","zona","puesto","mesa"]]
    tach_df["puesto"] = tach_df["puesto"].str.replace(r"Puesto_\d+_", "", regex=True).str.replace("_", " ")
    if tach_df.empty:
        st.info("Ninguna en la selección actual.")
    else:
        st.dataframe(tach_df, use_container_width=True, hide_index=True)

# ── Tabla completa ────────────────────────────────────────────────────────────
with st.expander("Ver tabla completa"):
    show = df[["muni_name","zona","puesto","mesa","votos","tachado"]].copy()
    show["puesto"]  = show["puesto"].str.replace(r"Puesto_\d+_", "", regex=True).str.replace("_", " ")
    show["tachado"] = show["tachado"].map({0: "", 1: "✗"})
    st.dataframe(show, use_container_width=True, hide_index=True)

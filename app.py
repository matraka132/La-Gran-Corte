import os
import json
import streamlit as st
from coliseo_core import (
    sanitizar_key,
    obtener_partidos_hoy_hardrock,
    ejecutar_pipeline_coliseo,
    enviar_whatsapp,
    consultar_ia
)

st.set_page_config(page_title="Coliseo de Expertos AI", page_icon="🏛️", layout="centered")

if "input_text" not in st.session_state:
    st.session_state["input_text"] = ""
if "resultados" not in st.session_state:
    if os.path.exists("ultimo_veredicto.json"):
        with open("ultimo_veredicto.json", "r", encoding="utf-8") as f:
            st.session_state["resultados"] = json.load(f)
    else:
        st.session_state["resultados"] = None

def limpiar_datos():
    st.session_state["input_text"] = ""
    st.session_state["resultados"] = None

st.title("🏛️ El Coliseo: Consenso Universal")
st.caption("Auditoría multideporte · Hard Rock Bet · Sin Over/Under")

# Barra lateral con credenciales
with st.sidebar:
    st.header("🔑 Credenciales")
    api_key = sanitizar_key(st.text_input("OpenRouter API Key:", type="password", value=os.getenv("OPENROUTER_API_KEY", "")))
    odds_key = sanitizar_key(st.text_input("The Odds API Key (Hard Rock):", type="password", value=os.getenv("ODDS_API_KEY", "")))

    st.divider()
    st.header("📲 WhatsApp (Opcional)")
    wa_phone = st.text_input("Tu WhatsApp (+1...):", value=os.getenv("WA_PHONE", ""))
    wa_apikey = st.text_input("CallMeBot API Key:", type="password", value=os.getenv("WA_APIKEY", ""))

    if api_key and st.button("🧪 Probar Sonar", use_container_width=True):
        with st.spinner("Probando..."):
            res = consultar_ia("perplexity/sonar", "Responde brevemente: Hola.", api_key)
            if res["status"] == "OK":
                st.success(res["content"])
            else:
                st.error(res["content"])

# Botón para cargar automáticamente partidos de Hard Rock Bet
if st.button("📥 Cargar Cartelera de HOY en Hard Rock Bet (Sin Over/Under)", use_container_width=True):
    if not odds_key:
        st.warning("⚠️ Introduce tu API Key de The Odds API en la barra lateral.")
    else:
        with st.spinner("Descargando partidos y momios de hoy desde Hard Rock Bet..."):
            juegos = obtener_partidos_hoy_hardrock(odds_key)
            if juegos:
                st.session_state["input_text"] = juegos
                st.success("✅ Cartelera cargada (solo Moneyline y Spreads).")
            else:
                st.info("No se encontraron partidos activos hoy en Hard Rock Bet.")

pregunta = st.text_area(
    "✍️ Cartelera del día o consulta manual:",
    key="input_text",
    placeholder="Pulsa el botón superior para cargar los partidos de hoy o pega tus datos aquí...",
    height=170
)

col1, col2 = st.columns([3, 1])
with col1:
    procesar = st.button("🚀 Iniciar Consenso del Coliseo", type="primary", use_container_width=True)
with col2:
    st.button("🔄 Limpiar", on_click=limpiar_datos, use_container_width=True)

if procesar:
    if not api_key or not api_key.startswith("sk-or-"):
        st.error("⚠️ Falta una API Key válida de OpenRouter (`sk-or-...`).")
    elif not pregunta.strip():
        st.warning("⚠️ Escribe una consulta o carga la cartelera primero.")
    else:
        with st.status("🏛️ Auditando eventos en el Coliseo...", expanded=True) as status:
            res = ejecutar_pipeline_coliseo(pregunta, api_key, callback_progreso=st.write)
            st.session_state["resultados"] = res
            status.update(label="✅ Consenso finalizado", state="complete", expanded=False)

        # Enviar automáticamente a WhatsApp si está configurado
        if res["claude"]["status"] == "OK" and wa_phone and wa_apikey:
            ok, msg = enviar_whatsapp(wa_phone, wa_apikey, f"🏛️ *VEREDICTO EL COLISEO*\n\n{res['claude']['content']}")
            if ok:
                st.toast("📲 Veredicto enviado a tu WhatsApp")

# Renderizado persistente de resultados (amigable para móvil)
if st.session_state["resultados"]:
    res = st.session_state["resultados"]
    st.divider()
    st.caption(f"Último análisis: {res.get('fecha', '')}")

    # Tablero compacto responsivo de estado de agentes
    agentes_ui = [
        ("Perplexity", res["perplexity"]),
        ("Cohere (DS)", res["cohere"]),
        ("Llama 3", res["llama"]),
        ("DeepSeek", res["deepseek"]),
        ("Codestral", res["codestral"]),
        ("Grok", res["grok"]),
        ("Gemini", res["gemini"]),
        ("Juez Claude", res["claude"]),
    ]
    st.markdown(" · ".join(f"{'🟢' if r['status'] == 'OK' else '🔴'} **{n}**" for n, r in agentes_ui))

    st.subheader("🏆 Jugadas Seleccionadas (Moneyline / Spread)")
    if res["claude"]["status"] == "OK":
        with st.container(border=True):
            st.markdown(res["claude"]["content"])

        if wa_phone and wa_apikey and st.button("📲 Reenviar este veredicto a mi WhatsApp", use_container_width=True):
            ok, info = enviar_whatsapp(wa_phone, wa_apikey, f"🏛️ *VEREDICTO EL COLISEO*\n\n{res['claude']['content']}")
            if ok:
                st.success("✅ Enviado a WhatsApp.")
            else:
                st.error(f"Error WhatsApp: {info}")
    else:
        st.error(f"⚠️ El Juez Final falló:\n{res['claude']['content']}")

    with st.expander("🔎 Ver respuestas individuales y registro de auditoría"):
        for nombre, resp in agentes_ui[:-1]:
            st.markdown(f"**{nombre} ({resp['status']}):**")
            st.caption(resp["content"])
            st.divider()

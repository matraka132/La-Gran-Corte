import streamlit as st
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="La Gran Corte de Pan con Leche", layout="wide")

st.markdown("""
<style>
    .stApp {
        background-color: #1e130c;
        color: #f5eedb;
        font-family: 'Georgia', serif;
    }
    .court-header {
        text-align: center;
        border-bottom: 2px solid #b8860b;
        padding-bottom: 15px;
        margin-bottom: 20px;
    }
    .court-title {
        font-size: 2.6rem;
        font-weight: bold;
        color: #fdf6e2;
        letter-spacing: 2px;
        text-shadow: 2px 2px 4px #000000;
    }
    .court-subtitle {
        color: #d4af37;
        font-size: 1rem;
        max-width: 850px;
        margin: 0 auto;
    }
    .juror-card {
        background: linear-gradient(145deg, #4a2e18, #2a180b);
        border: 2px solid #b8860b;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
        box-shadow: inset 0 0 10px #000, 2px 2px 5px rgba(0,0,0,0.5);
        margin-bottom: 12px;
    }
    .juror-name {
        color: #ffe082;
        font-weight: bold;
        font-size: 1.1rem;
    }
    .led-active {
        display: inline-block;
        width: 12px;
        height: 12px;
        background-color: #00ff66;
        border-radius: 50%;
        box-shadow: 0 0 8px #00ff66;
        margin-right: 8px;
    }
    .led-waiting {
        display: inline-block;
        width: 12px;
        height: 12px;
        background-color: #555;
        border-radius: 50%;
        margin-right: 8px;
    }
    .verdict-box {
        background-color: #150c07;
        border: 2px solid #d4af37;
        padding: 20px;
        border-radius: 8px;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="court-header">
    <div class="court-title">🏛️ LA GRAN CORTE DE PAN CON LECHE</div>
    <div class="court-subtitle">
        Motor de análisis predictivo y auditoría de datos enfocado en la búsqueda y exposición 
        de posibles vendehumos, charlatanes y esquemas engañosos. Consenso Jurídico-Analítico.
    </div>
</div>
""", unsafe_allow_html=True)

# Manejo robusto de la clave en sesión
default_key = ""
if "OPENROUTER_API_KEY" in st.secrets:
    default_key = str(st.secrets["OPENROUTER_API_KEY"]).strip()
elif os.getenv("OPENROUTER_API_KEY"):
    default_key = str(os.getenv("OPENROUTER_API_KEY")).strip()

with st.sidebar:
    st.markdown("### 🔑 Credenciales OpenRouter")
    api_key_input = st.text_input("Ingresa tu API Key:", value=default_key, type="password")
    
    if st.button("🧪 Probar Conexión con OpenRouter"):
        if not api_key_input.strip():
            st.error("Por favor introduce una clave primero.")
        else:
            try:
                test_client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=api_key_input.strip()
                )
                res = test_client.chat.completions.create(
                    model="meta-llama/llama-3.3-70b-instruct",
                    messages=[{"role": "user", "content": "di ok"}],
                    max_tokens=5
                )
                st.success("✅ ¡Conexión exitosa con OpenRouter! La clave funciona perfectamente.")
            except Exception as e:
                st.error(f"❌ Error al conectar: {e}")

api_key = api_key_input.strip()

# Lista de jurados
JURADOS = [
    {"slot": "Jurado #1", "name": "Perplexity Sonar", "id": "perplexity/sonar"},
    {"slot": "Jurado #2", "name": "Cohere Command R+", "id": "cohere/command-r-plus"},
    {"slot": "Jurado #3", "name": "Llama 3.3 70B", "id": "meta-llama/llama-3.3-70b-instruct"},
    {"slot": "Jurado #4", "name": "Gemini 1.5 Pro", "id": "google/gemini-pro-1.5"},
    {"slot": "Jurado #5", "name": "DeepSeek V3", "id": "deepseek/deepseek-chat"},
    {"slot": "Jurado #6", "name": "Mistral Large", "id": "mistralai/mistral-large"},
    {"slot": "Jurado #7", "name": "Grok 2", "id": "x-ai/grok-2-1212"},
    {"slot": "Jurado #8", "name": "Claude 3.5 Sonnet", "id": "anthropic/claude-3.5-sonnet"}
]

JUEZ_SUPREMO_ID = "anthropic/claude-3.5-sonnet"

def consultar_modelo(client: OpenAI, model_id: str, prompt: str, system_prompt: str) -> str:
    try:
        completion = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error con {model_id}: {str(e)}"

investigado = st.text_area(
    "Introduce tu alegato, o DATOS, o NOMBRE DE INVESTIGADO:",
    placeholder="HOY VAMOS A INVESTIGAR A...",
    height=100
)

col_btn1, col_btn2, _ = st.columns([2, 2, 4])
with col_btn1:
    iniciar = st.button("⚖️ Iniciar Dictamen de la Corte", use_container_width=True)
with col_btn2:
    reiniciar = st.button("🔄 Reiniciar Evidencia", use_container_width=True)

if reiniciar:
    st.rerun()

st.markdown("### 📜 Estado del Escaneo de Agentes:")

cols = st.columns(4)
jurado_placeholders = []
for i, jurado in enumerate(JURADOS):
    with cols[i % 4]:
        ph = st.empty()
        ph.markdown(f"""
        <div class="juror-card">
            <small style="color: #b8860b;">{jurado['slot']}</small><br>
            <span class="led-waiting"></span><span class="juror-name">{jurado['name']}</span>
        </div>
        """, unsafe_allow_html=True)
        jurado_placeholders.append(ph)

if iniciar:
    if not api_key:
        st.error("⚠️ Falta la API Key en la barra lateral.")
    elif not investigado.strip():
        st.warning("⚠️ Debes introducir a quién vamos a investigar.")
    else:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/matraka132/La-Gran-Corte",
                "X-Title": "La Gran Corte de Pan con Leche"
            }
        )

        votos_jurado = []
        system_jurado = (
            "Eres un jurado antifraude implacable. Analiza críticamente al sujeto o empresa mencionada. "
            "Detecta patrones de venta de humo, promesas vacías, academias o cursos cuestionables y estafas. "
            "Entrega: 1) Nivel de riesgo, 2) Razones y datos objetivos detectados."
        )

        progreso = st.progress(0, text="Los jurados están deliberando...")

        for idx, jurado in enumerate(JURADOS):
            progreso.text(f"Consultando a {jurado['name']} ({jurado['slot']})...")
            
            alegato = consultar_modelo(client, jurado["id"], investigado, system_jurado)
            votos_jurado.append({"nombre": jurado["name"], "dictamen": alegato})

            jurado_placeholders[idx].markdown(f"""
            <div class="juror-card" style="border-color: #00ff66;">
                <small style="color: #ffe082;">{jurado['slot']}</small><br>
                <span class="led-active"></span><span class="juror-name">{jurado['name']}</span>
            </div>
            """, unsafe_allow_html=True)

            progreso.progress((idx + 1) / (len(JURADOS) + 1))

        progreso.text("El Juez Supremo está consolidando el veredicto final...")
        
        expediente_completo = f"ACUSADO / HECHOS:\n{investigado}\n\nDELIBERACIONES DEL JURADO:\n"
        for v in votos_jurado:
            expediente_completo += f"\n--- {v['nombre']} ---\n{v['dictamen']}\n"

        system_supremo = (
            "Eres el Juez Supremo de 'La Gran Corte de Pan con Leche'. Evalúa los 8 dictámenes del jurado "
            "y entrega un VEREDICTO FINAL rotundo, detallado y contundente:\n"
            "1. RESUMEN DEL CASO\n"
            "2. PATRONES DETECTADOS Y SEÑALES DE ALERTA\n"
            "3. SENTENCIA (Inocente / Sospechoso / Culpable de Vendehumos)\n"
            "4. RECOMENDACIÓN FINAL AL PÚBLICO."
        )

        veredicto_final = consultar_modelo(client, JUEZ_SUPREMO_ID, expediente_completo, system_supremo)
        progreso.progress(1.0, text="Juicio Concluido.")

        st.markdown('<div class="verdict-box">', unsafe_allow_html=True)
        st.markdown("## ⚖️ VEREDICTO FINAL DE LA CORTE")
        st.markdown(veredicto_final)
        st.markdown('</div>', unsafe_allow_html=True)

        with st.expander("🔍 Ver deliberaciones individuales de los 8 Jurados"):
            for v in votos_jurado:
                st.markdown(f"**{v['nombre']}**")
                st.write(v['dictamen'])
                st.divider()

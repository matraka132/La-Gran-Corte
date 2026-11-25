import os
import json
import urllib.parse
from datetime import datetime, timezone, timedelta
import requests
from concurrent.futures import ThreadPoolExecutor

session = requests.Session()

def sanitizar_key(raw_key):
    if not raw_key:
        return ""
    limpia = "".join(c for c in raw_key if 33 <= ord(c) <= 126).replace('"', '').replace("'", "")
    if limpia.lower().startswith("bearer"):
        limpia = limpia[6:].strip()
    return limpia

# ==========================================================
# 1. DESCARGA AUTOMÁTICA DE HARD ROCK BET (SIN OVER / UNDER)
# ==========================================================
def obtener_partidos_hoy_hardrock(odds_api_key, deportes=None):
    """
    Descarga los juegos de HOY en Hard Rock Bet.
    Solo trae 'h2h' (Moneyline) y 'spreads' (Hándicap). Excluye 'totals' (Over/Under).
    """
    if not odds_api_key:
        return ""

    if deportes is None:
        # Deportes principales activos; puedes agregar o quitar según temporada
        deportes = [
            "basketball_nba",
            "basketball_ncaab",
            "americanfootball_nfl",
            "americanfootball_ncaaf",
            "icehockey_nhl",
            "baseball_mlb",
            "soccer_usa_mls",
            "soccer_epl",
            "soccer_spain_la_liga",
            "soccer_uefa_champs_league"
        ]

    # Ventana de tiempo: juegos que empiezan hoy (hora Este EE.UU. / Florida)
    tz_est = timezone(timedelta(hours=-5))
    ahora_est = datetime.now(tz_est)
    fin_dia_est = ahora_est.replace(hour=23, minute=59, second=59)

    cartelera = []

    for deporte in deportes:
        url = f"https://api.the-odds-api.com/v4/sports/{deporte}/odds/"
        params = {
            "apiKey": odds_api_key,
            "regions": "us",
            "markets": "h2h,spreads",  # <-- EXCLUYE 'totals' (Over/Under)
            "bookmakers": "hardrockbet",
            "oddsFormat": "american"
        }
        try:
            r = session.get(url, params=params, timeout=12)
            if r.status_code != 200:
                continue

            for juego in r.json():
                # Filtrar solo partidos de hoy
                inicio_utc = datetime.fromisoformat(juego["commence_time"].replace("Z", "+00:00"))
                inicio_est = inicio_utc.astimezone(tz_est)
                if not (ahora_est - timedelta(hours=1) <= inicio_est <= fin_dia_est):
                    continue

                lineas_texto = []
                for book in juego.get("bookmakers", []):
                    if book.get("key") != "hardrockbet":
                        continue
                    for market in book.get("markets", []):
                        m_key = market.get("key")
                        # Doble seguro para descartar cualquier total/over/under
                        if m_key not in ("h2h", "spreads"):
                            continue

                        nombre_mercado = "Moneyline" if m_key == "h2h" else "Spread/Hándicap"
                        opciones = []
                        for o in market.get("outcomes", []):
                            punto = f" ({o['point']:+g})" if "point" in o and o["point"] is not None else ""
                            momio = f"{o['price']:+d}" if isinstance(o["price"], int) else str(o["price"])
                            opciones.append(f"{o['name']}{punto}: {momio}")
                        lineas_texto.append(f"{nombre_mercado} -> {', '.join(opciones)}")

                if lineas_texto:
                    hora_str = inicio_est.strftime("%I:%M %p EST")
                    cartelera.append(
                        f"[{juego.get('sport_title', deporte)}] {juego['away_team']} @ {juego['home_team']} ({hora_str})\n"
                        f"   Líneas Hard Rock: {' | '.join(lineas_texto)}"
                    )
        except Exception:
            continue

    return "\n\n".join(cartelera)

# ==========================================================
# 2. CONSULTA A OPENROUTER (TUS MODELOS EXACTOS)
# ==========================================================
def consultar_ia(model_id, prompt, key, system_prompt="Eres un analista experto."):
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://streamlit.app",
        "X-Title": "Coliseo de Expertos AI"
    }
    payload = {
        "model": model_id,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = session.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=(10, 110)
        )
    except requests.RequestException as e:
        return {"status": "ERROR", "content": f"Error de conexión ({model_id}): {e}"}

    detalle = f"Modelo: {model_id}\nHTTP: {response.status_code}\nRespuesta:\n{response.text[:3000]}"

    if response.status_code != 200:
        return {"status": "ERROR", "content": detalle}

    try:
        data = response.json()
    except ValueError:
        return {"status": "ERROR", "content": f"JSON inválido.\n{detalle}"}

    if not isinstance(data, dict) or data.get("error"):
        return {"status": "ERROR", "content": detalle}

    choices = data.get("choices") or []
    if choices:
        texto = (choices[0].get("message") or {}).get("content")
        if isinstance(texto, str) and texto.strip():
            return {"status": "OK", "content": texto.strip()}

    return {"status": "ERROR", "content": f"Sin texto utilizable.\n{detalle}"}

def obtener_contenido_seguro(respuesta):
    return respuesta["content"] if respuesta["status"] == "OK" else "No disponible (Agente fuera de línea)."

# ==========================================================
# 3. PIPELINE DE 3 FASES (TUS IAs Y DIRECCIONES INTACTAS)
# ==========================================================
def ejecutar_pipeline_coliseo(pregunta, api_key, callback_progreso=None):
    regla_no_totals = (
        "REGLA ESTRICTA: Queda TOTALMENTE PROHIBIDO recomendar, analizar o incluir apuestas de "
        "Over/Under (Altas/Bajas o totales de puntos/goles). Enfócate exclusivamente en ganador directo "
        "(Moneyline), Hándicap/Spread o doble oportunidad."
    )

    # FASE 1
    if callback_progreso:
        callback_progreso("📡 Fase 1/3: Buscando datos en vivo y estadísticas...")

    prompt_fact = (
        f"Investiga a fondo y extrae el contexto real actual, bajas, lesiones, estadísticas clave y "
        f"datos de última hora para los siguientes eventos deportivos de hoy:\n{pregunta}\n\n{regla_no_totals}"
    )

    with ThreadPoolExecutor(max_workers=3) as executor:
        f_perp = executor.submit(
            consultar_ia, "perplexity/sonar", prompt_fact, api_key,
            f"Eres el Fact-Checker deportivo universal. Trae datos reales y actualizados de internet para cualquier deporte. {regla_no_totals}"
        )
        f_coh = executor.submit(
            consultar_ia, "deepseek/deepseek-chat-v3.1", f"{pregunta}\n\n{regla_no_totals}", api_key,
            f"Eres el Administrador de Datos. Organiza, procesa y cruza de forma matemática la información estadística entregada, buscando patrones de valor. {regla_no_totals}"
        )
        f_llam = executor.submit(
            consultar_ia, "google/gemini-2.5-pro", f"{pregunta}\n\n{regla_no_totals}", api_key,
            f"Eres el Generalista Deportivo. Ofrece una perspectiva situacional rápida y directa sobre el enfrentamiento o escenario planteado. {regla_no_totals}"
        )

        call_perplexity = f_perp.result()
        call_cohere = f_coh.result()
        call_llama = f_llam.result()

    # FASE 2
    if callback_progreso:
        callback_progreso("⚖️ Fase 2/3: Auditando probabilidades, incongruencias e intangibles...")

    prompt_debate = f"""
    CONSULTA ORIGINAL: {pregunta}

    REPORTE DE CONTEXTO WEB (Perplexity): {obtener_contenido_seguro(call_perplexity)}
    ANÁLISIS ESTADÍSTICO (Administrador): {obtener_contenido_seguro(call_cohere)}
    PERSPECTIVA SITUACIONAL (Llama): {obtener_contenido_seguro(call_llama)}

    Tu tarea: Evalúa críticamente esta información. Analiza las ventajas competitivas reales, tendencias del encuentro y la lógica de las probabilidades para determinar dónde está el verdadero valor del pick, neutralizando sesgos.
    {regla_no_totals}
    """

    with ThreadPoolExecutor(max_workers=4) as executor:
        f_deep = executor.submit(
            consultar_ia, "deepseek/deepseek-v4-pro", prompt_debate, api_key,
            f"Eres DeepSeek R1. Analiza con lógica matemática estricta la probabilidad de éxito de cada escenario basado en los datos recabados. {regla_no_totals}"
        )
        f_code = executor.submit(
            consultar_ia, "mistralai/codestral-2508", prompt_debate, api_key,
            f"Eres el Auditor Eficiente. Identifica incongruencias numéricas, datos cruzados falsos o contradicciones entre los reportes previos. {regla_no_totals}"
        )
        f_grok = executor.submit(
            consultar_ia, "x-ai/grok-4.20", prompt_debate, api_key,
            f"Eres Grok. Evalúa las variables intangibles, el factor de localía, motivación o comportamiento reciente en la disciplina analizada. {regla_no_totals}"
        )
        f_gem = executor.submit(
            consultar_ia, "google/gemini-2.5-pro", prompt_debate, api_key,
            f"Eres Gemini. Procesa todo el volumen masivo de argumentos anteriores para estructurar un panorama contextual completo del evento. {regla_no_totals}"
        )

        call_deepseek = f_deep.result()
        call_codestral = f_code.result()
        call_grok = f_grok.result()
        call_gemini = f_gem.result()

    # FASE 3
    if callback_progreso:
        callback_progreso("👑 Fase 3/3: Emitiendo veredicto final del Juez Supremo...")

    debate_completo = f"""
    CONSULTA DEL EVENTO: {pregunta}

    --- FASE 1: DATOS Y HECHOS ---
    Perplexity: {obtener_contenido_seguro(call_perplexity)}
    Datos/Patrones: {obtener_contenido_seguro(call_cohere)}
    Situacional: {obtener_contenido_seguro(call_llama)}

    --- FASE 2: DEBATE TÉCNICO Y AUDITORÍA ---
    Lógica Matemática (DeepSeek): {obtener_contenido_seguro(call_deepseek)}
    Auditoría de Contradicciones (Codestral): {obtener_contenido_seguro(call_codestral)}
    Variables Intangibles (Grok): {obtener_contenido_seguro(call_grok)}
    Síntesis Contextual (Gemini): {obtener_contenido_seguro(call_gemini)}
    """

    call_claude = consultar_ia(
        "anthropic/claude-sonnet-5.5",
        debate_completo,
        api_key,
        (
            "Eres el Analista Clínico de Anthropic. Actúas como el Juez Supremo del Coliseo. "
            "Filtra de forma definitiva todo el debate de tus compañeros y extrae con precisión matemática "
            "las 2 o 3 mejores opciones/jugadas con mayor factor de ganar en este deporte. "
            "PROHIBIDO incluir apuestas Over/Under o totales de puntos/goles: solo Moneyline o Spread/Hándicap. "
            "Muestra los resultados finales de forma sumamente bonita, limpia y compacta para una pantalla móvil, "
            "empleando viñetas y negritas."
        )
    )

    resultados = {
        "perplexity": call_perplexity,
        "cohere": call_cohere,
        "llama": call_llama,
        "deepseek": call_deepseek,
        "codestral": call_codestral,
        "grok": call_grok,
        "gemini": call_gemini,
        "claude": call_claude,
        "fecha": datetime.now().strftime("%Y-%m-%d %I:%M %p")
    }

    # Guardar respaldo local para que Streamlit pueda leerlo
    with open("ultimo_veredicto.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    return resultados

# ==========================================================
# 4. ENVÍO A WHATSAPP (CallMeBot - Gratis y sin servidor propio)
# ==========================================================
def enviar_whatsapp(telefono, apikey_callmebot, mensaje):
    """
    Envía el veredicto a tu WhatsApp personal usando CallMeBot.
    Formato telefono: +1XXXXXXXXXX (con código de país).
    """
    if not telefono or not apikey_callmebot:
        return False, "Falta teléfono o API Key de CallMeBot."

    # Recortar si excede el límite cómodo de WhatsApp
    texto_limpio = mensaje[:3500]
    texto_codificado = urllib.parse.quote(texto_limpio)
    tel_limpio = telefono.replace(" ", "").replace("-", "")

    url = f"https://api.callmebot.com/whatsapp.php?phone={tel_limpio}&text={texto_codificado}&apikey={apikey_callmebot}"
    try:
        r = session.get(url, timeout=20)
        return (r.status_code == 200), r.text
    except Exception as e:
        return False, str(e)

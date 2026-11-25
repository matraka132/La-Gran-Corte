import os
from coliseo_core import (
    sanitizar_key,
    obtener_partidos_hoy_hardrock,
    ejecutar_pipeline_coliseo,
    enviar_whatsapp
)

OPENROUTER_KEY = sanitizar_key(os.getenv("OPENROUTER_API_KEY", ""))
ODDS_KEY = sanitizar_key(os.getenv("ODDS_API_KEY", ""))
WA_PHONE = os.getenv("WA_PHONE", "")       # Ej: "+13525551234"
WA_APIKEY = os.getenv("WA_APIKEY", "")     # Tu clave gratuita de CallMeBot

def main():
    cartelera = obtener_partidos_hoy_hardrock(ODDS_KEY)
    if not cartelera:
        enviar_whatsapp(WA_PHONE, WA_APIKEY, "🏛️ *El Coliseo (5:00 PM):* Hoy no hay partidos activos con líneas en Hard Rock Bet.")
        return

    resultados = ejecutar_pipeline_coliseo(cartelera, OPENROUTER_KEY)
    veredicto = resultados["claude"]

    if veredicto["status"] == "OK":
        mensaje = f"🏛️ *EL COLISEO - PICKS DEL DÍA (5:00 PM)*\n_(Solo Moneyline y Spread)_\n\n{veredicto['content']}"
    else:
        mensaje = f"⚠️ *El Coliseo:* Hubo un error con el Juez Supremo hoy.\n{veredicto['content'][:500]}"

    enviar_whatsapp(WA_PHONE, WA_APIKEY, mensaje)

if __name__ == "__main__":
    main()

import os
import time
import logging
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, ConversationHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

time.sleep(3)

TOKEN = os.environ.get("TOKEN")
ORS_KEY = os.environ.get("ORS_KEY")
KM_POR_GALON = 50
PRECIO_GALON = 15500
COMISION_UBER = 0.25
GANANCIA_MINIMA_KM = 500

ESPERANDO_ORIGEN, ESPERANDO_DESTINO, ESPERANDO_TARIFA = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Bienvenido a tu calculadora Uber*\n\n"
        "📍 ¿Cuál es el *origen* del viaje?\n"
        "_Ejemplo: Carrera 7 con calle 32, Bogotá_",
        parse_mode="Markdown"
    )
    return ESPERANDO_ORIGEN

async def recibir_origen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["origen"] = update.message.text
    await update.message.reply_text(
        "✅ Origen guardado.\n\n"
        "🏁 ¿Cuál es el *destino* del viaje?\n"
        "_Ejemplo: Aeropuerto El Dorado, Bogotá_",
        parse_mode="Markdown"
    )
    return ESPERANDO_DESTINO

async def recibir_destino(update: Update, context: ContextTypes.DEFAULT_TYPE):
    destino = update.message.text
    origen = context.user_data["origen"]

    await update.message.reply_text("🔍 Calculando ruta, espera un momento...")

    try:
        async with httpx.AsyncClient() as client:
            def geocode(lugar):
                url = "https://api.openrouteservice.org/geocode/search"
                r = client.get(url, params={"api_key": ORS_KEY, "text": lugar, "size": 1})
                return r

            r_origen = await client.get(
                "https://api.openrouteservice.org/geocode/search",
                params={"api_key": ORS_KEY, "text": origen, "size": 1}
            )
            r_destino = await client.get(
                "https://api.openrouteservice.org/geocode/search",
                params={"api_key": ORS_KEY, "text": destino, "size": 1}
            )

            coords_origen = r_origen.json()["features"][0]["geometry"]["coordinates"]
            coords_destino = r_destino.json()["features"][0]["geometry"]["coordinates"]

            r_ruta = await client.post(
                "https://api.openrouteservice.org/v2/directions/driving-car/json",
                headers={"Authorization": ORS_KEY},
                json={"coordinates": [coords_origen, coords_destino]}
            )

            ruta = r_ruta.json()["routes"][0]["summary"]
            km = round(ruta["distance"] / 1000, 1)
            minutos = round(ruta["duration"] / 60)

            context.user_data["km"] = km
            context.user_data["minutos"] = minutos

            await update.message.reply_text(
                f"🗺 *Ruta encontrada*\n\n"
                f"📍 Distancia: *{km} km*\n"
                f"⏱ Tiempo estimado: *{minutos} minutos*\n\n"
                f"💰 ¿Cuánto vale el viaje en pesos?",
                parse_mode="Markdown"
            )
            return ESPERANDO_TARIFA

    except Exception as e:
        logger.error(f"Error calculando ruta: {e}")
        await update.message.reply_text(
            "⚠️ No pude encontrar la ruta. Intenta con una dirección más específica.\n\n"
            "Escribe /start para intentar de nuevo."
        )
        return ConversationHandler.END

async def recibir_tarifa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tarifa = float(update.message.text.replace(".", "").replace(",", ""))
        km = context.user_data["km"]
        minutos = context.user_data["minutos"]

        costo_gasolina = (PRECIO_GALON / 3.785) / KM_POR_GALON * km
        valor_neto = tarifa * (1 - COMISION_UBER)
        ganancia = valor_neto - costo_gasolina
        ganancia_por_km = ganancia / km if km > 0 else 0

        if ganancia_por_km >= 800:
            alerta = "🟢 *Buen viaje* — vale la pena"
        elif ganancia_por_km >= 500:
            alerta = "🟡 *Viaje regular* — aceptable"
        else:
            alerta = "🔴 *No vale la pena* — muy poco por km"

        await update.message.reply_text(
            f"{'✅' if ganancia > 0 else '❌'} *Resumen del viaje*\n\n"
            f"📍 Distancia: {km} km\n"
            f"⏱ Tiempo: {minutos} min\n"
            f"💰 Tarifa: ${tarifa:,.0f}\n"
            f"🚗 Uber se lleva: ${tarifa * COMISION_UBER:,.0f}\n"
            f"⛽ Gasolina: ${costo_gasolina:,.0f}\n"
            f"─────────────────\n"
            f"💵 *Ganancia neta: ${ganancia:,.0f}*\n"
            f"📊 Por km: ${ganancia_por_km:,.0f}/km\n\n"
            f"{alerta}\n\n"
            f"_Escribe /start para calcular otro viaje_",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    except Exception:
        await update.message.reply_text("⚠️ Ingresa solo el valor. Ejemplo: *18000*", parse_mode="Markdown")
        return ESPERANDO_TARIFA

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelado. Escribe /start para empezar.")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ESPERANDO_ORIGEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_origen)],
            ESPERANDO_DESTINO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_destino)],
            ESPERANDO_TARIFA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_tarifa)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    app.add_handler(conv)
    app.run_polling()

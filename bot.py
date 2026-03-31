import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("TOKEN")
KM_POR_GALON = 50
PRECIO_GALON = 15500
COMISION_UBER = 0.25

async def calcular(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        partes = update.message.text.strip().split()
        km = float(partes[0])
        tarifa = float(partes[1])

        costo_gasolina = (PRECIO_GALON / 3.785) / KM_POR_GALON * km
        valor_neto = tarifa * (1 - COMISION_UBER)
        ganancia = valor_neto - costo_gasolina

        emoji = "✅" if ganancia > 0 else "❌"

        respuesta = (
            f"{emoji} *Resumen del viaje*\n\n"
            f"📍 Distancia: {km} km\n"
            f"💰 Tarifa: ${tarifa:,.0f}\n"
            f"🚗 Uber se lleva: ${tarifa * COMISION_UBER:,.0f}\n"
            f"⛽ Gasolina: ${costo_gasolina:,.0f}\n"
            f"─────────────────\n"
            f"💵 *Ganancia neta: ${ganancia:,.0f}*\n"
            f"📊 Rentabilidad: {(ganancia/tarifa*100):.1f}%"
        )
        await update.message.reply_text(respuesta, parse_mode="Markdown")

    except:
        await update.message.reply_text(
            "Envíame: *distancia valor*\nEjemplo: `15 18000`",
            parse_mode="Markdown"
        )

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT, calcular))
app.run_polling()

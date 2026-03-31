import os
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, ConversationHandler

time.sleep(3)

TOKEN = os.environ.get("TOKEN")
KM_POR_GALON = 50
PRECIO_GALON = 15500
COMISION_UBER = 0.25

ESPERANDO_KM, ESPERANDO_TARIFA = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Bienvenido a tu calculadora Uber*\n\n"
        "Vamos a calcular tu ganancia.\n\n"
        "📍 ¿Cuántos kilómetros tiene el viaje?",
        parse_mode="Markdown"
    )
    return ESPERANDO_KM

async def recibir_km(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        km = float(update.message.text.replace(",", "."))
        context.user_data["km"] = km
        await update.message.reply_text(
            f"✅ *{km} km* registrados.\n\n"
            "💰 ¿Cuánto vale el viaje en pesos?",
            parse_mode="Markdown"
        )
        return ESPERANDO_TARIFA
    except:
        await update.message.reply_text("⚠️ Ingresa solo el número. Ejemplo: *12* o *7.5*", parse_mode="Markdown")
        return ESPERANDO_KM

async def recibir_tarifa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tarifa = float(update.message.text.replace(",", "").replace(".", ""))
        km = context.user_data["km"]

        costo_gasolina = (PRECIO_GALON / 3.785) / KM_POR_GALON * km
        valor_neto = tarifa * (1 - COMISION_UBER)
        ganancia = valor_neto - costo_gasolina
        emoji = "✅" if ganancia > 0 else "❌"

        await update.message.reply_text(
            f"{emoji} *Resumen del viaje*\n\n"
            f"📍 Distancia: {km} km\n"
            f"💰 Tarifa: ${tarifa:,.0f}\n"
            f"🚗 Uber se lleva: ${tarifa * COMISION_UBER:,.0f}\n"
            f"⛽ Gasolina: ${costo_gasolina:,.0f}\n"
            f"─────────────────\n"
            f"💵 *Ganancia neta: ${ganancia:,.0f}*\n"
            f"📊 Rentabilidad: {(ganancia/tarifa*100):.1f}%\n\n"
            f"_Escribe /start para calcular otro viaje_",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    except:
        await update.message.reply_text("⚠️ Ingresa solo el valor. Ejemplo: *18000*", parse_mode="Markdown")
        return ESPERANDO_TARIFA

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cálculo cancelado. Escribe /start para empezar de nuevo.")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ESPERANDO_KM: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_km)],
            ESPERANDO_TARIFA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_tarifa)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(conv)
    app.run_polling()

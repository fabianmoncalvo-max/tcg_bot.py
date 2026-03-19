"""
TCG BOT - VERSION CON DIAGNOSTICO
"""

import logging
import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# Configuracion de logging DETALLADO
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

TOKEN = "8604982984:AAGztYBQfjcUT0GnFQlgogamubCjNoPtZ7c"
GOOGLE_URL = "https://script.google.com/macros/s/AKfycbwaY1MURBCqgReCYJK7IvNPimWxSRw7tC3gkVGiP-ljxZosa8-PiULLwcGmsXAA3TH0/exec"

def api_call(action, data=None):
    """Llamada a Google Sheets con LOGS"""
    try:
        payload = {"action": action}
        if data:
            payload.update(data)
        
        logger.info("ENVIANDO a %s", GOOGLE_URL)
        logger.info("Payload: %s", json.dumps(payload))
        
        response = requests.post(
            GOOGLE_URL, 
            json=payload, 
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        
        logger.info("Status Code: %s", response.status_code)
        logger.info("Respuesta: %s", response.text[:500])
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            logger.error("Error HTTP: %s", response.status_code)
            return {"success": False, "error": "HTTP " + str(response.status_code), "productos": []}
            
    except Exception as e:
        logger.error("EXCEPCION: %s", str(e))
        return {"success": False, "error": str(e), "productos": []}

async def start(update: Update, context):
    """Inicio"""
    user = update.effective_user
    
    # TEST: Llamar a API inmediatamente
    logger.info("=" * 50)
    logger.info("TEST DE CONEXION AL INICIAR")
    test_result = api_call("get_productos")
    logger.info("Test result: %s", test_result)
    logger.info("=" * 50)
    
    productos_count = len(test_result.get('productos', []))
    
    mensaje = (
        "🐕‍🦺 *TCG Pet Store* 🐈\n\n"
        f"Hola {user.first_name}!\n\n"
        f"📊 *Diagnostico:*\n"
        f"Productos en Google Sheets: `{productos_count}`\n"
        f"Conexion API: {'✅ OK' if test_result.get('success') else '❌ ERROR'}\n\n"
        f"{'✅ Sistema funcionando correctamente' if productos_count > 0 else '⚠️ No se encontraron productos. Verifica Google Sheets.'}\n\n"
        "¿Que deseas hacer?"
    )
    
    await update.message.reply_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Ver Productos", callback_data='prod')],
            [InlineKeyboardButton("🔄 Test Conexion", callback_data='test')],
            [InlineKeyboardButton("📊 Ver Stock", callback_data='stock')]
        ])
    )

async def button_handler(update: Update, context):
    """Maneja botones"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'prod':
        result = api_call("get_productos")
        productos = result.get('productos', [])
        
        logger.info("Productos obtenidos: %s", len(productos))
        
        if not productos:
            error_msg = result.get('error', 'Sin error especifico')
            mensaje_error = (
                "❌ *No hay productos*\n\n"
                f"Error: `{error_msg}`\n"
                f"Success: `{result.get('success')}`\n\n"
                "*Verifica:*\n"
                "1. ¿La hoja 'productos' tiene datos?\n"
                "2. ¿La Web App esta publicada como 'Cualquiera'?\n"
                "3. ¿Las columnas tienen los nombres correctos?\n\n"
                "ID Hoja: `1ddtqz7_pozoY4hFXmTFhLv81m5ZNtH0lOoC6SkDNNJk`"
            )
            await query.edit_message_text(
                mensaje_error,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Reintentar", callback_data='prod')],
                    [InlineKeyboardButton("« Volver", callback_data='back')]
                ])
            )
            return
        
        text = "*🛒 Productos disponibles:*\n\n"
        for p in productos[:10]:
            if p.get('stock', 0) > 0:
                precio = f"${p['precio']:,}".replace(',', '.')
                text += f"✅ *{p['nombre']}*\n💰 {precio} | 📦 {p['stock']} u.\n\n"
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Actualizar", callback_data='prod')],
                [InlineKeyboardButton("« Volver", callback_data='back')]
            ])
        )
    
    elif data == 'test':
        result = api_call("get_productos")
        mensaje_test = (
            "*🧪 TEST DE CONEXION*\n\n"
            f"Success: `{result.get('success')}`\n"
            f"Productos: `{len(result.get('productos', []))}`\n"
            f"Error: `{result.get('error', 'Ninguno')}`\n\n"
            "Respuesta completa:\n"
            "```\n"
            f"{json.dumps(result, indent=2)[:800]}\n"
            "```"
        )
        await query.edit_message_text(
            mensaje_test,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Volver", callback_data='back')]
            ])
        )
    
    elif data == 'stock':
        result = api_call("get_stats")
        stats = result.get('estadisticas', {})
        prod = stats.get('productos', {})
        
        mensaje_stock = (
            "*📊 Stock*\n\n"
            f"Total: `{prod.get('total', 0)}`\n"
            f"Disponibles: `{prod.get('disponibles', 0)}`\n"
            f"Agotados: `{prod.get('agotados', 0)}`"
        )
        await query.edit_message_text(
            mensaje_stock,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Volver", callback_data='back')]
            ])
        )
    
    elif data == 'back':
        await start(update, context)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("=" * 50)
    logger.info("BOT INICIADO - VERSION CON DIAGNOSTICO")
    logger.info("=" * 50)
    
    print("🚀 Bot iniciado con diagnostico!")
    app.run_polling()

if __name__ == '__main__':
    main()

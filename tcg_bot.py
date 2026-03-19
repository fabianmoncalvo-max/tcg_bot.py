"""
TCG BOT - VERSION PARA PYTHON 3.14
"""

import logging
import requests
import json
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# Configuracion de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8604982984:AAGztYBQfjcUT0GnFQlgogamubCjNoPtZ7c"
GOOGLE_URL = "https://script.google.com/macros/s/AKfycbwaY1MURBCqgReCYJK7IvNPimWxSRw7tC3gkVGiP-ljxZosa8-PiULLwcGmsXAA3TH0/exec"

def api_call(action, data=None):
    """Llamada a Google Sheets"""
    try:
        payload = {"action": action}
        if data:
            payload.update(data)
        
        logger.info("ENVIANDO a %s", GOOGLE_URL)
        response = requests.post(
            GOOGLE_URL, 
            json=payload, 
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        
        logger.info("Status: %s", response.status_code)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"success": False, "error": "HTTP " + str(response.status_code), "productos": []}
            
    except Exception as e:
        logger.error("Error: %s", str(e))
        return {"success": False, "error": str(e), "productos": []}

async def start(update: Update, context):
    """Inicio"""
    user = update.effective_user
    
    # TEST de conexion
    test_result = api_call("get_productos")
    productos_count = len(test_result.get('productos', []))
    
    mensaje = (
        "🐕‍🦺 *TCG Pet Store* 🐈\n\n"
        f"Hola {user.first_name}!\n\n"
        f"📊 *Diagnostico:*\n"
        f"Productos: `{productos_count}`\n"
        f"Conexion: {'✅ OK' if test_result.get('success') else '❌ ERROR'}\n\n"
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
        
        if not productos:
            await query.edit_message_text(
                "❌ *No hay productos*\n\nVerifica Google Sheets.",
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
            f"Error: `{result.get('error', 'Ninguno')}`"
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

async def main_async():
    """Funcion principal async"""
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("BOT INICIADO")
    print("🚀 Bot iniciado!")
    
    # Iniciar polling
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Mantener corriendo
    while True:
        await asyncio.sleep(3600)  # Dormir 1 hora

if __name__ == '__main__':
    asyncio.run(main_async())

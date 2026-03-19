"""
TCG BOT - VERSIÓN CON DIAGNÓSTICO
"""

import logging
import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# Configuración de logging DETALLADO
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # CAMBIADO A DEBUG para ver todo
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
        
        logger.info(f"🔍 ENVIANDO a {GOOGLE_URL}")
        logger.info(f"📦 Payload: {json.dumps(payload)}")
        
        response = requests.post(
            GOOGLE_URL, 
            json=payload, 
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        
        logger.info(f"📥 Status Code: {response.status_code}")
        logger.info(f"📥 Respuesta cruda: {response.text[:500]}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ JSON parseado: {json.dumps(result)[:500]}")
            return result
        else:
            logger.error(f"❌ Error HTTP: {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}", "productos": []}
            
    except Exception as e:
        logger.error(f"❌ EXCEPCIÓN: {str(e)}")
        return {"success": False, "error": str(e), "productos": []}

async def start(update: Update, context):
    """Inicio"""
    user = update.effective_user
    
    # TEST: Llamar a API inmediatamente y mostrar resultado
    logger.info("=" * 50)
    logger.info("TEST DE CONEXIÓN AL INICIAR")
    test_result = api_call("get_productos")
    logger.info(f"Test result: {test_result}")
    logger.info("=" * 50)
    
    productos_count = len(test_result.get('productos', []))
    
    await update.message.reply_text(
        f"""🐕‍🦺 *TCG Pet Store* 🐈

Hola {user.first_name}!

📊 *Diagnóstico:*
Productos en Google Sheets: `{productos_count}`
Conexión API: {'✅ OK' if test_result.get('success') else '❌ ERROR'}

{'✅ Sistema funcionando correctamente' if productos_count > 0 else '⚠️ No se encontraron productos. Verifica Google Sheets.'}

¿Qué deseas hacer?""",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Ver Productos", callback_data='prod')],
            [InlineKeyboardButton("🔄 Test Conexión", callback_data='test')],
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
        
        logger.info(f"Productos obtenidos: {len(productos)}")
        
        if not productos:
            error_msg = result.get('error', 'Sin error específico')
            await query.edit_message_text(
                f"""❌ *No hay productos*

Error: `{error_msg}`
Success: `{result.get('success')}`

*Verifica:*
1. ¿La hoja "productos" tiene datos?
2. ¿La Web App está publicada como "Cualquiera"?
3. ¿Las columnas tienen los nombres correctos?

ID Hoja: `1ddtqz7_pozoY4hFXmTFhLv81m5ZNtH0lOoC6SkDNNJk`""",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Reintentar", callback_data='prod')],
                    [InlineKeyboardButton("« Volver", callback_data='back')]
                ])
            )
            return
        
        text = "*🛒 Productos disponibles:*\n\n"
        for p in productos[:10]:  # Limitar a 10 para no saturar
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
        await query.edit_message_text(
            f"""*🧪 TEST DE CONEXIÓN*

Success: `{result.get('success')}`
Productos: `{len(result.get('productos', []))}`
Error: `{result.get('error', 'Ninguno')}`

Respuesta completa:

"""
TCG PET STORE - BOT ESTABLE v3.0
Compatible con Python 3.11+ y Render
"""

import logging
import requests
import json
import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# Configuración de logging detallado
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Cambiar a INFO en producción
)
logger = logging.getLogger(__name__)

# CONFIGURACIÓN - Verificar estas variables
TOKEN = "8604982984:AAGztYBQfjcUT0GnFQlgogamubCjNoPtZ7c"
GOOGLE_URL = "https://script.google.com/macros/s/AKfycbwaY1MURBCqgReCYJK7IvNPimWxSRw7tC3gkVGiP-ljxZosa8-PiULLwcGmsXAA3TH0/exec"

# Validar configuración al inicio
logger.info("=" * 60)
logger.info("INICIANDO BOT TCG PET STORE")
logger.info(f"Google URL: {GOOGLE_URL[:50]}...")
logger.info("=" * 60)

def api_call(action, data=None, max_retries=3):
    """
    Llama a Google Sheets API con reintentos y logging detallado
    """
    payload = {"action": action}
    if data:
        payload.update(data)
    
    for attempt in range(max_retries):
        try:
            logger.debug(f"Intento {attempt + 1}/{max_retries} - Action: {action}")
            logger.debug(f"Payload: {json.dumps(payload)}")
            
            response = requests.post(
                GOOGLE_URL, 
                json=payload, 
                timeout=30,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            )
            
            logger.debug(f"Response Status: {response.status_code}")
            logger.debug(f"Response Headers: {dict(response.headers)}")
            logger.debug(f"Response Body: {response.text[:500]}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.info(f"✅ API call exitoso: {action} - Success: {result.get('success')}")
                    return result
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Error decodificando JSON: {e}")
                    logger.error(f"Texto recibido: {response.text[:200]}")
                    return {"success": False, "error": "JSON invalido", "productos": []}
            else:
                logger.error(f"❌ HTTP Error {response.status_code}: {response.text[:200]}")
                if attempt < max_retries - 1:
                    continue
                return {"success": False, "error": f"HTTP {response.status_code}", "productos": []}
                
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout en intento {attempt + 1}")
            if attempt < max_retries - 1:
                continue
            return {"success": False, "error": "Timeout", "productos": []}
            
        except Exception as e:
            logger.error(f"❌ Excepción: {str(e)}")
            if attempt < max_retries - 1:
                continue
            return {"success": False, "error": str(e), "productos": []}
    
    return {"success": False, "error": "Max retries exceeded", "productos": []}

async def start(update: Update, context):
    """Handler de inicio con diagnóstico de conexión"""
    user = update.effective_user
    
    # Test de conexión inmediato
    logger.info(f"Usuario {user.first_name} inició sesión. Testeando conexión...")
    test_result = api_call("get_productos")
    
    productos_count = len(test_result.get('productos', []))
    conexion_ok = test_result.get('success', False) and productos_count > 0
    
    logger.info(f"Test de conexión: Success={test_result.get('success')}, Productos={productos_count}")
    
    if conexion_ok:
        mensaje = (
            f"🐕‍🦺 *¡Bienvenido a TCG Pet Store!* 🐈\n\n"
            f"Hola {user.first_name}, soy *Luna*.\n\n"
            f"✅ *Conexión establecida*\n"
            f"📦 {productos_count} productos disponibles\n\n"
            f"¿Qué deseas hacer?"
        )
    else:
        error_msg = test_result.get('error', 'Desconocido')
        mensaje = (
            f"🐕‍🦺 *TCG Pet Store* 🐈\n\n"
            f"Hola {user.first_name}.\n\n"
            f"⚠️ *Problema de conexión*\n"
            f"Error: `{error_msg}`\n\n"
            f"El catálogo puede no estar disponible temporalmente."
        )
    
    keyboard = [
        [InlineKeyboardButton("🛒 Ver Productos", callback_data='ver_productos')],
        [InlineKeyboardButton("📊 Ver Stock", callback_data='ver_stock')],
        [InlineKeyboardButton("ℹ️ Información", callback_data='info')]
    ]
    
    await update.message.reply_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def menu_handler(update: Update, context):
    """Handler central de callbacks"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    logger.info(f"Callback recibido: {data}")
    
    handlers = {
        'ver_productos': mostrar_productos,
        'ver_stock': mostrar_stock,
        'info': mostrar_info,
        'volver': start_callback,
    }
    
    handler = handlers.get(data)
    if handler:
        await handler(update, context)
    else:
        logger.warning(f"Callback no reconocido: {data}")
        await query.edit_message_text(
            "⚠️ Opción no disponible",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Volver", callback_data='volver')
            ]])
        )

async def mostrar_productos(update: Update, context):
    """Muestra lista de productos"""
    query = update.callback_query
    
    await query.edit_message_text("⏳ Cargando productos...")
    
    result = api_call("get_productos")
    productos = result.get('productos', [])
    
    if not productos:
        error = result.get('error', 'Sin error específico')
        await query.edit_message_text(
            f"❌ *No se pudieron cargar los productos*\n\n"
            f"Error: `{error}`\n\n"
            f"Por favor, intenta más tarde.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Reintentar", callback_data='ver_productos'),
                InlineKeyboardButton("« Volver", callback_data='volver')
            ]])
        )
        return
    
    mensaje = "*🛒 Productos Disponibles*\n\n"
    
    for p in productos:
        if p.get('stock', 0) > 0:
            precio = f"${p['precio']:,}".replace(',', '.')
            mensaje += f"✅ *{p['nombre']}*\n"
            mensaje += f"💰 {precio} | 📦 {p['stock']} u.\n\n"
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Actualizar", callback_data='ver_productos')],
            [InlineKeyboardButton("« Volver", callback_data='volver')]
        ])
    )

async def mostrar_stock(update: Update, context):
    """Muestra estadísticas de stock"""
    query = update.callback_query
    
    result = api_call("get_stats")
    stats = result.get('estadisticas', {})
    prod = stats.get('productos', {})
    
    mensaje = (
        "*📊 Inventario*\n\n"
        f"Total: {prod.get('total', 0)}\n"
        f"Disponibles: {prod.get('disponibles', 0)}\n"
        f"Agotados: {prod.get('agotados', 0)}\n"
        f"Valor: ${prod.get('valor_inventario', 0):,}".replace(',', '.')
    )
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("« Volver", callback_data='volver')
        ]])
    )

async def mostrar_info(update: Update, context):
    """Muestra información de la empresa"""
    query = update.callback_query
    
    mensaje = (
        "*🏭 TIT CAN GROSS (TCG)*\n\n"
        "15 años en Formosa, Argentina\n\n"
        "✅ Alimentos balanceados premium\n"
        "✅ Master Crock & Upper Crock\n"
        "✅ Stock inmediato"
    )
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("« Volver", callback_data='volver')
        ]])
    )

async def start_callback(update: Update, context):
    """Vuelve al menú principal"""
    query = update.callback_query
    # Simular nuevo mensaje
    await query.edit_message_text("Cargando menú...")
    await start(update, context)

async def error_handler(update: Update, context):
    """Manejo global de errores"""
    logger.error(f"Error: {context.error}", exc_info=True)
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "😅 Ocurrió un error. Intenta /start"
            )
    except:
        pass

async def main():
    """Función principal async"""
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(menu_handler))
    application.add_error_handler(error_handler)
    
    logger.info("🚀 Bot iniciado y escuchando...")
    
    await application.initialize()
    await application.start()
    
    # Usar polling con configuración estable
    await application.updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )
    
    # Mantener vivo
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot detenido por usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}")

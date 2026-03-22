"""
TCG PET STORE - BOT ESTABLE v3.0
Compatible con Python 3.14 y Render
"""

import logging
import requests
import json
import asyncio
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from telegram.error import Conflict, NetworkError

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# CONFIGURACIÓN - VERIFICAR ESTOS DATOS
TOKEN = "8604982984:AAGztYBQfjcUT0GnFQlgogamubCjNoPtZ7c"
GOOGLE_URL = "https://script.google.com/macros/library/d/1I6G4hoPgOZVoypp5SzBntSdrjZ76mY9fscWHPnjgy-5SX4bYgSmaRE0u/7"

def api_call(action, data=None, max_retries=3):
    """Llamada a Google Sheets con reintentos"""
    payload = {"action": action}
    if data:
        payload.update(data)
    
    for attempt in range(max_retries):
        try:
            logger.info(f"API Call: {action} (intento {attempt + 1})")
            response = requests.post(
                GOOGLE_URL, 
                json=payload, 
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.info(f"Success: {result.get('success', False)}")
                    return result
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    logger.error(f"Response text: {response.text[:200]}")
                    return {"success": False, "error": "Invalid JSON", "productos": []}
            else:
                logger.error(f"HTTP Error: {response.status_code}")
                if attempt < max_retries - 1:
                    continue
                return {"success": False, "error": f"HTTP {response.status_code}", "productos": []}
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout en intento {attempt + 1}")
            if attempt < max_retries - 1:
                continue
            return {"success": False, "error": "Timeout", "productos": []}
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            if attempt < max_retries - 1:
                continue
            return {"success": False, "error": str(e), "productos": []}
    
    return {"success": False, "error": "Max retries exceeded", "productos": []}

async def start(update: Update, context):
    """Inicio del bot"""
    user = update.effective_user
    
    # Inicializar carrito
    if 'carrito' not in context.user_data:
        context.user_data['carrito'] = []
    
    # Test de conexión
    logger.info("Testeando conexión con Google Sheets...")
    test_result = api_call("get_productos")
    
    productos_count = len(test_result.get('productos', []))
    conexion_ok = test_result.get('success', False) and productos_count > 0
    
    logger.info(f"Productos encontrados: {productos_count}")
    logger.info(f"Conexión OK: {conexion_ok}")
    
    mensaje = (
        f"🐕‍🦺 *¡Bienvenido a TCG Pet Store!* 🐈\n\n"
        f"Hola {user.first_name}, soy *Luna*, tu asesora.\n\n"
        f"Vendo alimentos *Master Crock* y *Upper Crock* de TCG.\n\n"
    )
    
    if conexion_ok:
        mensaje += f"✅ *Sistema online*\n📦 {productos_count} productos disponibles\n\n"
    else:
        mensaje += f"⚠️ *Advertencia:*\nError: `{test_result.get('error', 'Desconocido')}`\n\n"
    
    mensaje += "¿Qué deseas hacer?"
    
    keyboard = [
        [InlineKeyboardButton("🛒 Ver Productos", callback_data='ver_productos')],
        [InlineKeyboardButton("📊 Ver Stock", callback_data='consultar_stock')],
        [InlineKeyboardButton("💳 Pagos", callback_data='ver_pagos')],
        [InlineKeyboardButton("🚚 Envíos", callback_data='ver_envios')],
        [InlineKeyboardButton("ℹ️ Sobre TCG", callback_data='info_empresa')],
        [InlineKeyboardButton("📊 Admin", callback_data='demo_admin')]
    ]
    
    await update.message.reply_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def menu_handler(update: Update, context):
    """Maneja todas las callbacks"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    logger.info(f"Callback recibida: {data}")
    
    handlers = {
        'ver_productos': mostrar_categorias,
        'consultar_stock': menu_stock,
        'ver_pagos': mostrar_pagos,
        'ver_envios': mostrar_envios,
        'info_empresa': info_empresa,
        'demo_admin': demo_admin,
        'volver_inicio': volver_inicio,
        'ver_carrito': mostrar_carrito,
        'checkout': finalizar_compra,
        'vaciar_carrito': vaciar_carrito,
        'ver_inventario': mostrar_inventario,
    }
    
    try:
        if data.startswith('cat_'):
            await mostrar_productos_categoria(update, context)
        elif data.startswith('prod_'):
            await detalle_producto(update, context)
        elif data.startswith('cant_'):
            await agregar_carrito(update, context)
        elif data in handlers:
            await handlers[data](update, context)
        else:
            logger.warning(f"Callback desconocida: {data}")
            await query.edit_message_text(
                "⚠️ Opción no reconocida.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Volver", callback_data='volver_inicio')
                ]])
            )
    except Exception as e:
        logger.error(f"Error en handler: {str(e)}", exc_info=True)
        await query.edit_message_text(
            f"😅 Error: {str(e)[:100]}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Volver", callback_data='volver_inicio')
            ]])
        )

async def mostrar_categorias(update: Update, context):
    """Muestra categorías"""
    query = update.callback_query
    
    await query.edit_message_text(
        "🛍️ *¿Para quién buscas alimento?*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🐕 Perros", callback_data='cat_Perros')],
            [InlineKeyboardButton("🐈 Gatos", callback_data='cat_Gatos')],
            [InlineKeyboardButton("⭐ Destacados", callback_data='cat_destacados')],
            [InlineKeyboardButton("« Volver", callback_data='volver_inicio')]
        ])
    )

async def mostrar_productos_categoria(update: Update, context):
    """Muestra productos por categoría"""
    query = update.callback_query
    categoria = query.data.replace('cat_', '')
    
    logger.info(f"Solicitando productos de: {categoria}")
    
    if categoria == 'destacados':
        result = api_call("get_productos", {"solo_stock": True})
        productos = [p for p in result.get('productos', []) if p.get('destacado')]
        titulo = "⭐ Destacados"
    else:
        result = api_call("get_productos", {"categoria": categoria})
        productos = result.get('productos', [])
        titulo = f"🐕🐈 {categoria}"
    
    logger.info(f"Productos encontrados: {len(productos)}")
    
    if not productos:
        error_detail = result.get('error', 'Sin error específico')
        await query.edit_message_text(
            f"❌ *No hay productos*\n\nError: `{error_detail}`\n\n"
            f"Verifica que la hoja 'productos' tenga datos.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Volver", callback_data='ver_productos')
            ]])
        )
        return
    
    mensaje = f"*{titulo}*\n\n"
    keyboard = []
    
    for p in productos:
        stock_emoji = "✅" if p['stock'] > 0 else "❌"
        precio = f"${p['precio']:,}".replace(',', '.')
        mensaje += f"{stock_emoji} *{p['nombre']}*\n💰 {precio} | 📦 {p['stock']} u.\n\n"
        
        if p['stock'] > 0:
            keyboard.append([InlineKeyboardButton(
                f"🛒 {p['nombre'][:25]}...", 
                callback_data=f'prod_{p["sku"]}'
            )])
    
    keyboard.append([InlineKeyboardButton("« Volver", callback_data='ver_productos')])
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def detalle_producto(update: Update, context):
    """Muestra detalle de producto"""
    query = update.callback_query
    sku = query.data.replace('prod_', '')
    
    result = api_call("get_producto", {"sku": sku})
    
    if not result.get('success'):
        await query.edit_message_text("❌ Producto no encontrado")
        return
    
    p = result['producto']
    context.user_data['producto_actual'] = p
    
    stock_emoji = "🟢" if p['stock'] > 10 else "🟡" if p['stock'] > 0 else "🔴"
    precio = f"${p['precio']:,}".replace(',', '.')
    
    mensaje = (
        f"*{p['nombre']}* {stock_emoji}\n\n"
        f"💰 *Precio:* {precio}\n"
        f"📦 *Stock:* {p['stock']} u.\n\n"
        f"_{p['descripcion']}_\n\n"
    )
    
    keyboard = []
    if p['stock'] > 0:
        mensaje += "*¿Cuántas unidades?*"
        cantidades = [1, 2, 3] if p['stock'] >= 3 else list(range(1, p['stock'] + 1))
        row = [InlineKeyboardButton(str(c), callback_data=f'cant_{c}') for c in cantidades]
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("« Volver", callback_data='ver_productos')])
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def agregar_carrito(update: Update, context):
    """Agrega al carrito"""
    query = update.callback_query
    cantidad = int(query.data.replace('cant_', ''))
    p = context.user_data.get('producto_actual')
    
    if not p:
        return
    
    item = {
        'sku': p['sku'],
        'nombre': p['nombre'],
        'precio': p['precio'],
        'cantidad': cantidad,
        'subtotal': p['precio'] * cantidad
    }
    
    if 'carrito' not in context.user_data:
        context.user_data['carrito'] = []
    
    carrito = context.user_data['carrito']
    existente = next((i for i in carrito if i['sku'] == item['sku']), None)
    
    if existente:
        existente['cantidad'] += cantidad
        existente['subtotal'] = existente['precio'] * existente['cantidad']
    else:
        carrito.append(item)
    
    total = sum(i['subtotal'] for i in carrito)
    
    mensaje = (
        f"✅ *Agregado:*\n{item['nombre']} x{cantidad}\n\n"
        f"🛒 Carrito: {len(carrito)} items\n"
        f"💰 Total: ${total:,}"
    ).replace(',', '.')
    
    keyboard = [
        [InlineKeyboardButton("🛍️ Seguir comprando", callback_data='ver_productos')],
        [InlineKeyboardButton("📋 Ver carrito", callback_data='ver_carrito')],
        [InlineKeyboardButton("💳 Finalizar", callback_data='checkout')],
        [InlineKeyboardButton("« Inicio", callback_data='volver_inicio')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def mostrar_carrito(update: Update, context):
    """Muestra carrito"""
    query = update.callback_query
    carrito = context.user_data.get('carrito', [])
    
    if not carrito:
        await query.edit_message_text(
            "🛒 Carrito vacío",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Volver", callback_data='volver_inicio')
            ]

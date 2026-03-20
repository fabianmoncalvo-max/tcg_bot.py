"""
TCG PET STORE - BOT DE VENTAS DEMO COMPLETO
Version profesional con todas las funcionalidades
"""

import logging
import requests
import json
import asyncio  # <-- AGREGADO para Python 3.14
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# Configuracion
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8604982984:AAGztYBQfjcUT0GnFQlgogamubCjNoPtZ7c"
GOOGLE_URL = "https://script.google.com/macros/s/AKfycbzMNJM8INFE8k7mHh4Bz_7mnLeJ1I8CkkUlHRyIUytE3LDGpkvwmwLMHOKiAddeqlu3/exec"

def api_call(action, data=None):
    """Llamada a Google Sheets"""
    try:
        payload = {"action": action}
        if data:
            payload.update(data)
        
        response = requests.post(
            GOOGLE_URL, 
            json=payload, 
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"success": False, "error": "HTTP " + str(response.status_code), "productos": []}
            
    except Exception as e:
        logger.error("Error API: %s", str(e))
        return {"success": False, "error": str(e), "productos": []}

async def start(update: Update, context):
    """Inicio - Menu principal completo"""
    user = update.effective_user
    
    mensaje = (
        "🐕‍🦺 *¡Bienvenido a TCG Pet Store!* 🐈\n\n"
        f"Hola {user.first_name}, soy *Luna*, tu asesora de confianza.\n\n"
        "Vendo los mejores alimentos balanceados de Argentina: *Master Crock* y *Upper Crock*, "
        "fabricados por TIT CAN GROSS (TCG) con 15 años de experiencia.\n\n"
        "✅ *¿Por qué elegir TCG?*\n"
        "• Fórmulas argentinas adaptadas a nuestra región\n"
        "• Proteínas de alta calidad (26-30%)\n"
        "• Sin colorantes artificiales\n"
        "• Precio directo de fábrica\n"
        "• Stock inmediato en Formosa\n\n"
        "¿En qué puedo ayudarte hoy?"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛒 Ver Productos", callback_data='ver_productos')],
        [InlineKeyboardButton("📦 Consultar Stock", callback_data='consultar_stock')],
        [InlineKeyboardButton("💳 Métodos de Pago", callback_data='ver_pagos')],
        [InlineKeyboardButton("🚚 Envíos y Retiro", callback_data='ver_envios')],
        [InlineKeyboardButton("ℹ️ Sobre TCG", callback_data='info_empresa')],
        [InlineKeyboardButton("📊 Ver Demo Admin", callback_data='demo_admin')]
    ]
    
    await update.message.reply_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def menu_handler(update: Update, context):
    """Maneja todos los botones del menu"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    try:
        if data == 'ver_productos':
            await mostrar_categorias(update, context)
        elif data.startswith('cat_'):
            await mostrar_productos_categoria(update, context)
        elif data.startswith('prod_'):
            await detalle_producto(update, context)
        elif data.startswith('cant_'):
            await agregar_carrito(update, context)
        elif data == 'consultar_stock':
            await menu_stock(update, context)
        elif data == 'ver_inventario':
            await mostrar_inventario(update, context)
        elif data == 'ver_pagos':
            await mostrar_pagos(update, context)
        elif data == 'ver_envios':
            await mostrar_envios(update, context)
        elif data == 'info_empresa':
            await info_empresa(update, context)
        elif data == 'demo_admin':
            await demo_admin(update, context)
        elif data == 'volver_inicio':
            await volver_inicio(update, context)
        elif data == 'ver_carrito':
            await mostrar_carrito(update, context)
        else:
            await query.edit_message_text(
                "⚠️ Opción no reconocida.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Volver al inicio", callback_data='volver_inicio')
                ]])
            )
    except Exception as e:
        logger.error("Error en menu: %s", str(e))
        await query.edit_message_text(
            "😅 Ups, algo salió mal. Intenta de nuevo.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Volver al inicio", callback_data='volver_inicio')
            ]])
        )

async def mostrar_categorias(update: Update, context):
    """Muestra categorias de productos"""
    query = update.callback_query
    
    mensaje = (
        "🛍️ *Nuestro Catálogo*\n\n"
        "¿Para quién buscas alimento?"
    )
    
    keyboard = [
        [InlineKeyboardButton("🐕 Perros", callback_data='cat_Perros')],
        [InlineKeyboardButton("🐈 Gatos", callback_data='cat_Gatos')],
        [InlineKeyboardButton("⭐ Destacados", callback_data='cat_destacados')],
        [InlineKeyboardButton("🔍 Ver Todo el Inventario", callback_data='ver_inventario')],
        [InlineKeyboardButton("« Volver al inicio", callback_data='volver_inicio')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def mostrar_productos_categoria(update: Update, context):
    """Muestra productos por categoria"""
    query = update.callback_query
    categoria = query.data.replace('cat_', '')
    
    if categoria == 'destacados':
        result = api_call("get_productos", {"solo_stock": True})
        productos = [p for p in result.get('productos', []) if p.get('destacado')]
        titulo = "⭐ Productos Destacados"
    else:
        result = api_call("get_productos", {"categoria": categoria, "solo_stock": False})
        productos = result.get('productos', [])
        emoji = "🐕" if categoria == "Perros" else "🐈"
        titulo = f"{emoji} Alimentos para {categoria}"
    
    if not productos:
        await query.edit_message_text(
            "😔 No hay productos en esta categoría actualmente.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Volver", callback_data='ver_productos')
            ]])
        )
        return
    
    mensaje = f"*{titulo}*\n\n"
    keyboard = []
    
    for p in productos:
        stock_emoji = "✅" if p['stock'] > 0 else "❌"
        stock_text = f"{p['stock']} u." if p['stock'] > 0 else "AGOTADO"
        precio = f"${p['precio']:,}".replace(',', '.')
        
        mensaje += f"{stock_emoji} *{p['nombre']}*\n💰 {precio} | 📦 {stock_text}\n\n"
        
        if p['stock'] > 0:
            keyboard.append([InlineKeyboardButton(
                f"🛒 {p['nombre'][:30]}...", 
                callback_data=f'prod_{p["sku"]}'
            )])
    
    keyboard.append([InlineKeyboardButton("« Volver a categorías", callback_data='ver_productos')])
    keyboard.append([InlineKeyboardButton("🏠 Menú Principal", callback_data='volver_inicio')])
    
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
        await query.edit_message_text(
            "❌ Producto no encontrado",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Volver", callback_data='ver_productos')
            ]])
        )
        return
    
    p = result['producto']
    context.user_data['producto_actual'] = p
    
    stock_emoji = "🟢" if p['stock'] > 10 else "🟡" if p['stock'] > 0 else "🔴"
    precio = f"${p['precio']:,}".replace(',', '.')
    
    mensaje = (
        f"*{p['nombre']}* {stock_emoji}\n\n"
        f"💰 *Precio:* {precio}\n"
        f"📦 *Stock:* {p['stock']} unidades\n"
        f"🏷️ *SKU:* `{p['sku']}`\n\n"
        f"📝 *Descripción:*\n_{p['descripcion']}_\n\n"
    )
    
    if p.get('destacado'):
        mensaje += "✨ *Producto destacado*\n\n"
    
    keyboard = []
    
    if p['stock'] > 0:
        mensaje += "*¿Cuántas unidades deseas?*"
        cantidades = [1, 2, 3] if p['stock'] >= 3 else list(range(1, p['stock'] + 1))
        row = [InlineKeyboardButton(str(c), callback_data=f'cant_{c}') for c in cantidades]
        keyboard.append(row)
    else:
        mensaje += "⚠️ *Producto temporalmente agotado*"
        keyboard.append([InlineKeyboardButton("🔍 Ver alternativas", callback_data=f'cat_{p["categoria"]}')])
    
    keyboard.append([InlineKeyboardButton("« Volver al catálogo", callback_data='ver_productos')])
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def agregar_carrito(update: Update, context):
    """Agrega producto al carrito"""
    query = update.callback_query
    cantidad = int(query.data.replace('cant_', ''))
    p = context.user_data.get('producto_actual')
    
    if not p:
        return
    
    check = api_call("check_stock", {"sku": p['sku'], "cantidad": cantidad})
    
    if not check.get('disponible'):
        await query.edit_message_text(
            f"❌ Solo quedan {check.get('stock_actual', 0)} unidades disponibles",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Volver", callback_data=f'prod_{p["sku"]}')
            ]])
        )
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
        f"✅ *Agregado al carrito:*\n\n"
        f"*{item['nombre']}*\n"
        f"Cantidad: {cantidad} x ${item['precio']:,} = ${item['subtotal']:,}\n\n"
        f"🛒 *Carrito:* {len(carrito)} productos\n"
        f"💰 *Total:* ${total:,}"
    ).replace(',', '.')
    
    keyboard = [
        [InlineKeyboardButton("🛍️ Seguir comprando", callback_data='ver_productos')],
        [InlineKeyboardButton("📋 Ver carrito", callback_data='ver_carrito')],
        [InlineKeyboardButton("💳 Finalizar compra", callback_data='checkout')],
        [InlineKeyboardButton("« Menú Principal", callback_data='volver_inicio')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def mostrar_carrito(update: Update, context):
    """Muestra contenido del carrito"""
    query = update.callback_query
    carrito = context.user_data.get('carrito', [])
    
    if not carrito:
        await query.edit_message_text(
            "🛒 Tu carrito está vacío",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Ver Productos", callback_data='ver_productos')],
                [InlineKeyboardButton("« Volver", callback_data='volver_inicio')]
            ])
        )
        return
    
    mensaje = "🛒 *Tu Carrito*\n\n"
    total = 0
    
    for i, item in enumerate(carrito, 1):
        subtotal_fmt = f"${item['subtotal']:,}".replace(',', '.')
        mensaje += f"{i}. *{item['nombre']}*\n{item['cantidad']} x ${item['precio']:,} = {subtotal_fmt}\n\n".replace(',', '.')
        total += item['subtotal']
    
    mensaje += f"💰 *Total:* ${total:,}".replace(',', '.')
    
    keyboard = [
        [InlineKeyboardButton("🛍️ Agregar más", callback_data='ver_productos')],
        [InlineKeyboardButton("💳 Finalizar", callback_data='checkout')],
        [InlineKeyboardButton("🗑️ Vaciar", callback_data='vaciar_carrito')],
        [InlineKeyboardButton("« Volver", callback_data='volver_inicio')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def menu_stock(update: Update, context):
    """Menu de consulta de stock"""
    query = update.callback_query
    
    mensaje = (
        "📦 *Consulta de Stock en Tiempo Real*\n\n"
        "Puedo verificar disponibilidad al instante."
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 Ver inventario completo", callback_data='ver_inventario')],
        [InlineKeyboardButton("« Volver al inicio", callback_data='volver_inicio')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def mostrar_inventario(update: Update, context):
    """Muestra inventario completo"""
    query = update.callback_query
    result = api_call("get_productos", {"solo_stock": False})
    productos = result.get('productos', [])
    
    mensaje = "*📊 Inventario Completo*\n\n"
    
    for p in productos:
        emoji = "✅" if p['stock'] > 5 else "⚠️" if p['stock'] > 0 else "❌"
        precio = f"${p['precio']:,}".replace(',', '.')
        mensaje += f"{emoji} *{p['nombre'][:22]}*\nStock: `{p['stock']}` u. | {precio}\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Actualizar", callback_data='ver_inventario')],
        [InlineKeyboardButton("« Volver", callback_data='consultar_stock')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def mostrar_pagos(update: Update, context):
    """Muestra metodos de pago"""
    query = update.callback_query
    
    mensaje = (
        "💳 *Métodos de Pago Disponibles*\n\n"
        "*Opciones con descuento:*\n"
        "• 💵 *Efectivo* → 10% OFF (retiro en local)\n"
        "• 📲 *Transferencia* → 5% OFF\n\n"
        "*Otras opciones:*\n"
        "• 💳 Mercado Pago (tarjeta/QR)\n"
        "• 🏦 Depósito bancario\n\n"
        "*Garantía:* Si tu mascota no come el alimento en 7 días, *te devolvemos el 100%*."
    )
    
    keyboard = [
        [InlineKeyboardButton("🛒 Ir a Comprar", callback_data='ver_productos')],
        [InlineKeyboardButton("« Volver al inicio", callback_data='volver_inicio')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def mostrar_envios(update: Update, context):
    """Muestra opciones de envio"""
    query = update.callback_query
    
    mensaje = (
        "🚚 *Envíos y Retiro - Formosa*\n\n"
        "*Formosa Capital:*\n"
        "• 🏍️ *Moto mensajería:* $2.500 (2-4 horas)\n"
        "• 🚗 *Delivery propio:* $1.800 (24-48 hs)\n"
        "• 🏪 *Retiro en local:* GRATIS\n"
        "  📍 Av. 9 de Julio 1234, Formosa\n\n"
        "*Interior:*\n"
        "• 🚌 Terminal: $3.500 - $5.500\n"
        "• 📦 Correo Argentino: A convenir\n\n"
        "🎁 *ENVÍO GRATIS* en compras +$50.000"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛒 Ir a Comprar", callback_data='ver_productos')],
        [InlineKeyboardButton("« Volver al inicio", callback_data='volver_inicio')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def info_empresa(update: Update, context):
    """Informacion sobre TCG"""
    query = update.callback_query
    
    mensaje = (
        "🏭 *TIT CAN GROSS (TCG)*\n\n"
        "*15 años nutriendo mascotas argentinas*\n\n"
        "🥩 *Nuestra fórmula:*\n"
        "• Proteínas de origen animal certificadas\n"
        "• Granos seleccionados de la región\n"
        "• Sin subproductos de dudosa procedencia\n"
        "• Omega 3 y 6 naturales\n\n"
        "*Líneas:*\n"
        "🏆 *Master Crock* → Calidad-precio\n"
        "⭐ *Upper Crock* → Máximo rendimiento\n\n"
        "📍 *Fábrica:* Formosa, Argentina\n"
        "✅ *Autorizado SENASA*"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛒 Ver Productos", callback_data='ver_productos')],
        [InlineKeyboardButton("« Volver", callback_data='volver_inicio')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def demo_admin(update: Update, context):
    """Panel de administracion demo"""
    query = update.callback_query
    
    result = api_call("get_stats")
    stats = result.get('estadisticas', {})
    prod = stats.get('productos', {})
    ventas = stats.get('ventas', {})
    
    mensaje = (
        "📊 *PANEL DE ADMINISTRACIÓN - DEMO*\n\n"
        "*Este es el panel que verías como dueño:*\n\n"
        "📦 *Inventario:*\n"
        f"• Total productos: `{prod.get('total', 0)}`\n"
        f"• Disponibles: `{prod.get('disponibles', 0)}` ✅\n"
        f"• Agotados: `{prod.get('agotados', 0)}` ❌\n"
        f"• Valor stock: `${prod.get('valor_inventario', 0):,}`\n\n"
        "💰 *Ventas:*\n"
        f"• Transacciones: `{ventas.get('total', 0)}`\n"
        f"• Facturación: `${ventas.get('monto_total', 0):,}`\n\n"
        "👥 *Clientes:* `{stats.get('clientes', 0)}`\n\n"
        "*Todo se actualiza en tiempo real desde Google Sheets*"
    ).replace(',', '.')
    
    keyboard = [
        [InlineKeyboardButton("🔄 Actualizar Datos", callback_data='demo_admin')],
        [InlineKeyboardButton("📦 Gestionar Stock", callback_data='ver_inventario')],
        [InlineKeyboardButton("« Volver al inicio", callback_data='volver_inicio')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def volver_inicio(update: Update, context):
    """Vuelve al menu principal"""
    query = update.callback_query
    
    mensaje = (
        "🐕‍🦺 *TCG Pet Store* 🐈\n\n"
        "¿En qué puedo ayudarte ahora?"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛒 Ver Productos", callback_data='ver_productos')],
        [InlineKeyboardButton("📦 Consultar Stock", callback_data='consultar_stock')],
        [InlineKeyboardButton("💳 Métodos de Pago", callback_data='ver_pagos')],
        [InlineKeyboardButton("🚚 Envíos y Retiro", callback_data='ver_envios')],
        [InlineKeyboardButton("ℹ️ Sobre TCG", callback_data='info_empresa')],
        [InlineKeyboardButton("📊 Ver Demo Admin", callback_data='demo_admin')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def error_handler(update: Update, context):
    """Maneja errores"""
    logger.error("Error: %s", context.error)
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "😅 Ups, algo salió mal. Intenta de nuevo con /start"
            )
    except:
        pass

def main():
    """Funcion principal - CORREGIDA PARA PYTHON 3.14"""
    # Crear explícitamente el event loop para Python 3.14+
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(menu_handler))
    app.add_error_handler(error_handler)
    
    logger.info("=" * 50)
    logger.info("TCG BOT - VERSION COMPLETA INICIADA")
    logger.info("=" * 50)
    print("🚀 Bot iniciado!")
    
    # Usar close_loop=False para evitar problemas con el event loop
    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == '__main__':
    main()

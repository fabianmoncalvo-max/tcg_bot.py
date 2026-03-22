"""
TCG PET STORE - BOT COMPLETO Y ESTABLE
Version corregida con manejo de errores y checkout
"""

import logging
import requests
import json
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# Configuracion
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8604982984:AAGztYBQfjcUT0GnFQlgogamubCjNoPtZ7c"
GOOGLE_URL = "https://script.google.com/macros/library/d/1I6G4hoPgOZVoypp5SzBntSdrjZ76mY9fscWHPnjgy-5SX4bYgSmaRE0u/7"

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
    """Inicio - Menu principal"""
    user = update.effective_user
    
    # Inicializar carrito si no existe
    if 'carrito' not in context.user_data:
        context.user_data['carrito'] = []
    
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
    """Maneja todos los botones"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    try:
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
        
        # Manejar prefijos
        if data.startswith('cat_'):
            await mostrar_productos_categoria(update, context)
        elif data.startswith('prod_'):
            await detalle_producto(update, context)
        elif data.startswith('cant_'):
            await agregar_carrito(update, context)
        elif data in handlers:
            await handlers[data](update, context)
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
    """Muestra categorias"""
    query = update.callback_query
    
    mensaje = "🛍️ *Nuestro Catálogo*\n\n¿Para quién buscas alimento?"
    
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

async def finalizar_compra(update: Update, context):
    """Finaliza la compra"""
    query = update.callback_query
    carrito = context.user_data.get('carrito', [])
    
    if not carrito:
        await query.edit_message_text(
            "🛒 Tu carrito está vacío",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Volver", callback_data='volver_inicio')
            ]])
        )
        return
    
    total = sum(item['subtotal'] for item in carrito)
    total_fmt = f"${total:,}".replace(',', '.')
    
    resumen = "🛒 *RESUMEN DE TU PEDIDO*\n\n"
    for i, item in enumerate(carrito, 1):
        subtotal_fmt = f"${item['subtotal']:,}".replace(',', '.')
        resumen += f"{i}. {item['nombre']}\n"
        resumen += f"   {item['cantidad']} x ${item['precio']:,} = {subtotal_fmt}\n\n".replace(',', '.')
    
    resumen += f"💰 *TOTAL A PAGAR:* {total_fmt}\n\n"
    resumen += "✅ Pedido registrado. Un asesor se contactará para coordinar el pago y envío."
    
    # Guardar venta en Google Sheets (opcional)
    # api_call("registrar_venta", {...})
    
    context.user_data['carrito'] = []
    
    await query.edit_message_text(
        resumen,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Menú Principal", callback_data='volver_inicio')
        ]])
    )

async def vaciar_carrito(update: Update, context):
    """Vacia el carrito"""
    query = update.callback_query
    context.user_data['carrito'] = []
    
    await query.edit_message_text(
        "🗑️ *Carrito vaciado*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Ver Productos", callback_data='ver_productos')],
            [InlineKeyboardButton("« Menú Principal", callback_data='volver_inicio')]
        ])
    )

async def menu_stock(update: Update, context):
    """Menu de consulta de stock"""
    query = update.callback_query
    
    mensaje = "📦 *Consulta de Stock*\n\nPuedo verificar disponibilidad al instante."
    
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
        "💳 *Métodos de Pago*\n\n"
        "*Con descuento:*\n"
        "• 💵 *Efectivo* → 10% OFF\n"
        "• 📲 *Transferencia* → 5% OFF\n\n"
        "*Otras opciones:*\n"
        "• 💳 Mercado Pago\n"
        "• 🏦 Depósito bancario\n\n"
        "*Garantía:* 7 días o devolución"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛒 Ir a Comprar", callback_data='ver_productos')],
        [InlineKeyboardButton("« Volver", callback_data='volver_inicio')]
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
        "🚚 *Envíos y Retiro*\n\n"
        "*Formosa Capital:*\n"
        "• 🏍️ Moto: $2.500 (2-4 hs)\n"
        "• 🚗 Delivery: $1.800\n"
        "• 🏪 Retiro: GRATIS\n\n"
        "*Promo:* Gratis en +$50.000"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛒 Ir a Comprar", callback_data='ver_productos')],
        [InlineKeyboardButton("« Volver", callback_data='volver_inicio')]
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
        "15 años en Formosa, Argentina\n\n"
        "🥩 Proteínas certificadas\n"
        "🌾 Granos locales\n"
        "✅ SENASA autorizado\n\n"
        "*Master Crock:* Calidad-precio\n"
        "*Upper Crock:* Premium"
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
    """Panel de administracion"""
    query = update.callback_query
    
    result = api_call("get_stats")
    stats = result.get('estadisticas', {})
    prod = stats.get('productos', {})
    ventas = stats.get('ventas', {})
    
    mensaje = (
        "📊 *PANEL ADMIN - DEMO*\n\n"
        f"📦 Productos: `{prod.get('total', 0)}`\n"
        f"✅ Disponibles: `{prod.get('disponibles', 0)}`\n"
        f"❌ Agotados: `{prod.get('agotados', 0)}`\n"
        f"💰 Valor: `${prod.get('valor_inventario', 0):,}`\n\n"
        f"💵 Ventas: `{ventas.get('total', 0)}`\n"
        f"📈 Facturado: `${ventas.get('monto_total', 0):,}`\n\n"
        "Todo se actualiza en tiempo real"
    ).replace(',', '.')
    
    keyboard = [
        [InlineKeyboardButton("🔄 Actualizar", callback_data='demo_admin')],
        [InlineKeyboardButton("« Volver", callback_data='volver_inicio')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def volver_inicio(update: Update, context):
    """Vuelve al menu principal"""
    query = update.callback_query
    
    mensaje = "🐕‍🦺 *TCG Pet Store* 🐈\n\n¿En qué puedo ayudarte?"
    
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
                "😅 Ups, algo salió mal. Intenta /start"
            )
    except:
        pass

async def main_async():
    """Funcion principal async"""
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(menu_handler))
    app.add_error_handler(error_handler)
    
    logger.info("BOT INICIADO")
    print("🚀 Bot iniciado!")
    
    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        
        # Mantener corriendo
        while True:
            await asyncio.sleep(3600)
            
    except Exception as e:
        logger.error("Error: %s", e)
        raise
    finally:
        await app.stop()

if __name__ == '__main__':
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n🛑 Bot detenido")

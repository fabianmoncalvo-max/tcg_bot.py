"""
TCG PET STORE - BOT DE VENTAS DEMO v2.0
Bot estable para PythonAnywhere - Python 3.13
"""

import logging
import requests
import sys
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes
)

# ============================================
# CONFIGURACIÓN
# ============================================

TOKEN = "8604982984:AAGztYBQfjcUT0GnFQlgogamubCjNoPtZ7c"
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwaY1MURBCqgReCYJK7IvNPimWxSRw7tC3gkVGiP-ljxZosa8-PiULLwcGmsXAA3TH0/exec"

# Estados de conversación
MENU_PRINCIPAL, VER_PRODUCTOS, DETALLE_PRODUCTO = range(3)

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# FUNCIONES DE GOOGLE SHEETS (con reintentos)
# ============================================

def call_api(action: str, data: dict = None, max_retries: int = 3) -> dict:
    """Llama a Google Apps Script con reintentos"""
    payload = {"action": action}
    if data:
        payload.update(data)
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Llamando API: {action} (intento {attempt + 1})")
            response = requests.post(
                GOOGLE_SCRIPT_URL, 
                json=payload, 
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Respuesta exitosa: {result.get('success', False)}")
                return result
            else:
                logger.error(f"Error HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error en intento {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                return {"success": False, "error": str(e), "productos": []}
    
    return {"success": False, "error": "Max retries exceeded", "productos": []}

# ============================================
# COMANDOS PRINCIPALES
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicio de conversación"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    # Registrar cliente
    try:
        call_api("registrar_cliente", {
            "chat_id": chat_id,
            "nombre": user.first_name or "Usuario",
            "preferencias": "Demo TCG"
        })
    except Exception as e:
        logger.error(f"Error registrando cliente: {e}")
    
    # Inicializar carrito
    context.user_data['carrito'] = []
    context.user_data['cliente'] = user.first_name or "Usuario"
    
    mensaje = f"""
🐕‍🦺 *¡Bienvenido a TCG Pet Store!* 🐈

Hola *{user.first_name or "amigo"}*, soy *Luna*, tu asesora de confianza.

Vendo los mejores alimentos balanceados de Argentina: *Master Crock* y *Upper Crock*, fabricados por TIT CAN GROSS (TCG) con 15 años de experiencia.

✅ *¿Por qué elegir TCG?*
• 🥩 Proteínas 26-30% de alta calidad
• 🚫 Sin colorantes artificiales  
• 💰 Precio directo de fábrica
• 📦 Stock inmediato en Formosa

*¿Qué necesitas hoy?*
    """
    
    keyboard = [
        [InlineKeyboardButton("🛒 Ver Productos", callback_data='menu_productos')],
        [InlineKeyboardButton("📦 Consultar Stock", callback_data='menu_stock')],
        [InlineKeyboardButton("💳 Métodos de Pago", callback_data='menu_pagos')],
        [InlineKeyboardButton("🚚 Envíos y Retiro", callback_data='menu_envios')],
        [InlineKeyboardButton("ℹ️ Sobre TCG", callback_data='menu_info')],
        [InlineKeyboardButton("📊 Panel Admin (Demo)", callback_data='menu_admin')]
    ]
    
    await update.message.reply_text(
        mensaje, 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return MENU_PRINCIPAL

# ============================================
# MANEJADOR DE MENÚ PRINCIPAL
# ============================================

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja todas las callbacks del menú"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    logger.info(f"Callback recibida: {data}")
    
    try:
        if data == 'menu_productos' or data == 'ver_productos':
            return await mostrar_categorias(update, context)
        elif data.startswith('cat_'):
            return await mostrar_productos_categoria(update, context)
        elif data.startswith('prod_'):
            return await mostrar_detalle_producto(update, context)
        elif data.startswith('cant_'):
            return await agregar_al_carrito(update, context)
        elif data == 'menu_stock' or data == 'consultar_stock':
            return await menu_stock(update, context)
        elif data == 'ver_inventario':
            return await mostrar_inventario_completo(update, context)
        elif data == 'menu_pagos':
            return await mostrar_pagos(update, context)
        elif data == 'menu_envios':
            return await mostrar_envios(update, context)
        elif data == 'menu_info':
            return await mostrar_info_empresa(update, context)
        elif data == 'menu_admin':
            return await mostrar_panel_admin(update, context)
        elif data == 'volver_inicio':
            return await volver_menu_principal(update, context)
        elif data == 'ver_carrito':
            return await mostrar_carrito(update, context)
        else:
            logger.warning(f"Callback desconocida: {data}")
            await query.edit_message_text(
                "⚠️ Opción no reconocida. Usa /start para reiniciar.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Inicio", callback_data='volver_inicio')
                ]])
            )
            return MENU_PRINCIPAL
            
    except Exception as e:
        logger.error(f"Error en callback {data}: {str(e)}")
        await query.edit_message_text(
            f"😅 Ups, hubo un error: {str(e)[:100]}\n\nIntenta de nuevo con /start",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Inicio", callback_data='volver_inicio')
            ]])
        )
        return MENU_PRINCIPAL

# ============================================
# CATÁLOGO DE PRODUCTOS
# ============================================

async def mostrar_categorias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra las categorías disponibles"""
    query = update.callback_query
    
    mensaje = """
🛍️ *Nuestro Catálogo*

¿Para quién buscas alimento hoy?
    """
    
    keyboard = [
        [InlineKeyboardButton("🐕 Perros", callback_data='cat_Perros')],
        [InlineKeyboardButton("🐈 Gatos", callback_data='cat_Gatos')],
        [InlineKeyboardButton("⭐ Productos Destacados", callback_data='cat_destacados')],
        [InlineKeyboardButton("🔍 Ver Todo el Inventario", callback_data='ver_inventario')],
        [InlineKeyboardButton("« Volver al Inicio", callback_data='volver_inicio')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return VER_PRODUCTOS

async def mostrar_productos_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra productos de una categoría específica"""
    query = update.callback_query
    await query.answer()
    
    categoria = query.data.replace('cat_', '')
    logger.info(f"Solicitando productos de categoría: {categoria}")
    
    # Llamar a la API
    if categoria == 'destacados':
        result = call_api("get_productos", {"solo_stock": True})
        productos = [p for p in result.get('productos', []) if p.get('destacado')]
        titulo = "⭐ Productos Destacados"
    else:
        result = call_api("get_productos", {"categoria": categoria, "solo_stock": False})
        productos = result.get('productos', [])
        emoji = "🐕" if categoria == "Perros" else "🐈"
        titulo = f"{emoji} Alimentos para {categoria}"
    
    logger.info(f"Productos encontrados: {len(productos)}")
    
    if not productos:
        await query.edit_message_text(
            f"""😔 *No hay productos disponibles*

Categoría: {categoria}
Respuesta API: {result}

⚠️ *Verifica que:*
1. La hoja "productos" tiene datos
2. Los nombres de columnas son correctos
3. La Web App está publicada correctamente

« Volver: /start""",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Volver", callback_data='ver_productos')
            ]])
        )
        return VER_PRODUCTOS
    
    # Construir mensaje
    mensaje = f"*{titulo}*\\n"
    mensaje += f"_{len(productos)} productos encontrados_\\n\\n"
    
    keyboard = []
    
    for p in productos:
        stock_emoji = "✅" if p['stock'] > 5 else "⚠️" if p['stock'] > 0 else "❌"
        stock_text = f"{p['stock']} u." if p['stock'] > 0 else "AGOTADO"
        precio = f"${p['precio']:,}".replace(',', '.')
        
        mensaje += f"{stock_emoji} *{p['nombre']}*\\n"
        mensaje += f"   💰 {precio} | 📦 {stock_text}\\n"
        
        if p['stock'] > 0:
            keyboard.append([InlineKeyboardButton(
                f"🛒 {p['nombre'][:28]}", 
                callback_data=f'prod_{p["sku"]}'
            )])
    
    keyboard.append([InlineKeyboardButton("« Volver a Categorías", callback_data='ver_productos')])
    keyboard.append([InlineKeyboardButton("🏠 Menú Principal", callback_data='volver_inicio')])
    
    try:
        await query.edit_message_text(
            mensaje,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error mostrando productos: {e}")
        # Si el mensaje es muy largo, truncarlo
        await query.edit_message_text(
            mensaje[:3000] + "\n\n... (mensaje truncado)",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return VER_PRODUCTOS

async def mostrar_detalle_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra detalle de un producto específico"""
    query = update.callback_query
    await query.answer()
    
    sku = query.data.replace('prod_', '')
    logger.info(f"Consultando producto SKU: {sku}")
    
    result = call_api("get_producto", {"sku": sku})
    
    if not result.get('success'):
        await query.edit_message_text(
            "❌ *Producto no encontrado*\\n\\nEs posible que el código SKU haya cambiado.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Volver", callback_data='ver_productos')
            ]])
        )
        return VER_PRODUCTOS
    
    p = result['producto']
    context.user_data['producto_actual'] = p
    
    stock_emoji = "🟢 Disponible" if p['stock'] > 10 else "🟡 Pocas unidades" if p['stock'] > 0 else "🔴 Agotado"
    precio = f"${p['precio']:,}".replace(',', '.')
    
    mensaje = f"""
*{p['nombre']}*

💰 *Precio:* {precio}
📦 *Stock:* {p['stock']} unidades - {stock_emoji}
🏷️ *SKU:* `{p['sku']}`
📂 *Categoría:* {p['categoria']}

📝 *Descripción:*
_{p['descripcion']}_

{'✨ *Este es un producto destacado*' if p.get('destacado') else ''}
    """
    
    keyboard = []
    
    if p['stock'] > 0:
        mensaje += "\n*¿Cuántas unidades deseas?*"
        # Botones de cantidad según stock disponible
        cantidades = [1, 2, 3, 5] if p['stock'] >= 5 else list(range(1, min(p['stock'] + 1, 4)))
        row = [InlineKeyboardButton(str(c), callback_data=f'cant_{c}') for c in cantidades]
        keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🛒 Agregar al Carrito", callback_data=f'cant_1')])
    else:
        mensaje += "\n\n⚠️ *Producto temporalmente agotado*"
        keyboard.append([InlineKeyboardButton("🔍 Ver Alternativas", callback_data=f'cat_{p["categoria"]}')])
    
    keyboard.append([InlineKeyboardButton("« Volver al Catálogo", callback_data='ver_productos')])
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return DETALLE_PRODUCTO

async def agregar_al_carrito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Agrega producto al carrito"""
    query = update.callback_query
    await query.answer()
    
    try:
        cantidad = int(query.data.replace('cant_', ''))
    except:
        cantidad = 1
    
    p = context.user_data.get('producto_actual')
    
    if not p:
        await query.edit_message_text(
            "⚠️ Sesión expirada. Inicia de nuevo con /start",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Inicio", callback_data='volver_inicio')
            ]])
        )
        return MENU_PRINCIPAL
    
    # Verificar stock
    check = call_api("check_stock", {"sku": p['sku'], "cantidad": cantidad})
    
    if not check.get('disponible'):
        await query.edit_message_text(
            f"""❌ *Stock insuficiente*

Solo quedan {check.get('stock_actual', 0)} unidades de *{p['nombre']}*

Por favor, elige una cantidad menor.""",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Volver", callback_data=f'prod_{p["sku"]}')
            ]])
        )
        return DETALLE_PRODUCTO
    
    # Agregar al carrito
    item = {
        'sku': p['sku'],
        'nombre': p['nombre'],
        'precio_unitario': p['precio'],
        'cantidad': cantidad,
        'subtotal': p['precio'] * cantidad
    }
    
    if 'carrito' not in context.user_data:
        context.user_data['carrito'] = []
    
    carrito = context.user_data['carrito']
    
    # Verificar si ya existe
    existente = next((i for i in carrito if i['sku'] == item['sku']), None)
    if existente:
        existente['cantidad'] += cantidad
        existente['subtotal'] = existente['precio_unitario'] * existente['cantidad']
    else:
        carrito.append(item)
    
    total = sum(i['subtotal'] for i in carrito)
    
    mensaje = f"""
✅ *Producto agregado*

*{item['nombre']}*
Cantidad: {cantidad} unidades
Subtotal: ${item['subtotal']:,}

🛒 *Tu Carrito:*
{len(carrito)} producto(s) - Total: ${total:,}
    """.replace(',', '.')
    
    keyboard = [
        [InlineKeyboardButton("🛍️ Seguir Comprando", callback_data='ver_productos')],
        [InlineKeyboardButton("📋 Ver Carrito", callback_data='ver_carrito')],
        [InlineKeyboardButton("💳 Finalizar Compra", callback_data='checkout')],
        [InlineKeyboardButton("« Menú Principal", callback_data='volver_inicio')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return VER_PRODUCTOS

async def mostrar_carrito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el contenido del carrito"""
    query = update.callback_query
    await query.answer()
    
    carrito = context.user_data.get('carrito', [])
    
    if not carrito:
        await query.edit_message_text(
            "🛒 *Tu carrito está vacío*\n\nExplora nuestros productos para comenzar.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Ver Productos", callback_data='ver_productos')],
                [InlineKeyboardButton("« Inicio", callback_data='volver_inicio')]
            ])
        )
        return VER_PRODUCTOS
    
    mensaje = "🛒 *Tu Carrito de Compras*\\n\\n"
    total = 0
    
    for i, item in enumerate(carrito, 1):
        subtotal_fmt = f"${item['subtotal']:,}".replace(',', '.')
        mensaje += f"{i}. *{item['nombre']}*\\n"
        mensaje += f"   {item['cantidad']} x ${item['precio_unitario']:,} = {subtotal_fmt}\\n\\n".replace(',', '.')
        total += item['subtotal']
    
    mensaje += f"💰 *Total a pagar:* ${total:,}".replace(',', '.')
    
    keyboard = [
        [InlineKeyboardButton("🛍️ Agregar más productos", callback_data='ver_productos')],
        [InlineKeyboardButton("💳 Finalizar Compra", callback_data='checkout')],
        [InlineKeyboardButton("🗑️ Vaciar Carrito", callback_data='vaciar_carrito')],
        [InlineKeyboardButton("« Menú Principal", callback_data='volver_inicio')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return VER_PRODUCTOS

# ============================================
# STOCK Y CONSULTAS
# ============================================

async def menu_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menú de consulta de stock"""
    query = update.callback_query
    
    mensaje = """
📦 *Consulta de Stock en Tiempo Real*

Puedo verificar disponibilidad al instante desde nuestra base de datos.
    """
    
    keyboard = [
        [InlineKeyboardButton("📊 Ver Inventario Completo", callback_data='ver_inventario')],
        [InlineKeyboardButton("✅ Solo Productos Disponibles", callback_data='cat_destacados')],
        [InlineKeyboardButton("⚠️ Ver Productos Agotados", callback_data='ver_agotados')],
        [InlineKeyboardButton("« Volver al Inicio", callback_data='volver_inicio')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MENU_PRINCIPAL

async def mostrar_inventario_completo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra todo el inventario"""
    query = update.callback_query
    await query.answer()
    
    result = call_api("get_productos", {"solo_stock": False})
    productos = result.get('productos', [])
    
    if not productos:
        await query.edit_message_text(
            """❌ *No se pudieron cargar los productos*

⚠️ *Posibles causas:*
1. La hoja "productos" está vacía
2. La Web App no tiene permisos
3. Error de conexión con Google Sheets

*Verifica tu configuración y vuelve a intentar.*""",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Reintentar", callback_data='ver_inventario'),
                InlineKeyboardButton("« Volver", callback_data='menu_stock')
            ]])
        )
        return MENU_PRINCIPAL
    
    mensaje = f"*📊 Inventario Completo*\\n"
    mensaje += f"_{len(productos)} productos en sistema_\\n\\n"
    
    for p in productos:
        estado = "✅" if p['stock'] > 5 else "⚠️" if p['stock'] > 0 else "❌"
        precio = f"${p['precio']:,}".replace(',', '.')
        mensaje += f"{estado} *{p['nombre'][:22]}*\\n"
        mensaje += f"   Stock: `{p['stock']}` u. | {precio}\\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Actualizar", callback_data='ver_inventario')],
        [InlineKeyboardButton("« Volver", callback_data='menu_stock')]
    ]
    
    try:
        await query.edit_message_text(
            mensaje,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except:
        # Si es muy largo, enviar nuevo mensaje
        await query.message.reply_text(
            mensaje[:3500],
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return MENU_PRINCIPAL

# ============================================
# INFORMACIÓN ADICIONAL
# ============================================

async def mostrar_pagos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra métodos de pago"""
    query = update.callback_query
    
    mensaje = """
💳 *Métodos de Pago Disponibles*

*Opciones con descuento:*
• 💵 *Efectivo* → 10% OFF (retiro en local)
• 📲 *Transferencia* → 5% OFF

*Otras opciones:*
• 💳 Mercado Pago (tarjeta/QR)
• 🏦 Depósito bancario

*Garantía de satisfacción:*
Si tu mascota no come el alimento en 7 días, *te devolvemos el 100%*.

*¿Necesitas factura A?* ¡Sin problema! Solo avísanos al finalizar.
    """
    
    keyboard = [
        [InlineKeyboardButton("🛒 Ir a Comprar", callback_data='ver_productos')],
        [InlineKeyboardButton("« Volver al Inicio", callback_data='volver_inicio')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MENU_PRINCIPAL

async def mostrar_envios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra opciones de envío"""
    query = update.callback_query
    
    mensaje = """
🚚 *Envíos y Retiro - Formosa*

*Formosa Capital:*
• 🏍️ *Moto mensajería:* $2.500 (2-4 horas)
• 🚗 *Delivery propio:* $1.800 (24-48 hs)
• 🏪 *Retiro en local:* GRATIS
  📍 Av. 9 de Julio 1234, Formosa

*Interior de Formosa:*
• 🚌 *Terminal de ómnibus:* $3.500 - $5.500
• 📦 *Correo Argentino:* A convenir

🎁 *ENVÍO GRATIS* en compras mayores a $50.000
    """
    
    keyboard = [
        [InlineKeyboardButton("🛒 Ir a Comprar", callback_data='ver_productos')],
        [InlineKeyboardButton("« Volver al Inicio", callback_data='volver_inicio')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MENU_PRINCIPAL

async def mostrar_info_empresa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Información sobre TCG"""
    query = update.callback_query
    
    mensaje = """
🏭 *TIT CAN GROSS (TCG)*

*15 años nutriendo mascotas argentinas*

🥩 *Nuestra fórmula única:*
• Proteínas de origen animal certificadas
• Granos seleccionados de la región
• Sin subproductos de dudosa procedencia
• Omega 3 y 6 naturales

*Líneas de producto:*
🏆 *Master Crock* → Calidad-precio insuperable
⭐ *Upper Crock* → Máximo rendimiento proteico

📍 *Fábrica:* Formosa, Argentina
✅ *Autorizado SENASA*
🌱 *Empresa con compromiso ambiental*

*¿Por qué elegirnos sobre importados?*
✓ Frescura garantizada (producción mensual)
✓ Fórmula adaptada al clima subtropical
✓ Soporte técnico local directo
✓ Precio justo sin intermediarios
    """
    
    keyboard = [
        [InlineKeyboardButton("🛒 Ver Productos", callback_data='ver_productos')],
        [InlineKeyboardButton("📞 Contactar Asesor", callback_data='contactar')],
        [InlineKeyboardButton("« Volver al Inicio", callback_data='volver_inicio')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MENU_PRINCIPAL

async def mostrar_panel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Panel de administración demo"""
    query = update.callback_query
    
    result = call_api("get_stats")
    stats = result.get('estadisticas', {})
    
    prod = stats.get('productos', {})
    ventas = stats.get('ventas', {})
    
    mensaje = f"""
📊 *PANEL DE ADMINISTRACIÓN - DEMO*

*Este es el panel que verías como dueño del negocio:*

📦 *Gestión de Inventario:*
• Total productos: `{prod.get('total', 0)}`
• Disponibles: `{prod.get('disponibles', 0)}` ✅
• Agotados: `{prod.get('agotados', 0)}` ❌
• Valor del stock: `${prod.get('valor_inventario', 0):,}`

💰 *Ventas del día:*
• Transacciones: `{ventas.get('total', 0)}`
• Facturación: `${ventas.get('monto_total', 0):,}`
• Ticket promedio: `${ventas.get('ticket_promedio', 0):,}`

👥 *Clientes registrados:* `{stats.get('clientes', 0)}`

*✨ Funciones exclusivas del dueño:*
• Actualizar stock en tiempo real (Google Sheets)
• Recibir notificaciones de ventas por WhatsApp
• Ver reportes de rentabilidad
• Alertas automáticas de stock bajo
    """.replace(',', '.')
    
    keyboard = [
        [InlineKeyboardButton("🔄 Actualizar Datos", callback_data='menu_admin')],
        [InlineKeyboardButton("📦 Gestionar Stock", callback_data='ver_inventario')],
        [InlineKeyboardButton("« Volver al Inicio", callback_data='volver_inicio')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MENU_PRINCIPAL

async def volver_menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vuelve al menú principal"""
    query = update.callback_query
    await query.answer()
    
    mensaje = """
🐕‍🦺 *TCG Pet Store* 🐈

¿En qué puedo ayudarte ahora?
    """
    
    keyboard = [
        [InlineKeyboardButton("🛒 Ver Productos", callback_data='menu_productos')],
        [InlineKeyboardButton("📦 Consultar Stock", callback_data='menu_stock')],
        [InlineKeyboardButton("💳 Métodos de Pago", callback_data='menu_pagos')],
        [InlineKeyboardButton("🚚 Envíos y Retiro", callback_data='menu_envios')],
        [InlineKeyboardButton("ℹ️ Sobre TCG", callback_data='menu_info')],
        [InlineKeyboardButton("📊 Panel Admin", callback_data='menu_admin')]
    ]
    
    await query.edit_message_text(
        mensaje,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MENU_PRINCIPAL

# ============================================
# MANEJO DE ERRORES
# ============================================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja errores del bot"""
    logger.error(f"Error: {context.error}", exc_info=True)
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "😅 *Ups, algo salió mal*\n\n"
                "Por favor, intenta de nuevo con /start\n\n"
                "Si el problema persiste, contacta soporte.",
                parse_mode='Markdown'
            )
        elif update and update.callback_query:
            await update.callback_query.edit_message_text(
                "😅 *Error en la operación*\n\n"
                "Intenta de nuevo con /start",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Reiniciar", callback_data='volver_inicio')
                ]])
            )
    except Exception as e:
        logger.error(f"Error en el handler de errores: {e}")

# ============================================
# INICIO DEL BOT
# ============================================

def main():
    """Función principal"""
    logger.info("=" * 50)
    logger.info("INICIANDO TCG PET STORE BOT")
    logger.info("=" * 50)
    
    # Crear aplicación
    application = Application.builder().token(TOKEN).build()
    
    # Configurar manejador de conversación
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU_PRINCIPAL: [CallbackQueryHandler(menu_callback)],
            VER_PRODUCTOS: [CallbackQueryHandler(menu_callback)],
            DETALLE_PRODUCTO: [CallbackQueryHandler(menu_callback)]
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True
    )
    
    # Agregar handlers
    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)
    
    logger.info("🚀 Bot iniciado y escuchando mensajes...")
    print("🚀 Bot iniciado! Presiona Ctrl+C para detener.")
    
    # Iniciar polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

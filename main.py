from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import database
from config import TOKEN, ADMIN_ID
import requests
import hmac
import hashlib
import time
import json

def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.first_name or "pengguna"
    welcome_message = (
        f"✨ Hai {username}, Selamat datang di Bot Store! ✨\n\n"
        "Berikut adalah menu yang tersedia:"
    )
    keyboard = [
        [InlineKeyboardButton("🛒 Lihat Stok", callback_data='view_products')],
        [InlineKeyboardButton("🛍️ Beli Produk", callback_data='buy_product')],
        [InlineKeyboardButton("🔑 Admin", callback_data='admin')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_message, reply_markup=reply_markup)

def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    products = database.get_products()
    if not products:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Maaf, saat ini tidak ada produk tersedia.')
        return
    
    menu_message = (
        "🛍️ *Daftar Produk yang Tersedia:*\n"
    )
    
    total_stok_tersedia = 0
    total_stok_terjual = 0
    
    for product in products:
        stok_tersedia = product[3]
        stok_awal = product[4]  # Asumsikan stok awal disimpan di kolom ke-5
        stok_terjual = stok_awal - stok_tersedia
        deskripsi = product[5] if product[5] else "Tidak ada deskripsi"
        
        total_stok_tersedia += stok_tersedia
        total_stok_terjual += stok_terjual
        
        menu_message += (
            f"📦 *{product[1]}*\n"
            f"💰 Harga: *Rp {product[2]:,.2f}*\n"
            f"📦 Stok Tersedia: *{stok_tersedia}*\n"
            f"📦 Stok Terjual: *{stok_terjual}*\n"
            f"📝 Deskripsi: *{deskripsi}*\n\n"
        )
    
    menu_message += (
        f"📊 *Total Stok Tersedia:* *{total_stok_tersedia}*\n"
        f"📊 *Total Stok Terjual:* *{total_stok_terjual}*"
    )
    
    keyboard = [
        [InlineKeyboardButton("Kembali", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id, text=menu_message, reply_markup=reply_markup, parse_mode='MarkdownV2')

def view_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    menu(update, context)

def buy_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    products = database.get_products()
    if not products:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Maaf, saat ini tidak ada produk tersedia untuk dibeli.')
        return
    keyboard = []
    for product in products:
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {product[1]} - Rp {product[2]:,.2f} - Stok: {product[3]}",
                callback_data=f'buy_{product[0]}'
            )
        ])
    keyboard.append([InlineKeyboardButton("Kembali", callback_data='main_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Pilih produk yang ingin Anda beli:', reply_markup=reply_markup)

def handle_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    query.answer()
    product_id = int(query.data.split('_')[1])
    products = database.get_products()
    product = next((p for p in products if p[0] == product_id), None)
    if not product:
        query.message.reply_text('Produk tidak ditemukan.')
        return
    query.message.reply_text(f"Anda memilih {product[1]}. Masukkan jumlah yang ingin dibeli:")
    context.user_data['product_id'] = product_id

def handle_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        quantity = int(update.message.text)
        product_id = context.user_data['product_id']
        if database.buy_product(update.message.chat_id, product_id, quantity):
            context.bot.send_message(chat_id=update.message.chat_id, text=f"Berhasil membeli {quantity} unit produk.")
            # Generate QRIS menggunakan Tripay
            product = database.get_product_by_name(database.get_product_name_by_id(product_id))
            if product:
                total_price = product[2] * quantity
                response = generate_qris(total_price, product[1], quantity, update.message.chat_id)
                if response.get('success'):
                    qris_url = response['data']['qris_url']
                    qris_message = (
                        f"🛍️ *Berhasil membeli {quantity} unit produk {product[1]}.*\n"
                        f"💰 *Total Harga:* *Rp {total_price:,.2f}*\n\n"
                        f"Silakan lakukan pembayaran melalui QRIS di bawah ini:\n"
                    )
                    context.bot.send_photo(chat_id=update.message.chat_id, photo=qris_url, caption=qris_message, parse_mode='MarkdownV2')
                else:
                    context.bot.send_message(chat_id=update.message.chat_id, text="Gagal menghasilkan QRIS. Silakan coba lagi nanti.")
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text="Stok tidak mencukupi.")
    except ValueError:
        context.bot.send_message(chat_id=update.message.chat_id, text="Masukkan jumlah yang valid.")
    context.user_data.pop('product_id', None)

def generate_qris(amount, product_name, quantity, chat_id):
    import requests
    import hmac
    import hashlib
    import time
    import json
    from config import TRIPAY_API_KEY, TRIPAY_PRIVATE_KEY, CALLBACK_URL, RETURN_URL

    url = "https://tripay.co.id/api/transaction/create"
    merchant_ref = f"INV-{product_name}-{quantity}-{int(time.time())}"
    payload = {
        "method": "QRIS",
        "merchant_ref": merchant_ref,
        "amount": amount,
        "customer_name": update.message.from_user.first_name,
        "customer_email": "",
        "customer_phone": "",
        "order_items": [
            {
                "sku": product_name,
                "name": product_name,
                "price": amount,
                "quantity": 1
            }
        ],
        "callback_url": CALLBACK_URL,
        "return_url": RETURN_URL,
        "expired_time": 3600,  # Waktu expired dalam detik (1 jam)
        "signature": generate_signature({
            "method": "QRIS",
            "merchant_ref": merchant_ref,
            "amount": amount,
            "private_key": TRIPAY_PRIVATE_KEY
        })
    }

    headers = {
        "Authorization": f"Bearer {TRIPAY_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.get('success'):
        transaction_id = response['data']['reference']
        database.add_transaction(transaction_id, product_name, quantity, chat_id, merchant_ref)
    return response.json()

def generate_signature(data):
    data_sorted = sorted(data.items())
    string_to_sign = '&'.join([f"{key}={value}" for key, value in data_sorted])
    signature = hmac.new(TRIPAY_PRIVATE_KEY.encode(), string_to_sign.encode(), hashlib.sha256).hexdigest()
    return signature

def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        update.callback_query.message.reply_text('Anda tidak memiliki izin untuk mengakses menu admin.')
        return
    keyboard = [
        [InlineKeyboardButton("Tambah Produk", callback_data='add_product')],
        [InlineKeyboardButton("Ubah Stok", callback_data='update_stock')],
        [InlineKeyboardButton("Ubah Harga", callback_data='update_price')],
        [InlineKeyboardButton("Ubah Deskripsi", callback_data='update_description')],
        [InlineKeyboardButton("Hapus Produk", callback_data='delete_product')],
        [InlineKeyboardButton("Kembali", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text('Menu Admin:', reply_markup=reply_markup)

def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        update.callback_query.message.reply_text('Anda tidak memiliki izin untuk menambah produk.')
        return
    update.callback_query.message.reply_text('Masukkan nama produk:')
    return 'NAME'

def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    context.user_data['name'] = update.message.text
    context.bot.send_message(chat_id=update.effective_chat.id, text='Masukkan harga produk:')
    return 'PRICE'

def handle_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    try:
        context.user_data['price'] = float(update.message.text)
        context.bot.send_message(chat_id=update.effective_chat.id, text='Masukkan deskripsi produk:')
        return 'DESCRIPTION'
    except ValueError:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Masukkan harga yang valid.')
        return 'PRICE'

def handle_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    context.user_data['description'] = update.message.text
    context.bot.send_message(chat_id=update.effective_chat.id, text='Masukkan detail produk (contoh: Mail:mail1@domain.com,Pass:password1,V2l:kode1\nMail:mail2@domain.com,Pass:password2,V2l:kode2):')
    return 'DETAILS'

def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['details'] = update.message.text
    details_list = [dict(item.split(':') for item in detail.split(',')) for detail in context.user_data['details'].split('\n')]
    stock = len(details_list)
    database.add_product(context.user_data['name'], context.user_data['price'], stock, context.user_data['description'], context.user_data['details'])
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"Produk {context.user_data['name']} berhasil ditambahkan dengan harga Rp {context.user_data['price']:,.2f}, stok {stock}, dan detail:\n{context.user_data['details']}")
    context.user_data.clear()

def update_stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        update.callback_query.message.reply_text('Anda tidak memiliki izin untuk mengubah stok.')
        return
    products = database.get_products()
    if not products:
        update.callback_query.message.reply_text('Maaf, saat ini tidak ada produk tersedia untuk diubah stoknya.')
        return
    keyboard = []
    for product in products:
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {product[1]} - Stok: {product[3]}",
                callback_data=f'stock_{product[0]}'
            )
        ])
    keyboard.append([InlineKeyboardButton("Kembali", callback_data='admin')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text('Pilih produk yang ingin Anda ubah stoknya:', reply_markup=reply_markup)

def handle_update_stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    product_id = int(query.data.split('_')[1])
    products = database.get_products()
    product = next((p for p in products if p[0] == product_id), None)
    if not product:
        query.message.reply_text('Produk tidak ditemukan.')
        return
    query.message.reply_text(f"Anda memilih {product[1]}. Masukkan stok baru:")
    context.user_data['product_id'] = product_id

def handle_new_stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        new_stock = int(update.message.text)
        product_id = context.user_data['product_id']
        database.update_stock(product_id, new_stock)
        context.bot.send_message(chat_id=update.message.chat_id, text=f"Stok produk dengan kode {product_id} berhasil diubah menjadi {new_stock}.")
        context.user_data.pop('product_id', None)
    except ValueError:
        context.bot.send_message(chat_id=update.message.chat_id, text='Masukkan stok yang valid.')

def update_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        update.callback_query.message.reply_text('Anda tidak memiliki izin untuk mengubah harga.')
        return
    products = database.get_products()
    if not products:
        update.callback_query.message.reply_text('Maaf, saat ini tidak ada produk tersedia untuk diubah harganya.')
        return
    keyboard = []
    for product in products:
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {product[1]} - Harga: Rp {product[2]:,.2f}",
                callback_data=f'price_{product[0]}'
            )
        ])
    keyboard.append([InlineKeyboardButton("Kembali", callback_data='admin')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text('Pilih produk yang ingin Anda ubah harganya:', reply_markup=reply_markup)

def handle_update_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    product_id = int(query.data.split('_')[1])
    products = database.get_products()
    product = next((p for p in products if p[0] == product_id), None)
    if not product:
        query.message.reply_text('Produk tidak ditemukan.')
        return
    query.message.reply_text(f"Anda memilih {product[1]}. Masukkan harga baru:")
    context.user_data['product_id'] = product_id

def handle_new_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        new_price = float(update.message.text)
        product_id = context.user_data['product_id']
        database.update_price(product_id, new_price)
        context.bot.send_message(chat_id=update.message.chat_id, text=f"Harga produk dengan kode {product_id} berhasil diubah menjadi Rp {new_price:,.2f}.")
        context.user_data.pop('product_id', None)
    except ValueError:
        context.bot.send_message(chat_id=update.message.chat_id, text='Masukkan harga yang valid.')

def update_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        update.callback_query.message.reply_text('Anda tidak memiliki izin untuk mengubah deskripsi.')
        return
    products = database.get_products()
    if not products:
        update.callback_query.message.reply_text('Maaf, saat ini tidak ada produk tersedia untuk diubah deskripsinya.')
        return
    keyboard = []
    for product in products:
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {product[1]} - Deskripsi: {product[5]}",
                callback_data=f'description_{product[0]}'
            )
        ])
    keyboard.append([InlineKeyboardButton("Kembali", callback_data='admin')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text('Pilih produk yang ingin Anda ubah deskripsinya:', reply_markup=reply_markup)

def handle_update_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    product_id = int(query.data.split('_')[1])
    products = database.get_products()
    product = next((p for p in products if p[0] == product_id), None)
    if not product:
        query.message.reply_text('Produk tidak ditemukan.')
        return
    query.message.reply_text(f"Anda memilih {product[1]}. Masukkan deskripsi baru:")
    context.user_data['product_id'] = product_id

def handle_new_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    new_description = update.message.text
    product_id = context.user_data['product_id']
    database.update_description(product_id, new_description)
    context.bot.send_message(chat_id=update.message.chat_id, text=f"Deskripsi produk dengan kode {product_id} berhasil diubah menjadi:\n{new_description}")
    context.user_data.pop('product_id', None)

def delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        update.callback_query.message.reply_text('Anda tidak memiliki izin untuk menghapus produk.')
        return
    products = database.get_products()
    if not products:
        update.callback_query.message.reply_text('Maaf, saat ini tidak ada produk tersedia untuk dihapus.')
        return
    keyboard = []
    for product in products:
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {product[1]} - Stok: {product[3]}",
                callback_data=f'delete_{product[0]}'
            )
        ])
    keyboard.append([InlineKeyboardButton("Kembali", callback_data='admin')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text('Pilih produk yang ingin Anda hapus:', reply_markup=reply_markup)

def handle_delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    product_id = int(query.data.split('_')[1])
    database.delete_product(product_id)
    query.message.reply_text(f"Produk dengan kode {product_id} berhasil dihapus.")

def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 2:
        context.bot.send_message(chat_id=update.message.chat_id, text='Format perintah salah. Gunakan: /buy <kode_barang> <jumlah>')
        return

    product_name = context.args[0]
    try:
        quantity = int(context.args[1])
    except ValueError:
        context.bot.send_message(chat_id=update.message.chat_id, text='Jumlah harus berupa angka.')
        return

    success, total_price, details = database.buy_product(update.message.chat_id, product_name, quantity)
    if not success:
        context.bot.send_message(chat_id=update.message.chat_id, text="Stok tidak mencukupi.")
        return

    # Generate QRIS menggunakan Tripay
    response = generate_qris(total_price, product_name, quantity, update.message.chat_id)
    if response.get('success'):
        qris_url = response['data']['qris_url']
        qris_message = (
            f"🛍️ *Berhasil membeli {quantity} unit produk {product_name}.*\n"
            f"💰 *Total Harga:* *Rp {total_price:,.2f}*\n\n"
            f"Silakan lakukan pembayaran melalui QRIS di bawah ini:\n"
        )
        context.bot.send_photo(chat_id=update.message.chat_id, photo=qris_url, caption=qris_message, parse_mode='MarkdownV2')
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text="Gagal menghasilkan QRIS. Silakan coba lagi nanti.")

def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        context.bot.send_message(chat_id=update.message.chat_id, text='Anda tidak memiliki izin untuk mengubah deskripsi produk.')
        return

    if len(context.args) < 2:
        context.bot.send_message(chat_id=update.message.chat_id, text='Format perintah salah. Gunakan: /edit <kode_barang> <deskripsi>')
        return

    product_name = context.args[0]
    new_description = ' '.join(context.args[1:])
    product = database.get_product_by_name(product_name)
    if not product:
        context.bot.send_message(chat_id=update.message.chat_id, text=f"Produk dengan kode {product_name} tidak ditemukan.")
        return

    product_id = product[0]
    database.update_description(product_id, new_description)
    context.bot.send_message(chat_id=update.message.chat_id, text=f"Deskripsi produk dengan kode {product_name} berhasil diubah menjadi:\n{new_description}")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == 'main_menu':
        await start(update, context)
    elif query.data == 'view_products':
        await view_products(update, context)
    elif query.data == 'buy_product':
        await buy_product(update, context)
    elif query.data.startswith('buy_'):
        await handle_buy(update, context)
    elif query.data == 'admin':
        await admin_menu(update, context)
    elif query.data == 'add_product':
        await add_product(update, context)
    elif query.data.startswith('stock_'):
        await handle_update_stock(update, context)
    elif query.data.startswith('price_'):
        await handle_update_price(update, context)
    elif query.data.startswith('description_'):
        await handle_update_description(update, context)
    elif query.data.startswith('delete_'):
        await handle_delete_product(update, context)

def main() -> None:
    database.init_db()
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("edit", edit_command))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quantity))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name), group=1)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price), group=2)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_description), group=3)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_details), group=4)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_stock), group=5)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_price), group=6)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_description), group=7)

    application.run_polling()

if __name__ == '__main__':
    main()
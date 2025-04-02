from flask import Flask, request, jsonify
import database
from config import TOKEN
import telegram

app = Flask(__name__)

bot = telegram.Bot(token=TOKEN)

@app.route('/tripay/callback', methods=['POST'])
def tripay_callback():
    data = request.json
    if data.get('status') == 'PAID':
        merchant_ref = data.get('merchant_ref')
        transaction_status = data.get('transaction_status')
        amount = data.get('amount')
        customer_name = data.get('customer_name')
        product_details = data.get('order_items', [{}])[0]
        product_name = product_details.get('name')
        quantity = product_details.get('quantity', 1)

        # Cari produk berdasarkan nama produk
        product = database.get_product_by_name(product_name)
        if not product:
            return jsonify({"status": "error", "message": "Produk tidak ditemukan"}), 404

        product_id, _, _, _, description, details = product
        details_list = json.loads(details)

        # Cari transaksi berdasarkan merchant_ref
        transaction = database.get_transaction_by_merchant_ref(merchant_ref)
        if not transaction:
            return jsonify({"status": "error", "message": "Transaksi tidak ditemukan"}), 404

        chat_id = transaction[3]
        if chat_id:
            detail_texts = [f"*Detail Akun {i+1}:*\n" + "\n".join([f"*{key.strip()}:* {value.strip()}" for key, value in details.items()]) for i, details in enumerate(details_list[:quantity])]
            message = (
                f"🎉 *Pembayaran Berhasil!* 🎉\n"
                f"📦 *Produk:* {product_name}\n"
                f"💰 *Total Harga:* *Rp {amount:,.2f}*\n"
                f"📦 *Jumlah:* {quantity}\n\n"
                f"*Deskripsi Produk:*\n{description}\n\n" +
                "\n\n".join(detail_texts)
            )
            bot.send_message(chat_id=chat_id, text=message, parse_mode='MarkdownV2')
        else:
            return jsonify({"status": "error", "message": "Chat ID tidak ditemukan"}), 404

    return jsonify({"status": "success", "message": "Webhook received"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
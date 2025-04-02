import sqlite3
import json

def init_db():
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    price REAL NOT NULL,
                    stock INTEGER NOT NULL,
                    initial_stock INTEGER NOT NULL,
                    description TEXT,
                    details TEXT)''')  # Menambahkan kolom description dan details
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    merchant_ref TEXT NOT NULL,
                    FOREIGN KEY (product_id) REFERENCES products (id))''')  # Menambahkan tabel transactions
    conn.commit()
    conn.close()

def add_product(name, price, stock, description, details):
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute("INSERT INTO products (name, price, stock, initial_stock, description, details) VALUES (?, ?, ?, ?, ?, ?)", 
              (name, price, stock, stock, description, json.dumps(details)))
    conn.commit()
    conn.close()

def get_products():
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    conn.close()
    return products

def get_product_by_name(name):
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE name = ?", (name,))
    product = c.fetchone()
    conn.close()
    return product

def get_product_name_by_id(product_id):
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute("SELECT name FROM products WHERE id = ?", (product_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def update_stock(product_id, new_stock):
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, product_id))
    conn.commit()
    conn.close()

def update_price(product_id, new_price):
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute("UPDATE products SET price = ? WHERE id = ?", (new_price, product_id))
    conn.commit()
    conn.close()

def update_description(product_id, new_description):
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute("UPDATE products SET description = ? WHERE id = ?", (new_description, product_id))
    conn.commit()
    conn.close()

def delete_product(product_id):
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

def buy_product(user_id, product_name, quantity):
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute("SELECT id, stock, price, initial_stock, description, details FROM products WHERE name = ?", (product_name,))
    result = c.fetchone()
    if not result:
        conn.close()
        return False, None, None, None

    product_id, stock, price, initial_stock, description, details = result
    total_price = price * quantity
    if stock >= quantity:
        c.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))
        conn.commit()
        conn.close()
        return True, total_price, description, json.loads(details)
    else:
        conn.close()
        return False, None, None, None

def add_transaction(transaction_id, product_name, quantity, chat_id, merchant_ref):
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute("INSERT INTO transactions (product_id, quantity, chat_id, merchant_ref) VALUES ((SELECT id FROM products WHERE name = ?), ?, ?, ?)", 
              (product_name, quantity, chat_id, merchant_ref))
    conn.commit()
    conn.close()

def get_transaction_by_merchant_ref(merchant_ref):
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE merchant_ref = ?", (merchant_ref,))
    transaction = c.fetchone()
    conn.close()
    return transaction
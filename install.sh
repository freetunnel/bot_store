#!/bin/bash

# Fungsi untuk mengecek apakah perintah tersedia
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Memeriksa apakah Python 3 terpasang
if ! command_exists python3; then
    echo "Python 3 tidak terpasang. Menginstal Python 3..."
    sudo apt-get update
    sudo apt-get install -y python3
fi

# Memeriksa apakah pip3 terpasang
if ! command_exists pip3; then
    echo "pip3 tidak terpasang. Menginstal pip3..."
    sudo apt-get install -y python3-pip
fi

# Memeriksa apakah git terpasang
if ! command_exists git; then
    echo "git tidak terpasang. Menginstal git..."
    sudo apt-get install -y git
fi

# Memeriksa apakah Flask terpasang
if ! command_exists flask; then
    echo "Flask tidak terpasang. Menginstal Flask..."
    pip3 install flask
fi

# Membuat direktori proyek
PROJECT_DIR="/usr/local/bin/bot_store"
mkdir -p "$PROJECT_DIR"

# Mengunduh proyek dari GitHub
echo "Mengunduh proyek dari GitHub..."
git clone https://github.com/username/bot_store.git "$PROJECT_DIR"

# Menginstall dependensi
echo "Menginstall dependensi..."
pip3 install -r "$PROJECT_DIR/requirements.txt"

# Meminta input detail konfigurasi
echo "Masukkan token bot Telegram:"
read TOKEN
echo "Masukkan ID admin:"
read ADMIN_ID
echo "Masukkan API Key Tripay:"
read TRIPAY_API_KEY
echo "Masukkan Merchant Code Tripay:"
read TRIPAY_MERCHANT_CODE
echo "Masukkan Private Key Tripay:"
read TRIPAY_PRIVATE_KEY
echo "Masukkan URL Callback Tripay (misalnya: https://your-domain.com/tripay/callback):"
read CALLBACK_URL
echo "Masukkan URL Return Tripay (misalnya: https://your-domain.com):"
read RETURN_URL

# Menulis konfigurasi ke file config.py
CONFIG_FILE="$PROJECT_DIR/config.py"
echo "TOKEN = '$TOKEN'" > "$CONFIG_FILE"
echo "ADMIN_ID = $ADMIN_ID" >> "$CONFIG_FILE"
echo "TRIPAY_API_KEY = '$TRIPAY_API_KEY'" >> "$CONFIG_FILE"
echo "TRIPAY_MERCHANT_CODE = '$TRIPAY_MERCHANT_CODE'" >> "$CONFIG_FILE"
echo "TRIPAY_PRIVATE_KEY = '$TRIPAY_PRIVATE_KEY'" >> "$CONFIG_FILE"
echo "CALLBACK_URL = '$CALLBACK_URL'" >> "$CONFIG_FILE"
echo "RETURN_URL = '$RETURN_URL'" >> "$CONFIG_FILE"

# Memberikan izin eksekusi pada file main.py dan webhook.py
chmod +x "$PROJECT_DIR/main.py"
chmod +x "$PROJECT_DIR/webhook.py"

# Membuat unit service systemd untuk bot
SERVICE_FILE="/etc/systemd/system/bot_store.service"
echo "[Unit]" > "$SERVICE_FILE"
echo "Description=Toko Online Bot" >> "$SERVICE_FILE"
echo "After=network.target" >> "$SERVICE_FILE"
echo "" >> "$SERVICE_FILE"
echo "[Service]" >> "$SERVICE_FILE"
echo "User=$(whoami)" >> "$SERVICE_FILE"
echo "WorkingDirectory=$PROJECT_DIR" >> "$SERVICE_FILE"
echo "ExecStart=/usr/bin/python3 $PROJECT_DIR/main.py" >> "$SERVICE_FILE"
echo "Restart=always" >> "$SERVICE_FILE"
echo "RestartSec=5" >> "$SERVICE_FILE"
echo "" >> "$SERVICE_FILE"
echo "[Install]" >> "$SERVICE_FILE"
echo "WantedBy=multi-user.target" >> "$SERVICE_FILE"

# Membuat unit service systemd untuk webhook
WEBHOOK_SERVICE_FILE="/etc/systemd/system/bot_store_webhook.service"
echo "[Unit]" > "$WEBHOOK_SERVICE_FILE"
echo "Description=Toko Online Webhook" >> "$WEBHOOK_SERVICE_FILE"
echo "After=network.target" >> "$WEBHOOK_SERVICE_FILE"
echo "" >> "$WEBHOOK_SERVICE_FILE"
echo "[Service]" >> "$WEBHOOK_SERVICE_FILE"
echo "User=$(whoami)" >> "$WEBHOOK_SERVICE_FILE"
echo "WorkingDirectory=$PROJECT_DIR" >> "$WEBHOOK_SERVICE_FILE"
echo "ExecStart=/usr/bin/python3 $PROJECT_DIR/webhook.py" >> "$WEBHOOK_SERVICE_FILE"
echo "Restart=always" >> "$WEBHOOK_SERVICE_FILE"
echo "RestartSec=5" >> "$WEBHOOK_SERVICE_FILE"
echo "" >> "$WEBHOOK_SERVICE_FILE"
echo "[Install]" >> "$WEBHOOK_SERVICE_FILE"
echo "WantedBy=multi-user.target" >> "$WEBHOOK_SERVICE_FILE"

# Memuat ulang systemd dan menjalankan layanan
echo "Memuat ulang systemd..."
sudo systemctl daemon-reload

echo "Menjalankan layanan bot_store..."
sudo systemctl start bot_store

echo "Menyetel layanan bot_store untuk dimulai pada boot..."
sudo systemctl enable bot_store

echo "Menjalankan layanan bot_store_webhook..."
sudo systemctl start bot_store_webhook

echo "Menyetel layanan bot_store_webhook untuk dimulai pada boot..."
sudo systemctl enable bot_store_webhook

echo "Layanan bot_store dan bot_store_webhook berhasil diinstal dan dijalankan."
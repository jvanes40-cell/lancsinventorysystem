import sqlite3

def create_database():
    # 1. Bikin koneksi ke file database (kalau belum ada, otomatis dibuat)
    conn = sqlite3.connect('gudang.db')
    cursor = conn.cursor()

    # 2. Bikin Tabel PRODUCTS (Master Barang)
    # Isinya: ID unik, Nama Barang, Kategori, Stok Sekarang
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT,
        stock INTEGER DEFAULT 0,
        price INTEGER DEFAULT 0
    )
    ''')

    # 3. Bikin Tabel TRANSACTIONS (Riwayat Keluar Masuk)
    # Isinya: ID, ID Barang, Jenis (MASUK/KELUAR), Jumlah, Tanggal
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        type TEXT NOT NULL, 
        quantity INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products (id)
    )
    ''')

    print("Database berhasil dibuat! Cek file 'gudang.db' di folder lo.")
    
    # 4. Simpan dan Tutup
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_database()
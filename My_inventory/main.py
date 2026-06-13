import sqlite3
import datetime

def get_connection():
    return sqlite3.connect('gudang.db')

# --- FUNGSI 1: TAMBAH BARANG BARU (Sama kayak tadi) ---
def tambah_barang():
    print("\n--- TAMBAH BARANG BARU ---")
    nama = input("Nama Barang: ")
    kategori = input("Kategori: ")
    try:
        stok = int(input("Stok Awal: "))
        harga = int(input("Harga Satuan: "))
    except ValueError:
        print("Input angka dong, Bro!")
        return

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO products (name, category, stock, price) VALUES (?, ?, ?, ?)', 
                   (nama, kategori, stok, harga))
    conn.commit()
    conn.close()
    print(f"[SUKSES] {nama} berhasil disimpan!")

# --- FUNGSI 2: LIHAT SEMUA BARANG (Sama kayak tadi) ---
def lihat_barang():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products')
    barangs = cursor.fetchall()
    conn.close()

    print("\n" + "="*60)
    print(f"{'ID':<5} {'Nama':<20} {'Kategori':<15} {'Stok':<10} {'Harga':<15}")
    print("-" * 60)

    if not barangs:
        print("Gudang kosong melompong.")
    else:
        for b in barangs:
            print(f"{b[0]:<5} {b[1]:<20} {b[2]:<15} {b[3]:<10} Rp{b[4]:,}")
    print("="*60 + "\n")

# --- FUNGSI 3: TRANSAKSI (BARU NIH!) ---
def transaksi_stok(jenis):
    # jenis bisa 'MASUK' atau 'KELUAR'
    lihat_barang() # Tunjukin dulu list barangnya biar tau ID-nya
    
    try:
        id_barang = int(input(f"Masukkan ID Barang yang mau di-{jenis}: "))
        jumlah = int(input(f"Jumlah barang {jenis}: "))
    except ValueError:
        print("ID atau Jumlah harus angka!")
        return

    conn = get_connection()
    cursor = conn.cursor()

    # 1. Cek dulu barangnya ada nggak?
    cursor.execute('SELECT stock, name FROM products WHERE id = ?', (id_barang,))
    data = cursor.fetchone()

    if data is None:
        print("Barang nggak ditemukan! Cek ID lagi.")
        conn.close()
        return

    stok_sekarang = data[0]
    nama_barang = data[1]

    # 2. Logika Hitung Stok
    stok_baru = 0
    if jenis == 'MASUK':
        stok_baru = stok_sekarang + jumlah
    elif jenis == 'KELUAR':
        if stok_sekarang < jumlah:
            print(f"[GAGAL] Stok nggak cukup! Sisa cuma {stok_sekarang}.")
            conn.close()
            return
        stok_baru = stok_sekarang - jumlah

    # 3. Update Database (Update Stok & Catat Riwayat)
    try:
        # A. Update jumlah stok di tabel products
        cursor.execute('UPDATE products SET stock = ? WHERE id = ?', (stok_baru, id_barang))
        
        # B. Catat di tabel transactions (Audit Trail)
        cursor.execute('INSERT INTO transactions (product_id, type, quantity, created_at) VALUES (?, ?, ?, ?)', 
                       (id_barang, jenis, jumlah, datetime.datetime.now()))
        
        conn.commit()
        print(f"\n[SUKSES] Stok {nama_barang} berhasil diupdate jadi {stok_baru}.")
        
    except Exception as e:
        print(f"Ada Error: {e}")
        conn.rollback() # Batalin semua kalau ada error
    
    finally:
        conn.close()

# --- MENU UTAMA ---
def main_menu():
    while True:
        print("\n=== SISTEM GUDANG V2 ===")
        print("1. Tambah Barang Baru (Master Data)")
        print("2. Cek Stok Gudang")
        print("3. Barang MASUK (+ Stok)")
        print("4. Barang KELUAR (- Stok)")
        print("5. Keluar Program")
        
        pilihan = input("Pilih menu (1-5): ")

        if pilihan == '1':
            tambah_barang()
        elif pilihan == '2':
            lihat_barang()
        elif pilihan == '3':
            transaksi_stok('MASUK')
        elif pilihan == '4':
            transaksi_stok('KELUAR')
        elif pilihan == '5':
            print("Cabut dulu, Bro!")
            break
        else:
            print("Pilihan salah.")

if __name__ == "__main__":
    main_menu()
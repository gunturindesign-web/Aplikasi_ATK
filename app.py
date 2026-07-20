import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# =====================================================================
# ⚠️ MASUKKAN LINK GOOGLE SHEETS & URL APPS SCRIPT KAMU DI SINI!
# =====================================================================
URL_SPREADSHEET = "https://docs.google.com/spreadsheets/d/19Qv2SMhD4Ua5NBAI2DDzC46NT6rcaTcJSJ1Hb8ARiAU/edit?usp=sharing"

URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbzcCff5UkIivpDpelQxf4kyPEyQSX2uD0id715xhklL-i2vt7qZJ5ZD7I2TlHBUrpIz/exec"

# Fungsi membaca data live dari Google Sheets
def dapatkan_url_sheet(url, nama_sheet):
    base_url = url.split('/edit')[0]
    return f"{base_url}/gviz/tq?tqx=out:csv&sheet={nama_sheet}"

try:
    df_master = pd.read_csv(dapatkan_url_sheet(URL_SPREADSHEET, "Master"))
    df_masuk = pd.read_csv(dapatkan_url_sheet(URL_SPREADSHEET, "Masuk"))
    df_keluar = pd.read_csv(dapatkan_url_sheet(URL_SPREADSHEET, "Keluar"))
    
    df_master.columns = df_master.columns.str.strip().str.title()
    df_masuk.columns = df_masuk.columns.str.strip().str.title()
    df_keluar.columns = df_keluar.columns.str.strip().str.title()
except Exception as e:
    st.error("❌ Gagal membaca Google Sheets. Pastikan URL dan Apps Script sudah benar!")
    st.stop()

# Menangani format tipe data dasar
if not df_master.empty and "Kode Barang" in df_master.columns:
    df_master["Kode Barang"] = df_master["Kode Barang"].astype(str).str.strip().str.upper()
if not df_masuk.empty and "Kode Barang" in df_masuk.columns:
    df_masuk["Kode Barang"] = df_masuk["Kode Barang"].astype(str).str.strip().str.upper()
if not df_keluar.empty and "Kode Barang" in df_keluar.columns:
    df_keluar["Kode Barang"] = df_keluar["Kode Barang"].astype(str).str.strip().str.upper()

# Ensure kolom Tahun tersedia di DataFrame
tahun_ini = datetime.now().year
for df in [df_master, df_masuk, df_keluar]:
    if not df.empty and "Tahun" in df.columns:
        df["Tahun"] = pd.to_numeric(df["Tahun"], errors='coerce').fillna(tahun_ini).astype(int)

# --- INSTANSIASI SESSION STATE ---
if "keranjang_masuk" not in st.session_state:
    st.session_state.keranjang_masuk = []
if "keranjang_keluar" not in st.session_state:
    st.session_state.keranjang_keluar = []

# --- TAMPILAN UTAMA STREAMLIT ---
st.set_page_config(page_title="Sistem Informasi ATK Set Bappebti", layout="wide")
st.title("📦 Sistem Pencatatan & Mutasi ATK Set Bappebti")
st.markdown("---")

# GENERATE LIST TAHUN DINAMIS (TAHUN INI + 15 TAHUN KE DEPAN)
tahun_sekarang = datetime.now().year
list_tahun_dinamis = list(range(2026, tahun_sekarang + 15))

if not df_master.empty and "Tahun" in df_master.columns:
    tahun_db = df_master["Tahun"].unique().tolist()
    list_tahun_dinamis = sorted(list(set(list_tahun_dinamis + tahun_db)))

st.sidebar.markdown("### 🗓️ TAHUN BUKU")
# Default pilihan otomatis mengarah ke tahun saat ini jika ada di daftar
idx_default = list_tahun_dinamis.index(2026) if 2026 in list_tahun_dinamis else 0
tahun_aktif = st.sidebar.selectbox("Pilih Tahun Aktif / Review:", list_tahun_dinamis, index=idx_default)

menu = st.sidebar.selectbox(
    "PILIH MENU:", 
    [
        "📊 Dashboard & Mutasi", 
        "➕ Input Barang Baru", 
        "📥 Catat Barang Masuk", 
        "📤 Catat Barang Keluar",
        "✏️ Kelola & Riwayat Data",
        "⚙️ Pengaturan & Tutup Buku"
    ]
)

# FILTER DATA SESUAI TAHUN AKTIF SELEKSI
df_master_th = df_master[df_master["Tahun"] == tahun_aktif] if (not df_master.empty and "Tahun" in df_master.columns) else pd.DataFrame()
df_masuk_th = df_masuk[df_masuk["Tahun"] == tahun_aktif] if (not df_masuk.empty and "Tahun" in df_masuk.columns) else pd.DataFrame()
df_keluar_th = df_keluar[df_keluar["Tahun"] == tahun_aktif] if (not df_keluar.empty and "Tahun" in df_keluar.columns) else pd.DataFrame()

def hitung_stok_sekarang(kode_barang):
    stok_awal = df_master_th[df_master_th["Kode Barang"] == kode_barang]["Stok Awal"].sum() if not df_master_th.empty else 0
    total_masuk = df_masuk_th[df_masuk_th["Kode Barang"] == kode_barang]["Jumlah Masuk"].sum() if (not df_masuk_th.empty and "Jumlah Masuk" in df_masuk_th.columns) else 0
    total_keluar = df_keluar_th[df_keluar_th["Kode Barang"] == kode_barang]["Jumlah Keluar"].sum() if (not df_keluar_th.empty and "Jumlah Keluar" in df_keluar_th.columns) else 0
    return int(stok_awal + total_masuk - total_keluar)


# ==========================================
# 1. MENU: DASHBOARD & MUTASI
# ==========================================
if menu == "📊 Dashboard & Mutasi":
    st.subheader(f"Laporan Mutasi & Status Stok ATK (Tahun Buku {tahun_aktif})")
    
    if df_master_th.empty:
        st.info(f"Belum ada Master Barang terdaftar untuk Tahun Buku {tahun_aktif}.")
    else:
        tipe_laporan = st.radio("Pilih Mode Tampilan Laporan:", ["📋 Ringkasan Semua Stok", "🔍 Lacak Histori Rinci Per Barang"], horizontal=True)
        st.markdown("---")
        
        if tipe_laporan == "📋 Ringkasan Semua Stok":
            total_masuk = df_masuk_th.groupby("Kode Barang")["Jumlah Masuk"].sum().reset_index() if (not df_masuk_th.empty and "Jumlah Masuk" in df_masuk_th.columns) else pd.DataFrame(columns=["Kode Barang", "Jumlah Masuk"])
            total_keluar = df_keluar_th.groupby("Kode Barang")["Jumlah Keluar"].sum().reset_index() if (not df_keluar_th.empty and "Jumlah Keluar" in df_keluar_th.columns) else pd.DataFrame(columns=["Kode Barang", "Jumlah Keluar"])
            
            df_mutasi = df_master_th[["Kode Barang", "Nama Barang", "Stok Awal"]].merge(total_masuk, on="Kode Barang", how="left").fillna(0)
            df_mutasi = df_mutasi.merge(total_keluar, on="Kode Barang", how="left").fillna(0)
            
            df_mutasi["Stok Akhir"] = df_mutasi["Stok Awal"] + df_mutasi["Jumlah Masuk"] - df_mutasi["Jumlah Keluar"]
            df_mutasi["Status"] = df_mutasi["Stok Akhir"].apply(lambda x: "🟢 MASIH" if x > 0 else "🔴 HABIS")
            
            for col in ["Stok Awal", "Jumlah Masuk", "Jumlah Keluar", "Stok Akhir"]:
                if col in df_mutasi.columns:
                    df_mutasi[col] = df_mutasi[col].astype(int)
                
            st.dataframe(df_mutasi, use_container_width=True)
            
        else:
            st.markdown("### 🔎 Kartu Kendali & Histori Barang")
            pilihan_lacak = st.selectbox("Pilih ATK yang ingin Anda lacak historinya:", df_master_th["Kode Barang"] + " - " + df_master_th["Nama Barang"])
            kode_lacak = pilihan_lacak.split(" - ")[0].strip().upper()
            nama_lacak = pilihan_lacak.split(" - ")[1]
            
            stok_saat_ini = hitung_stok_sekarang(kode_lacak)
            st.metric(label=f"Sisa Stok Aktual '{nama_lacak}' (Tahun {tahun_aktif})", value=f"{stok_saat_ini} unit")
            
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                st.markdown("#### 📥 Riwayat Barang Masuk (Restock)")
                df_masuk_item = df_masuk_th[df_masuk_th["Kode Barang"] == kode_lacak] if (not df_masuk_th.empty and "Kode Barang" in df_masuk_th.columns) else pd.DataFrame()
                if df_masuk_item.empty:
                    st.info("Belum ada riwayat barang masuk untuk item ini di tahun aktif.")
                else:
                    st.dataframe(df_masuk_item[[c for c in ["Tanggal", "Jumlah Masuk"] if c in df_masuk_item.columns]], use_container_width=True)
                    
            with col_h2:
                st.markdown("#### 📤 Riwayat Pengambilan (Barang Keluar)")
                df_keluar_item = df_keluar_th[df_keluar_th["Kode Barang"] == kode_lacak] if (not df_keluar_th.empty and "Kode Barang" in df_keluar_th.columns) else pd.DataFrame()
                if df_keluar_item.empty:
                    st.info("Belum ada riwayat pengeluaran untuk item ini di tahun aktif.")
                else:
                    df_keluar_view_item = df_keluar_item.merge(df_master_th[["Kode Barang", "Nama Barang"]], on="Kode Barang", how="left")
                    st.dataframe(df_keluar_view_item[[c for c in ["Tanggal", "Jumlah Keluar", "Keterangan"] if c in df_keluar_view_item.columns]], use_container_width=True)


# ==========================================
# 2. MENU: INPUT BARANG BARU
# ==========================================
elif menu == "➕ Input Barang Baru":
    st.subheader(f"Tambah Master Barang Baru (Tahun Buku {tahun_aktif})")
    
    with st.form("form_barang_baru", clear_on_submit=True):
        kode = st.text_input("Kode Barang (Contoh: ATK-01)").strip().upper()
        nama = st.text_input("Nama Barang (Contoh: Kertas A4)").strip()
        stok_awal = st.number_input("Stok Awal", min_value=0, value=0, step=1)
        submit = st.form_submit_button("Simpan Permanen Ke Google Sheets")
        
        if submit:
            if not df_master_th.empty and kode in df_master_th["Kode Barang"].values:
                st.error(f"⚠️ Kode Barang sudah terdaftar di Master Tahun {tahun_aktif}!")
            elif kode == "" or nama == "":
                st.warning("⚠️ Kode dan Nama Barang tidak boleh kosong.")
            else:
                payload = {
                    "sheet": "Master",
                    "action": "append",
                    "data": [[kode, nama, int(tahun_aktif), int(stok_awal)]]
                }
                res = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload))
                if res.status_code == 200:
                    st.success(f"🎉 Sukses! {nama} berhasil tersimpan langsung di Master Tahun {tahun_aktif}!")
                    st.rerun()
                else:
                    st.error("❌ Gagal menyimpan data via Apps Script.")


# ==========================================
# 3. MENU: CATAT BARANG MASUK (MULTI-ITEM)
# ==========================================
elif menu == "📥 Catat Barang Masuk":
    st.subheader(f"Input Barang Masuk / Restock (Tahun Buku {tahun_aktif})")
    
    if df_master_th.empty:
        st.warning(f"⚠️ Master Barang untuk Tahun {tahun_aktif} masih kosong. Silakan tambah barang baru atau lakukan Tutup Buku terlebih dahulu.")
    else:
        st.markdown("### 📋 Data Nota / Bukti Masuk")
        col_nota1, col_nota2 = st.columns(2)
        with col_nota1:
            tanggal_masuk = st.date_input("Tanggal Masuk")
            no_bukti_masuk = st.text_input("No. Bukti / Nota Masuk (Contoh: BM-001)").strip().upper()
        with col_nota2:
            keterangan_masuk = st.text_input("Keterangan / Supplier / Sumber Barang").strip()

        st.markdown("---")
        col_in, col_tbl = st.columns([1, 2])
        
        with col_in:
            st.markdown("### ➕ Tambah Barang")
            pilihan_barang = st.selectbox("Pilih Barang ", df_master_th["Kode Barang"] + " - " + df_master_th["Nama Barang"])
            kode_barang = pilihan_barang.split(" - ")[0].strip().upper()
            nama_barang = pilihan_barang.split(" - ")[1]
            jumlah_masuk = st.number_input("Jumlah Masuk", min_value=1, step=1)
            
            if st.button("Tambah ke Keranjang 🛒", key="btn_add_masuk", use_container_width=True):
                if no_bukti_masuk == "":
                    st.error("❌ No. Bukti / Nota Masuk wajib diisi!")
                elif keterangan_masuk == "":
                    st.error("❌ Kolom Keterangan / Supplier tidak boleh kosong!")
                else:
                    st.session_state.keranjang_masuk.append({
                        "Tanggal": str(tanggal_masuk),
                        "Kode Barang": kode_barang,
                        "Nama Barang": nama_barang,
                        "Jumlah Masuk": int(jumlah_masuk)
                    })
                    st.success(f"Added: {nama_barang}")
                    st.rerun()
                
        with col_tbl:
            st.markdown(f"### 📋 Daftar Tampung Masuk (Nota: {no_bukti_masuk if no_bukti_masuk else '-'})")
            if st.session_state.keranjang_masuk:
                df_temp_masuk = pd.DataFrame(st.session_state.keranjang_masuk)
                st.dataframe(df_temp_masuk, use_container_width=True)
                
                c_batal, c_simpan = st.columns(2)
                if c_batal.button("🗑️ Kosongkan Daftar", key="clear_masuk", use_container_width=True):
                    st.session_state.keranjang_masuk = []
                    st.rerun()
                    
                if c_simpan.button("💾 SIMPAN LANGSUNG KE GOOGLE SHEETS", type="primary", key="save_masuk", use_container_width=True):
                    data_rows = [[item["Tanggal"], item["Kode Barang"], item["Jumlah Masuk"], int(tahun_aktif)] for item in st.session_state.keranjang_masuk]
                    payload = {"sheet": "Masuk", "action": "append", "data": data_rows}
                    
                    res = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload))
                    if res.status_code == 200:
                        st.session_state.keranjang_masuk = []
                        st.success("🎉 Transaksi Restock Berhasil Disimpan Otomatis!")
                        st.rerun()
                    else:
                        st.error("❌ Gagal mengirim data ke Google Sheets.")
            else:
                st.info("Keranjang masuk kosong.")


# ==========================================
# 4. MENU: CATAT BARANG KELUAR (MULTI-ITEM)
# ==========================================
elif menu == "📤 Catat Barang Keluar":
    st.subheader(f"Input Pengambilan / Barang Keluar (Tahun Buku {tahun_aktif})")
    
    if df_master_th.empty:
        st.warning(f"⚠️ Master Barang untuk Tahun {tahun_aktif} masih kosong.")
    else:
        st.markdown("### 📋 Data Nota / Bukti Keluar")
        col_nota1, col_nota2 = st.columns(2)
        with col_nota1:
            tanggal_keluar = st.date_input("Tanggal Keluar")
            no_bukti = st.text_input("No. Bukti / Nota Keluar (Contoh: BK-001)").strip().upper()
        with col_nota2:
            bagian_pengambil = st.text_input("Keterangan / Bagian yang Mengambil").strip()

        st.markdown("---")
        col_in, col_tbl = st.columns([1, 2])
        
        with col_in:
            st.markdown("### ➕ Tambah Barang")
            pilihan_barang = st.selectbox("Pilih Barang Keluar", df_master_th["Kode Barang"] + " - " + df_master_th["Nama Barang"])
            kode_barang = pilihan_barang.split(" - ")[0].strip().upper()
            nama_barang = pilihan_barang.split(" - ")[1]
            
            stok_gudang = hitung_stok_sekarang(kode_barang)
            stok_terpesan = sum(item['Jumlah Keluar'] for item in st.session_state.keranjang_keluar if item['Kode Barang'] == kode_barang)
            stok_efektif = stok_gudang - stok_terpesan
            
            st.caption(f"Stok Gudang ({tahun_aktif}): **{stok_gudang}** | Batas Aman Diambil: **{stok_efektif}**")
            jumlah_keluar = st.number_input("Jumlah Keluar", min_value=1, step=1)
            
            if st.button("Tambah ke Daftar 🛒", key="btn_add_keluar", use_container_width=True):
                if no_bukti == "":
                    st.error("❌ No. Bukti / Nota Keluar wajib diisi!")
                elif bagian_pengambil == "":
                    st.error("❌ Kolom Keterangan / Bagian tidak boleh kosong!")
                elif jumlah_keluar > stok_efektif:
                    st.error(f"❌ Stok tidak mencukupi! Batas sisa barang: {stok_efektif}")
                else:
                    keterangan_gabungan = f"[{no_bukti}] - {bagian_pengambil}"
                    st.session_state.keranjang_keluar.append({
                        "Tanggal": str(tanggal_keluar),
                        "Kode Barang": kode_barang,
                        "Nama Barang": nama_barang,
                        "Jumlah Keluar": int(jumlah_keluar),
                        "Keterangan": keterangan_gabungan
                    })
                    st.success(f"✔️ {nama_barang} dimasukkan ke daftar sementara.")
                    st.rerun()

        with col_tbl:
            st.markdown(f"### 🛒 Keranjang Sementara (Nota: {no_bukti if no_bukti else '-'})")
            if st.session_state.keranjang_keluar:
                df_temp_keluar = pd.DataFrame(st.session_state.keranjang_keluar)
                st.dataframe(df_temp_keluar, use_container_width=True)
                
                c_batal, c_simpan = st.columns(2)
                if c_batal.button("🗑️ Kosongkan Keranjang", key="clear_keluar", use_container_width=True):
                    st.session_state.keranjang_keluar = []
                    st.rerun()
                    
                if c_simpan.button("💾 SIMPAN BARANG KELUAR PERMANEN", type="primary", key="save_keluar", use_container_width=True):
                    data_rows = [[item["Tanggal"], item["Kode Barang"], item["Jumlah Keluar"], item["Keterangan"], int(tahun_aktif)] for item in st.session_state.keranjang_keluar]
                    payload = {"sheet": "Keluar", "action": "append", "data": data_rows}
                    
                    res = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload))
                    if res.status_code == 200:
                        st.session_state.keranjang_keluar = []
                        st.success("🎉 Sukses! Data barang keluar telah disimpan!")
                        st.rerun()
                    else:
                        st.error("❌ Gagal mengirim transaksi ke Google Sheets.")
            else:
                st.info("Keranjang pengeluaran kosong.")


# ==========================================
# 5. MENU: KELOLA & RIWAYAT DATA
# ==========================================
elif menu == "✏️ Kelola & Riwayat Data":
    st.subheader(f"Kelola Riwayat Transaksi (Tahun Buku {tahun_aktif})")
    
    kategori_data = st.radio("Pilih Data yang Ingin Dikelola:", ["📥 Riwayat Barang Masuk", "📤 Riwayat Barang Keluar"], horizontal=True)
    st.markdown("---")
    
    if kategori_data == "📥 Riwayat Barang Masuk":
        if df_masuk_th.empty:
            st.info(f"Belum ada riwayat barang masuk di Tahun {tahun_aktif}.")
        else:
            st.markdown("### Daftar Transaksi Masuk")
            df_masuk_view = df_masuk_th.merge(df_master_th[["Kode Barang", "Nama Barang"]], on="Kode Barang", how="left")
            st.dataframe(df_masuk_view[["Tanggal", "Kode Barang", "Nama Barang", "Jumlah Masuk"]], use_container_width=True)
            
            st.markdown("#### ⚙️ Aksi Penyesuaian Data")
            indeks_pilihan = st.number_input("Masukkan Nomor Baris yang ingin diproses:", min_value=0, max_value=len(df_masuk_th)-1, step=1, key="idx_masuk")
            item_terpilih = df_masuk_view.iloc[indeks_pilihan]
            st.info(f"Item Terpilih: **{item_terpilih['Nama Barang']}** | Jumlah: **{item_terpilih['Jumlah Masuk']}**")
            
            if st.button("🗑️ HAPUS TRANSAKSI PERMANEN", type="primary", key="btn_del_m"):
                df_masuk_sisa = df_masuk.drop(item_terpilih.name).reset_index(drop=True)
                payload = {"sheet": "Masuk", "action": "overwrite", "headers": ["Tanggal", "Kode Barang", "Jumlah Masuk", "Tahun"], "data": df_masuk_sisa.values.tolist()}
                requests.post(URL_APPS_SCRIPT, data=json.dumps(payload))
                st.success("✔️ Transaksi berhasil dihapus!")
                st.rerun()

    elif kategori_data == "📤 Riwayat Barang Keluar":
        if df_keluar_th.empty:
            st.info(f"Belum ada riwayat barang keluar di Tahun {tahun_aktif}.")
        else:
            st.markdown("### Daftar Transaksi Keluar")
            df_keluar_view = df_keluar_th.merge(df_master_th[["Kode Barang", "Nama Barang"]], on="Kode Barang", how="left")
            st.dataframe(df_keluar_view[["Tanggal", "Kode Barang", "Nama Barang", "Jumlah Keluar", "Keterangan"]], use_container_width=True)
            
            st.markdown("#### ⚙️ Aksi Penyesuaian Data")
            indeks_pilihan = st.number_input("Masukkan Nomor Baris yang ingin diproses:", min_value=0, max_value=len(df_keluar_th)-1, step=1, key="idx_keluar")
            item_terpilih = df_keluar_view.iloc[indeks_pilihan]
            st.info(f"Item Terpilih: **{item_terpilih['Nama Barang']}** | Keterangan: **{item_terpilih['Keterangan']}**")
            
            if st.button("🗑️ HAPUS TRANSAKSI PERMANEN", type="primary", key="btn_del_k"):
                df_keluar_sisa = df_keluar.drop(item_terpilih.name).reset_index(drop=True)
                payload = {"sheet": "Keluar", "action": "overwrite", "headers": ["Tanggal", "Kode Barang", "Jumlah Keluar", "Keterangan", "Tahun"], "data": df_keluar_sisa.values.tolist()}
                requests.post(URL_APPS_SCRIPT, data=json.dumps(payload))
                st.success("✔️ Transaksi berhasil dihapus!")
                st.rerun()


# ==========================================
# 6. MENU: PENGATURAN & TUTUP BUKU
# ==========================================
elif menu == "⚙️ Pengaturan & Tutup Buku":
    st.subheader("⚙️ Fitur Tutup Buku & Transfer Stok Akhir")
    st.markdown("Gunakan fitur ini saat pergantian tahun untuk **memindahkan Stok Akhir tahun berjalan menjadi Stok Awal di tahun baru** secara otomatis.")
    
    st.markdown("---")
    col_tb1, col_tb2 = st.columns(2)
    
    with col_tb1:
        st.markdown(f"### 📍 Tutup Buku Tahun {tahun_aktif}")
        tahun_target = st.number_input("Tujuan Tahun Baru (Buka Tahun):", min_value=tahun_aktif + 1, max_value=2050, value=tahun_aktif + 1, step=1)
        
        st.warning(f"Tindakan ini akan menghitung seluruh Sisa Stok di Tahun **{tahun_aktif}** dan menjadikannya Stok Awal untuk Tahun **{tahun_target}** di Google Sheets.")
        
        if st.button(f"🚀 PROSES TUTUP BUKU ({tahun_aktif} ➔ {tahun_target})", type="primary"):
            if df_master_th.empty:
                st.error("Tidak ada data master barang yang bisa diproses.")
            else:
                data_buka_tahun = []
                for idx, row in df_master_th.iterrows():
                    k_code = row["Kode Barang"]
                    k_nama = row["Nama Barang"]
                    s_akhir = hitung_stok_sekarang(k_code)
                    
                    data_buka_tahun.append([k_code, k_nama, int(tahun_target), int(s_akhir)])
                
                payload = {"sheet": "Master", "action": "append", "data": data_buka_tahun}
                res = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload))
                
                if res.status_code == 200:
                    st.balloons()
                    st.success(f"🎉 TUTUP BUKU SUKSES! Seluruh sisa stok tahun {tahun_aktif} berhasil ditransfer menjadi Stok Awal tahun {tahun_target}!")
                    st.rerun()
                else:
                    st.error("❌ Gagal memproses Tutup Buku ke Google Sheets.")

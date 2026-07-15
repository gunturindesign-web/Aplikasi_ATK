import streamlit as st
import pandas as pd
import requests
import json
from io import BytesIO

# =====================================================================
# ⚠️ MASUKKAN LINK GOOGLE SHEETS & URL APPS SCRIPT KAMU DI SINI!
# =====================================================================
URL_SPREADSHEET = "https://docs.google.com/spreadsheets/d/19Qv2SMhD4Ua5NBAI2DDzC46NT6rcaTcJSJ1Hb8ARiAU/edit?usp=sharing"

URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbwU90nE05v1iqX_4AHQtAzXtueg3ppGwSDr-WG-45hN3n1ycIYMMTlMZL0SXmoKLQWj/exec"

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

if "Kode Barang" not in df_master.columns:
    st.error("❌ Kolom 'Kode Barang' tidak ditemukan di tab Master Google Sheets Anda.")
    st.stop()

df_master["Kode Barang"] = df_master["Kode Barang"].astype(str).str.strip().str.upper()
if not df_masuk.empty and "Kode Barang" in df_masuk.columns:
    df_masuk["Kode Barang"] = df_masuk["Kode Barang"].astype(str).str.strip().str.upper()
if not df_keluar.empty and "Kode Barang" in df_keluar.columns:
    df_keluar["Kode Barang"] = df_keluar["Kode Barang"].astype(str).str.strip().str.upper()

# --- INSTANSIASI SESSION STATE ---
if "keranjang_masuk" not in st.session_state:
    st.session_state.keranjang_masuk = []
if "keranjang_keluar" not in st.session_state:
    st.session_state.keranjang_keluar = []
if "mode_edit_masuk" not in st.session_state:
    st.session_state.mode_edit_masuk = False
if "mode_edit_keluar" not in st.session_state:
    st.session_state.mode_edit_keluar = False

# --- TAMPILAN UTAMA STREAMLIT ---
st.set_page_config(page_title="Sistem Informasi ATK Set Bappebti", layout="wide")
st.title("📦 Sistem Pencatatan & Mutasi ATK Set Bappebti")
st.markdown("---")

menu = st.sidebar.selectbox(
    "PILIH MENU:", 
    [
        "📊 Dashboard & Mutasi", 
        "➕ Input Barang Baru", 
        "📥 Catat Barang Masuk", 
        "📤 Catat Barang Keluar",
        "✏️ Kelola & Riwayat Data"
    ]
)

def hitung_stok_sekarang(kode_barang):
    stok_awal = df_master[df_master["Kode Barang"] == kode_barang]["Stok Awal"].sum()
    total_masuk = df_masuk[df_masuk["Kode Barang"] == kode_barang]["Jumlah Masuk"].sum() if (not df_masuk.empty and "Jumlah Masuk" in df_masuk.columns) else 0
    total_keluar = df_keluar[df_keluar["Kode Barang"] == kode_barang]["Jumlah Keluar"].sum() if (not df_keluar.empty and "Jumlah Keluar" in df_keluar.columns) else 0
    return int(stok_awal + total_masuk - total_keluar)


# ==========================================
# 1. MENU: DASHBOARD & MUTASI
# ==========================================
if menu == "📊 Dashboard & Mutasi":
    st.subheader("Laporan Mutasi & Status Stok ATK")
    
    tipe_laporan = st.radio("Pilih Mode Tampilan Laporan:", ["📋 Ringkasan Semua Stok", "🔍 Lacak Histori Rinci Per Barang"], horizontal=True)
    st.markdown("---")
    
    if tipe_laporan == "📋 Ringkasan Semua Stok":
        total_masuk = df_masuk.groupby("Kode Barang")["Jumlah Masuk"].sum().reset_index() if (not df_masuk.empty and "Jumlah Masuk" in df_masuk.columns) else pd.DataFrame(columns=["Kode Barang", "Jumlah Masuk"])
        total_keluar = df_keluar.groupby("Kode Barang")["Jumlah Keluar"].sum().reset_index() if (not df_keluar.empty and "Jumlah Keluar" in df_keluar.columns) else pd.DataFrame(columns=["Kode Barang", "Jumlah Keluar"])
        
        df_mutasi = df_master.merge(total_masuk, on="Kode Barang", how="left").fillna(0)
        df_mutasi = df_mutasi.merge(total_keluar, on="Kode Barang", how="left").fillna(0)
        
        df_mutasi["Stok Akhir"] = df_mutasi["Stok Awal"] + df_mutasi["Jumlah Masuk"] - df_mutasi["Jumlah Keluar"]
        df_mutasi["Status"] = df_mutasi["Stok Akhir"].apply(lambda x: "🟢 MASIH" if x > 0 else "🔴 HABIS")
        
        for col in ["Stok Awal", "Jumlah Masuk", "Jumlah Keluar", "Stok Akhir"]:
            if col in df_mutasi.columns:
                df_mutasi[col] = df_mutasi[col].astype(int)
            
        st.dataframe(df_mutasi, use_container_width=True)
        
    else:
        st.markdown("### 🔎 Kartu Kendali & Histori Barang")
        pilihan_lacak = st.selectbox("Pilih ATK yang ingin Anda lacak historinya:", df_master["Kode Barang"] + " - " + df_master["Nama Barang"])
        kode_lacak = pilihan_lacak.split(" - ")[0].strip().upper()
        nama_lacak = pilihan_lacak.split(" - ")[1]
        
        stok_saat_ini = hitung_stok_sekarang(kode_lacak)
        st.metric(label=f"Sisa Stok Aktual '{nama_lacak}' saat ini", value=f"{stok_saat_ini} unit")
        
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            st.markdown("#### 📥 Riwayat Barang Masuk (Restock)")
            df_masuk_item = df_masuk[df_masuk["Kode Barang"] == kode_lacak] if (not df_masuk.empty and "Kode Barang" in df_masuk.columns) else pd.DataFrame()
            if df_masuk_item.empty:
                st.info("Belum pernah ada riwayat barang masuk untuk item ini.")
            else:
                st.dataframe(df_masuk_item[[c for c in ["Tanggal", "Jumlah Masuk"] if c in df_masuk_item.columns]], use_container_width=True)
                
        with col_h2:
            st.markdown("#### 📤 Riwayat Pengambilan (Barang Keluar)")
            df_keluar_item = df_keluar[df_keluar["Kode Barang"] == kode_lacak] if (not df_keluar.empty and "Kode Barang" in df_keluar.columns) else pd.DataFrame()
            if df_keluar_item.empty:
                st.info("Belum pernah ada riwayat pengambilan/barang keluar untuk item ini.")
            else:
                df_keluar_view_item = df_keluar_item.merge(df_master[["Kode Barang", "Nama Barang"]], on="Kode Barang", how="left")
                st.dataframe(df_keluar_view_item[[c for c in ["Tanggal", "Jumlah Keluar", "Keterangan"] if c in df_keluar_view_item.columns]], use_container_width=True)


# ==========================================
# 2. MENU: INPUT BARANG BARU
# ==========================================
elif menu == "➕ Input Barang Baru":
    st.subheader("Tambah Master Barang Baru")
    
    with st.form("form_barang_baru", clear_on_submit=True):
        kode = st.text_input("Kode Barang (Contoh: ATK-01)").strip().upper()
        nama = st.text_input("Nama Barang (Contoh: Kertas A4)").strip()
        stok_awal = st.number_input("Stok Awal", min_value=0, value=0, step=1)
        submit = st.form_submit_button("Simpan Permanen Ke Google Sheets")
        
        if submit:
            if kode in df_master["Kode Barang"].values:
                st.error("⚠️ Kode Barang sudah terdaftar di database!")
            elif kode == "" or nama == "":
                st.warning("⚠️ Kode dan Nama Barang tidak boleh kosong.")
            else:
                payload = {
                    "sheet": "Master",
                    "action": "append",
                    "data": [[kode, nama, int(stok_awal)]]
                }
                res = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload))
                if res.status_code == 200:
                    st.success(f"🎉 Sukses! {nama} berhasil tersimpan langsung di Google Sheets Master!")
                    st.rerun()
                else:
                    st.error("❌ Gagal menyimpan data via Apps Script.")


# ==========================================
# 3. MENU: CATAT BARANG MASUK (MULTI-ITEM)
# ==========================================
elif menu == "📥 Catat Barang Masuk":
    st.subheader("Input Barang Masuk / Restock (Multi-Item)")
    
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
        pilihan_barang = st.selectbox("Pilih Barang ", df_master["Kode Barang"] + " - " + df_master["Nama Barang"])
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
                data_rows = [[item["Tanggal"], item["Kode Barang"], item["Jumlah Masuk"]] for item in st.session_state.keranjang_masuk]
                payload = {"sheet": "Masuk", "action": "append", "data": data_rows}
                
                res = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload))
                if res.status_code == 200:
                    st.session_state.keranjang_masuk = []
                    st.success("🎉 Transaksi Restock Berhasil Disimpan Otomatis ke Cloud Google Sheets!")
                    st.rerun()
                else:
                    st.error("❌ Gagal mengirim data ke Google Sheets.")
        else:
            st.info("Keranjang masuk kosong.")


# ==========================================
# 4. MENU: CATAT BARANG KELUAR (MULTI-ITEM)
# ==========================================
elif menu == "📤 Catat Barang Keluar":
    st.subheader("Input Pengambilan / Barang Keluar (Multi-Item)")
    
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
        pilihan_barang = st.selectbox("Pilih Barang Keluar", df_master["Kode Barang"] + " - " + df_master["Nama Barang"])
        kode_barang = pilihan_barang.split(" - ")[0].strip().upper()
        nama_barang = pilihan_barang.split(" - ")[1]
        
        stok_gudang = hitung_stok_sekarang(kode_barang)
        stok_terpesan = sum(item['Jumlah Keluar'] for item in st.session_state.keranjang_keluar if item['Kode Barang'] == kode_barang)
        stok_efektif = stok_gudang - stok_terpesan
        
        st.caption(f"Stok Gudang: **{stok_gudang}** | Batas Aman Diambil: **{stok_efektif}**")
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
                data_rows = [[item["Tanggal"], item["Kode Barang"], item["Jumlah Keluar"], item["Keterangan"]] for item in st.session_state.keranjang_keluar]
                payload = {"sheet": "Keluar", "action": "append", "data": data_rows}
                
                res = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload))
                if res.status_code == 200:
                    st.session_state.keranjang_keluar = []
                    st.success("🎉 Sukses! Semua item otomatis ter-posting dan aman di Google Sheets Anda!")
                    st.rerun()
                else:
                    st.error("❌ Gagal mengirim transaksi ke Google Sheets.")
        else:
            st.info("Keranjang pengeluaran kosong.")


# ==========================================
# 5. MENU: KELOLA & RIWAYAT DATA (EDIT & HAPUS CLOUD)
# ==========================================
elif menu == "✏️ Kelola & Riwayat Data":
    st.subheader("Kelola Riwayat Transaksi (Edit, Hapus & Tambah Cloud)")
    
    kategori_data = st.radio("Pilih Data yang Ingin Dikelola:", ["📥 Riwayat Barang Masuk", "📤 Riwayat Barang Keluar"], horizontal=True)
    st.markdown("---")
    
    # ------------------------------------------
    # MENGELOLA DATA MASUK
    # ------------------------------------------
    if kategori_data == "📥 Riwayat Barang Masuk":
        if df_masuk.empty:
            st.info("Belum ada riwayat barang masuk.")
        else:
            st.markdown("### Daftar Transaksi Masuk")
            df_masuk_view = df_masuk.merge(df_master[["Kode Barang", "Nama Barang"]], on="Kode Barang", how="left")
            st.dataframe(df_masuk_view[["Tanggal", "Kode Barang", "Nama Barang", "Jumlah Masuk"]], use_container_width=True)
            
            st.markdown("#### ⚙️ Aksi Penyesuaian Data")
            indeks_pilihan = st.number_input("Masukkan Nomor Baris yang ingin diproses:", min_value=0, max_value=len(df_masuk)-1, step=1, key="idx_masuk")
            
            item_terpilih = df_masuk_view.iloc[indeks_pilihan]
            st.info(f"Item Terpilih: **{item_terpilih['Nama Barang']}** | Jumlah: **{item_terpilih['Jumlah Masuk']}**")
            
            col_btn1, col_btn2 = st.columns(2)
            if col_btn1.button("✏️ EDIT / TAMBAH BARANG DI BARIS INI", key="btn_edit_m"):
                st.session_state.mode_edit_masuk = True
                st.rerun()
                
            if col_btn2.button("🗑️ HAPUS TRANSAKSI PERMANEN", type="primary", key="btn_del_m"):
                df_masuk_baru = df_masuk.drop(df_masuk.index[indeks_pilihan]).reset_index(drop=True)
                data_rows = df_masuk_baru.values.tolist()
                payload = {"sheet": "Masuk", "action": "overwrite", "headers": ["Tanggal", "Kode Barang", "Jumlah Masuk"], "data": data_rows}
                
                res = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload))
                if res.status_code == 200:
                    st.success("✔️ Data masuk berhasil dihapus dari Cloud!")
                    st.session_state.mode_edit_masuk = False
                    st.rerun()
                
            if st.session_state.mode_edit_masuk:
                with st.form("form_edit_masuk"):
                    edit_tgl = st.date_input("Tanggal", pd.to_datetime(item_terpilih["Tanggal"]))
                    list_barang = (df_master["Kode Barang"] + " - " + df_master["Nama Barang"]).tolist()
                    default_idx = df_master["Kode Barang"].tolist().index(item_terpilih["Kode Barang"])
                    edit_barang = st.selectbox("Pilih Barang", list_barang, index=default_idx)
                    edit_qty = st.number_input("Jumlah Masuk", min_value=1, value=int(item_terpilih["Jumlah Masuk"]), step=1)
                    
                    c_edit, c_tambah, c_batal = st.columns(3)
                    btn_save = c_edit.form_submit_button("💾 SIMPAN PERUBAHAN BARIS")
                    btn_add_new = c_tambah.form_submit_button("➕ TAMBAH SEBAGAI BARANG BARU")
                    btn_cancel = c_batal.form_submit_button("❌ BATAL")
                    
                    if btn_save:
                        edit_kode = edit_barang.split(" - ")[0].strip().upper()
                        df_masuk.at[indeks_pilihan, "Tanggal"] = str(edit_tgl)
                        df_masuk.at[indeks_pilihan, "Kode Barang"] = edit_kode
                        df_masuk.at[indeks_pilihan, "Jumlah Masuk"] = int(edit_qty)
                        
                        payload = {"sheet": "Masuk", "action": "overwrite", "headers": ["Tanggal", "Kode Barang", "Jumlah Masuk"], "data": df_masuk.values.tolist()}
                        requests.post(URL_APPS_SCRIPT, data=json.dumps(payload))
                        st.session_state.mode_edit_masuk = False
                        st.rerun()
                        
                    if btn_add_new:
                        edit_kode = edit_barang.split(" - ")[0].strip().upper()
                        payload = {"sheet": "Masuk", "action": "append", "data": [[str(edit_tgl), edit_kode, int(edit_qty)]]}
                        requests.post(URL_APPS_SCRIPT, data=json.dumps(payload))
                        st.session_state.mode_edit_masuk = False
                        st.rerun()
                        
                    if btn_cancel:
                        st.session_state.mode_edit_masuk = False
                        st.rerun()

    # ------------------------------------------
    # MENGELOLA DATA KELUAR
    # ------------------------------------------
    elif kategori_data == "📤 Riwayat Barang Keluar":
        if df_keluar.empty:
            st.info("Belum ada riwayat barang keluar.")
        else:
            st.markdown("### Daftar Transaksi Keluar")
            df_keluar_view = df_keluar.merge(df_master[["Kode Barang", "Nama Barang"]], on="Kode Barang", how="left")
            st.dataframe(df_keluar_view[["Tanggal", "Kode Barang", "Nama Barang", "Jumlah Keluar", "Keterangan"]], use_container_width=True)
            
            st.markdown("#### ⚙️ Aksi Penyesuaian Data")
            indeks_pilihan = st.number_input("Masukkan Nomor Baris yang ingin diproses:", min_value=0, max_value=len(df_keluar)-1, step=1, key="idx_keluar")
            
            item_terpilih = df_keluar_view.iloc[indeks_pilihan]
            st.info(f"Item Terpilih: **{item_terpilih['Nama Barang']}** | Keterangan: **{item_terpilih['Keterangan']}**")
            
            col_btn1, col_btn2 = st.columns(2)
            if col_btn1.button("✏️ EDIT / TAMBAH BARANG DI BARIS INI", key="btn_edit_k"):
                st.session_state.mode_edit_keluar = True
                st.rerun()
                
            if col_btn2.button("🗑️ HAPUS TRANSAKSI PERMANEN", type="primary", key="btn_del_k"):
                df_keluar_baru = df_keluar.drop(df_keluar.index[indeks_pilihan]).reset_index(drop=True)
                payload = {"sheet": "Keluar", "action": "overwrite", "headers": ["Tanggal", "Kode Barang", "Jumlah Keluar", "Keterangan"], "data": df_keluar_baru.values.tolist()}
                
                res = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload))
                if res.status_code == 200:
                    st.success("✔️ Data keluar berhasil dihapus dari Cloud!")
                    st.session_state.mode_edit_keluar = False
                    st.rerun()
                
            if st.session_state.mode_edit_keluar:
                with st.form("form_edit_keluar"):
                    edit_tgl = st.date_input("Tanggal", pd.to_datetime(item_terpilih["Tanggal"]))
                    list_barang = (df_master["Kode Barang"] + " - " + df_master["Nama Barang"]).tolist()
                    default_idx = df_master["Kode Barang"].tolist().index(item_terpilih["Kode Barang"])
                    edit_barang = st.selectbox("Pilih Barang", list_barang, index=default_idx)
                    
                    edit_kode = edit_barang.split(" - ")[0].strip().upper()
                    stok_gudang = hitung_stok_sekarang(edit_kode)
                    if edit_kode == item_terpilih["Kode Barang"]:
                        stok_gudang += int(item_terpilih["Jumlah Keluar"])
                        
                    st.caption(f"Batas Maksimal Pengambilan Aman: **{stok_gudang}**")
                    edit_qty = st.number_input("Jumlah Keluar", min_value=1, value=int(item_terpilih["Jumlah Keluar"]), step=1)
                    edit_ket = st.text_input("Keterangan / Bagian", value=str(item_terpilih["Keterangan"]))
                    
                    c_edit, c_tambah, c_batal = st.columns(3)
                    btn_save = c_edit.form_submit_button("💾 SIMPAN PERUBAHAN BARIS")
                    btn_add_new = c_tambah.form_submit_button("➕ TAMBAH SEBAGAI BARANG BARU")
                    btn_cancel = c_batal.form_submit_button("❌ BATAL")
                    
                    if btn_save:
                        if edit_qty > stok_gudang:
                            st.error("❌ Jumlah pengambilan melebihi batas stok!")
                        elif edit_ket.strip() == "":
                            st.error("❌ Keterangan tidak boleh kosong!")
                        else:
                            df_keluar.at[indeks_pilihan, "Tanggal"] = str(edit_tgl)
                            df_keluar.at[indeks_pilihan, "Kode Barang"] = edit_kode
                            df_keluar.at[indeks_pilihan, "Jumlah Keluar"] = int(edit_qty)
                            df_keluar.at[indeks_pilihan, "Keterangan"] = edit_ket.strip()
                            
                            payload = {"sheet": "Keluar", "action": "overwrite", "headers": ["Tanggal", "Kode Barang", "Jumlah Keluar", "Keterangan"], "data": df_keluar.values.tolist()}
                            requests.post(URL_APPS_SCRIPT, data=json.dumps(payload))
                            st.session_state.mode_edit_keluar = False
                            st.rerun()
                            
                    if btn_add_new:
                        stok_riil = hitung_stok_sekarang(edit_kode)
                        if edit_qty > stok_riil:
                            st.error("❌ Stok barang baru ini tidak mencukupi!")
                        else:
                            payload = {"sheet": "Keluar", "action": "append", "data": [[str(edit_tgl), edit_kode, int(edit_qty), edit_ket.strip()]]}
                            requests.post(URL_APPS_SCRIPT, data=json.dumps(payload))
                            st.session_state.mode_edit_keluar = False
                            st.rerun()
                            
                    if btn_cancel:
                        st.session_state.mode_edit_keluar = False
                        st.rerun()

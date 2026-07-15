import streamlit as st
import pandas as pd
from io import BytesIO

# =====================================================================
# ⚠️ GANTI LINK DI BAWAH INI DENGAN LINK GOOGLE SHEETS KAMU YANG SUDAH DISHARE!
# =====================================================================
URL_SPREADSHEET = "https://docs.google.com/spreadsheets/d/1dVQPDihjQEL0CqBBvbuzZBQMqxVFJRole__Zyc3yzbM/edit?usp=sharing"

# Fungsi untuk mengubah URL share biasa menjadi URL download CSV/Excel khusus Streamlit
def dapatkan_url_sheet(url, nama_sheet):
    base_url = url.split('/edit')[0]
    return f"{base_url}/gviz/tq?tqx=out:csv&sheet={nama_sheet}"

# Membaca data secara live dari Google Sheets
try:
    df_master = pd.read_csv(dapatkan_url_sheet(URL_SPREADSHEET, "Master"))
    df_masuk = pd.read_csv(dapatkan_url_sheet(URL_SPREADSHEET, "Masuk"))
    df_keluar = pd.read_csv(dapatkan_url_sheet(URL_SPREADSHEET, "Keluar"))
except Exception as e:
    st.error("❌ Gagal terhubung ke Google Sheets. Pastikan URL sudah benar dan statusnya 'Anyone with the link'!")
    st.stop()

# Sinkronisasi tipe data agar tidak error saat pencarian
if not df_master.empty:
    df_master["Kode Barang"] = df_master["Kode Barang"].astype(str).str.strip().str.upper()
if not df_masuk.empty:
    df_masuk["Kode Barang"] = df_masuk["Kode Barang"].astype(str).str.strip().str.upper()
if not df_keluar.empty:
    df_keluar["Kode Barang"] = df_keluar["Kode Barang"].astype(str).str.strip().str.upper()

# --- INSTANSIASI SESSION STATE (KERANJANG BELANJA) ---
if "keranjang_masuk" not in st.session_state:
    st.session_state.keranjang_masuk = []
if "keranjang_keluar" not in st.session_state:
    st.session_state.keranjang_keluar = []

# --- TAMPILAN UTAMA STREAMLIT ---
st.set_page_config(page_title="Sistem Informasi ATK Set Bappebti", layout="wide")
st.title("📦 Sistem Pencatatan & Mutasi ATK Set Bappebti")
st.markdown("---")

# Menu Navigasi di Samping (Sidebar)
menu = st.sidebar.selectbox(
    "PILIH MENU:", 
    [
        "📊 Dashboard & Mutasi", 
        "➕ Input Barang Baru", 
        "📥 Catat Barang Masuk", 
        "📤 Catat Barang Keluar"
    ]
)

# --- FUNGSI UTILITAS UNTUK MENGHITUNG STOK AKTUAL ---
def hitung_stok_sekarang(kode_barang):
    stok_awal = df_master[df_master["Kode Barang"] == kode_barang]["Stok Awal"].sum()
    total_masuk = df_masuk[df_masuk["Kode Barang"] == kode_barang]["Jumlah Masuk"].sum() if not df_masuk.empty else 0
    total_keluar = df_keluar[df_keluar["Kode Barang"] == kode_barang]["Jumlah Keluar"].sum() if not df_keluar.empty else 0
    return int(stok_awal + total_masuk - total_keluar)

# --- FUNGSI MENGUBAH DATAFRAME MENJADI FILE EXCEL DI MEMORI ---
def konversi_ke_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Laporan')
    processed_data = output.getvalue()
    return processed_data


# ==========================================
# 1. MENU: DASHBOARD & MUTASI
# ==========================================
if menu == "📊 Dashboard & Mutasi":
    st.subheader("Laporan Mutasi & Status Stok ATK")
    
    if df_master.empty:
        st.info("Belum ada data barang di Google Sheets Master.")
    else:
        tipe_laporan = st.radio("Pilih Mode Tampilan Laporan:", ["📋 Ringkasan Semua Stok", "🔍 Lacak Histori Rinci Per Barang"], horizontal=True)
        st.markdown("---")
        
        if tipe_laporan == "📋 Ringkasan Semua Stok":
            total_masuk = df_masuk.groupby("Kode Barang")["Jumlah Masuk"].sum().reset_index() if not df_masuk.empty else pd.DataFrame(columns=["Kode Barang", "Jumlah Masuk"])
            total_keluar = df_keluar.groupby("Kode Barang")["Jumlah Keluar"].sum().reset_index() if not df_keluar.empty else pd.DataFrame(columns=["Kode Barang", "Jumlah Keluar"])
            
            df_mutasi = df_master.merge(total_masuk, on="Kode Barang", how="left").fillna(0)
            df_mutasi = df_mutasi.merge(total_keluar, on="Kode Barang", how="left").fillna(0)
            
            df_mutasi["Stok Akhir"] = df_mutasi["Stok Awal"] + df_mutasi["Jumlah Masuk"] - df_mutasi["Jumlah Keluar"]
            df_mutasi["Status"] = df_mutasi["Stok Akhir"].apply(lambda x: "🟢 MASIH" if x > 0 else "🔴 HABIS")
            
            for col in ["Stok Awal", "Jumlah Masuk", "Jumlah Keluar", "Stok Akhir"]:
                df_mutasi[col] = df_mutasi[col].astype(int)
                
            st.dataframe(df_mutasi, use_container_width=True)
            
            excel_data = konversi_ke_excel(df_mutasi)
            st.download_button(
                label="📥 CETAK / DOWNLOAD LAPORAN STOK (EXCEL)",
                data=excel_data,
                file_name="Laporan_Ringkasan_Stok_ATK.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
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
                df_masuk_item = df_masuk[df_masuk["Kode Barang"] == kode_lacak] if not df_masuk.empty else pd.DataFrame()
                if df_masuk_item.empty:
                    st.info("Belum pernah ada riwayat barang masuk untuk item ini.")
                else:
                    st.dataframe(df_masuk_item[["Tanggal", "Jumlah Masuk"]], use_container_width=True)
                    
            with col_h2:
                st.markdown("#### 📤 Riwayat Pengambilan (Barang Keluar)")
                df_keluar_item = df_keluar[df_keluar["Kode Barang"] == kode_lacak] if not df_keluar.empty else pd.DataFrame()
                if df_keluar_item.empty:
                    st.info("Belum pernah ada riwayat pengambilan/barang keluar untuk item ini.")
                else:
                    df_keluar_view_item = df_keluar_item.merge(df_master[["Kode Barang", "Nama Barang"]], on="Kode Barang", how="left")
                    st.dataframe(df_keluar_view_item[["Tanggal", "Jumlah Keluar", "Keterangan"]], use_container_width=True)


# ==========================================
# 2. MENU: INPUT BARANG BARU
# ==========================================
elif menu == "➕ Input Barang Baru":
    st.subheader("Tambah Master Barang Baru")
    st.info("💡 Catatan: Mode tulis harian terhubung ke Google Sheets. Silakan input langsung di form ini.")
    
    with st.form("form_barang_baru", clear_on_submit=True):
        kode = st.text_input("Kode Barang (Contoh: ATK-01)").strip().upper()
        nama = st.text_input("Nama Barang (Contoh: Kertas A4)").strip()
        stok_awal = st.number_input("Stok Awal", min_value=0, value=0, step=1)
        submit = st.form_submit_button("Simpan Barang Baru")
        
        if submit:
            if kode in df_master["Kode Barang"].values:
                st.error("⚠️ Kode Barang sudah terdaftar di database!")
            elif kode == "" or nama == "":
                st.warning("⚠️ Kode dan Nama Barang tidak boleh kosong.")
            else:
                new_data = pd.DataFrame([{"Kode Barang": kode, "Nama Barang": nama, "Stok Awal": stok_awal}])
                # Pengingat instruksi simpan
                st.success(f"✔️ Sukses menyiapkan {nama}! Silakan catat/salin data ini ke Google Sheets bagian Master Anda agar permanen.")


# ==========================================
# 3. MENU: CATAT BARANG MASUK (MULTI-ITEM)
# ==========================================
elif menu == "📥 Catat Barang Masuk":
    st.subheader("Input Barang Masuk / Restock (Multi-Item)")
    
    if df_master.empty:
        st.warning("⚠️ Isi Master Barang di Google Sheets terlebih dahulu.")
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
                    ket_gabungan_masuk = f"[{no_bukti_masuk}] - {keterangan_masuk}"
                    st.session_state.keranjang_masuk.append({
                        "Nota": no_bukti_masuk,
                        "Tanggal": str(tanggal_masuk),
                        "Kode Barang": kode_barang,
                        "Nama Barang": nama_barang,
                        "Jumlah Masuk": jumlah_masuk,
                        "Keterangan": ket_gabungan_masuk
                    })
                    st.success(f"Added: {nama_barang}")
                    st.rerun()
                
        with col_tbl:
            st.markdown(f"### 📋 Daftar Tampung Masuk (Nota: {no_bukti_masuk if no_bukti_masuk else '-'})")
            if st.session_state.keranjang_masuk:
                df_temp_masuk = pd.DataFrame(st.session_state.keranjang_masuk)
                st.dataframe(df_temp_masuk[["Nota", "Tanggal", "Nama Barang", "Jumlah Masuk", "Keterangan"]], use_container_width=True)
                
                c_batal, c_download = st.columns(2)
                if c_batal.button("🗑️ Kosongkan Daftar", key="clear_masuk", use_container_width=True):
                    st.session_state.keranjang_masuk = []
                    st.rerun()
                    
                # Tombol untuk memindahkan isi keranjang ke file Excel/Sheets
                excel_temp_masuk = konversi_ke_excel(df_temp_masuk[["Tanggal", "Kode Barang", "Jumlah Masuk"]])
                st.download_button(
                    label="💾 UNDUH FILE UNTUK COPY KE GOOGLE SHEETS",
                    data=excel_temp_masuk,
                    file_name="Salin_Ke_Sheet_Masuk.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.info("Keranjang masuk kosong.")


# ==========================================
# 4. MENU: CATAT BARANG KELUAR (MULTI-ITEM)
# ==========================================
elif menu == "📤 Catat Barang Keluar":
    st.subheader("Input Pengambilan / Barang Keluar (Multi-Item)")
    
    if df_master.empty:
        st.warning("⚠️ Isi Master Barang di Google Sheets terlebih dahulu.")
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
                        "Nota": no_bukti,
                        "Tanggal": str(tanggal_keluar),
                        "Kode Barang": kode_barang,
                        "Nama Barang": nama_barang,
                        "Jumlah Keluar": jumlah_keluar,
                        "Keterangan": keterangan_gabungan
                    })
                    st.success(f"✔️ {nama_barang} dimasukkan ke daftar sementara.")
                    st.rerun()

        with col_tbl:
            st.markdown(f"### 🛒 Keranjang Sementara (Nota: {no_bukti if no_bukti else '-'})")
            if st.session_state.keranjang_keluar:
                df_temp_keluar = pd.DataFrame(st.session_state.keranjang_keluar)
                st.dataframe(df_temp_keluar[["Nota", "Tanggal", "Nama Barang", "Jumlah Keluar", "Keterangan"]], use_container_width=True)
                
                c_batal, c_download = st.columns(2)
                if c_batal.button("🗑️ Kosongkan Keranjang", key="clear_keluar", use_container_width=True):
                    st.session_state.keranjang_keluar = []
                    st.rerun()
                    
                excel_temp_keluar = konversi_ke_excel(df_temp_keluar[["Tanggal", "Kode Barang", "Jumlah Keluar", "Keterangan"]])
                st.download_button(
                    label="💾 UNDUH FILE UNTUK COPY KE GOOGLE SHEETS",
                    data=excel_temp_keluar,
                    file_name="Salin_Ke_Sheet_Keluar.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.info("Keranjang pengeluaran kosong.")

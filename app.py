import streamlit as st
import pandas as pd
import os
from io import BytesIO

# Nama file database Excel
DB_FILE = "database_atk.xlsx"

# Fungsi untuk membuat database awal jika belum ada
def inisialisasi_database():
    if not os.path.exists(DB_FILE):
        with pd.ExcelWriter(DB_FILE, engine='openpyxl') as writer:
            df_barang = pd.DataFrame(columns=["Kode Barang", "Nama Barang", "Stok Awal"])
            df_barang.to_excel(writer, sheet_name="Master", index=False)
            df_masuk = pd.DataFrame(columns=["Tanggal", "Kode Barang", "Jumlah Masuk"])
            df_masuk.to_excel(writer, sheet_name="Masuk", index=False)
            df_keluar = pd.DataFrame(columns=["Tanggal", "Kode Barang", "Jumlah Keluar", "Keterangan"])
            df_keluar.to_excel(writer, sheet_name="Keluar", index=False)

# Jalankan inisialisasi database
inisialisasi_database()

# --- INSTANSIASI SESSION STATE (KERANJANG & TOMBOL EDIT STATE) ---
if "keranjang_masuk" not in st.session_state:
    st.session_state.keranjang_masuk = []
if "keranjang_keluar" not in st.session_state:
    st.session_state.keranjang_keluar = []
if "mode_edit_masuk" not in st.session_state:
    st.session_state.mode_edit_masuk = False
if "mode_edit_keluar" not in st.session_state:
    st.session_state.mode_edit_keluar = False

# --- TAMPILAN UTAMA STREAMLIT ---
st.set_page_config(page_title="Sistem Informasi ATK", layout="wide")
st.title("📦 Sistem Pencatatan & Mutasi ATK Set Bappebti")
st.markdown("---")

# Menu Navigasi di Samping (Sidebar)
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

# Membaca data aktual dari Excel dan memastikan tipe data Kode Barang sinkron sebagai string
df_master = pd.read_excel(DB_FILE, sheet_name="Master")
df_masuk = pd.read_excel(DB_FILE, sheet_name="Masuk")
df_keluar = pd.read_excel(DB_FILE, sheet_name="Keluar")

if not df_master.empty:
    df_master["Kode Barang"] = df_master["Kode Barang"].astype(str).str.strip().str.upper()
if not df_masuk.empty:
    df_masuk["Kode Barang"] = df_masuk["Kode Barang"].astype(str).str.strip().str.upper()
if not df_keluar.empty:
    df_keluar["Kode Barang"] = df_keluar["Kode Barang"].astype(str).str.strip().str.upper()

# --- FUNGSI UTILITAS UNTUK MENGHITUNG STOK AKTUAL ---
def hitung_stok_sekarang(kode_barang):
    stok_awal = df_master[df_master["Kode Barang"] == kode_barang]["Stok Awal"].sum()
    total_masuk = df_masuk[df_masuk["Kode Barang"] == kode_barang]["Jumlah Masuk"].sum()
    total_keluar = df_keluar[df_keluar["Kode Barang"] == kode_barang]["Jumlah Keluar"].sum()
    return int(stok_awal + total_masuk - total_keluar)

# --- FUNGSI UNTUK MENYIMPAN SHEET TERTENTU KE EXCEL ---
def simpan_ke_excel(df, sheet_name):
    with pd.ExcelWriter(DB_FILE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)

# --- FUNGSI MENGUBAH DATAFRAME MENJADI FILE EXCEL DI MEMORI (UNTUK DOWNLOAD) ---
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
        st.info("Belum ada data barang. Silakan tambah barang baru terlebih dahulu.")
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
                    
                    excel_masuk = konversi_ke_excel(df_masuk_item[["Tanggal", "Kode Barang", "Jumlah Masuk"]])
                    st.download_button(
                        label=f"🟢 Cetak Riwayat Masuk {nama_lacak}",
                        data=excel_masuk,
                        file_name=f"Riwayat_Masuk_{kode_lacak}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
            with col_h2:
                st.markdown("#### 📤 Riwayat Pengambilan (Barang Keluar)")
                df_keluar_item = df_keluar[df_keluar["Kode Barang"] == kode_lacak] if not df_keluar.empty else pd.DataFrame()
                if df_keluar_item.empty:
                    st.info("Belum pernah ada riwayat pengambilan/barang keluar untuk item ini.")
                else:
                    df_keluar_view_item = df_keluar_item.merge(df_master[["Kode Barang", "Nama Barang"]], on="Kode Barang", how="left")
                    st.dataframe(df_keluar_view_item[["Tanggal", "Jumlah Keluar", "Keterangan"]], use_container_width=True)
                    
                    excel_keluar = konversi_ke_excel(df_keluar_view_item[["Tanggal", "Kode Barang", "Nama Barang", "Jumlah Keluar", "Keterangan"]])
                    st.download_button(
                        label=f"🔴 Cetak Riwayat Keluar {nama_lacak}",
                        data=excel_keluar,
                        file_name=f"Riwayat_Keluar_{kode_lacak}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )


# ==========================================
# 2. MENU: INPUT BARANG BARU
# ==========================================
elif menu == "➕ Input Barang Baru":
    st.subheader("Tambah Master Barang Baru")
    
    with st.form("form_barang_baru", clear_on_submit=True):
        kode = st.text_input("Kode Barang (Contoh: ATK-01)").strip().upper()
        nama = st.text_input("Nama Barang (Contoh: Kertas A4)").strip()
        stok_awal = st.number_input("Stok Awal", min_value=0, value=0, step=1)
        submit = st.form_submit_button("Simpan Barang")
        
        if submit:
            if kode in df_master["Kode Barang"].values:
                st.error("⚠️ Kode Barang sudah terdaftar di database!")
            elif kode == "" or nama == "":
                st.warning("⚠️ Kode dan Nama Barang tidak boleh kosong.")
            else:
                new_data = pd.DataFrame([{"Kode Barang": kode, "Nama Barang": nama, "Stok Awal": stok_awal}])
                df_master = pd.concat([df_master, new_data], ignore_index=True)
                simpan_ke_excel(df_master, "Master")
                st.success(f"✔️ Sukses menambahkan {nama} ke Master!")
                st.rerun()


# ==========================================
# 3. MENU: CATAT BARANG MASUK (MULTI-ITEM)
# ==========================================
elif menu == "📥 Catat Barang Masuk":
    st.subheader("Input Barang Masuk / Restock (Multi-Item)")
    
    if df_master.empty:
        st.warning("⚠️ Isi Master Barang terlebih dahulu sebelum mencatat transaksi.")
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
                
                c_batal, c_simpan = st.columns(2)
                if c_batal.button("🗑️ Kosongkan Daftar", key="clear_masuk", use_container_width=True):
                    st.session_state.keranjang_masuk = []
                    st.rerun()
                    
                if c_simpan.button("💾 SIMPAN BARANG MASUK KE EXCEL", type="primary", key="save_masuk", use_container_width=True):
                    df_clean_masuk = df_temp_masuk[["Tanggal", "Kode Barang", "Jumlah Masuk"]]
                    df_masuk = pd.concat([df_masuk, df_clean_masuk], ignore_index=True)
                    simpan_ke_excel(df_masuk, "Masuk")
                    st.session_state.keranjang_masuk = []
                    st.success("🎉 Transaksi Restock berhasil disimpan permanen!")
                    st.rerun()
            else:
                st.info("Keranjang masuk kosong.")


# ==========================================
# 4. MENU: CATAT BARANG KELUAR (MULTI-ITEM)
# ==========================================
elif menu == "📤 Catat Barang Keluar":
    st.subheader("Input Pengambilan / Barang Keluar (Multi-Item)")
    
    if df_master.empty:
        st.warning("⚠️ Isi Master Barang terlebih dahulu sebelum mencatat pengeluaran.")
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
                
                c_batal, c_simpan = st.columns(2)
                if c_batal.button("🗑️ Kosongkan Keranjang", key="clear_keluar", use_container_width=True):
                    st.session_state.keranjang_keluar = []
                    st.rerun()
                    
                if c_simpan.button("💾 SIMPAN BARANG KELUAR", type="primary", key="save_keluar", use_container_width=True):
                    df_clean_keluar = df_temp_keluar[["Tanggal", "Kode Barang", "Jumlah Keluar", "Keterangan"]]
                    df_keluar = pd.concat([df_keluar, df_clean_keluar], ignore_index=True)
                    simpan_ke_excel(df_keluar, "Keluar")
                    st.session_state.keranjang_keluar = []
                    st.success("🎉 Sukses! Semua item berhasil dibukukan!")
                    st.rerun()
            else:
                st.info("Keranjang pengeluaran kosong.")


# ==========================================
# 5. MENU: KELOLA & RIWAYAT DATA (EDIT & HAPUS)
# ==========================================
elif menu == "✏️ Kelola & Riwayat Data":
    st.subheader("Kelola Riwayat Transaksi (Edit & Hapus Data)")
    
    kategori_data = st.radio("Pilih Data yang Ingin Dikelola:", ["📥 Riwayat Barang Masuk", "📤 Riwayat Barang Keluar"], horizontal=True)
    st.markdown("---")
    
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
            st.info(f"Item Terpilih: **{item_terpilih['Nama Barang']}** | Jumlah: **{item_terpilih['Jumlah Masuk']}** | Tanggal: **{item_terpilih['Tanggal']}**")
            
            col_btn1, col_btn2 = st.columns(2)
            if col_btn1.button("✏️ EDIT DATA BARIS INI", key="btn_edit_m"):
                st.session_state.mode_edit_masuk = True
                st.rerun()
                
            if col_btn2.button("🗑️ HAPUS TRANSAKSI PERMANEN", type="primary", key="btn_del_m"):
                df_masuk = df_masuk.drop(df_masuk.index[indeks_pilihan]).reset_index(drop=True)
                simpan_ke_excel(df_masuk, "Masuk")
                st.success("✔️ Transaksi masuk berhasil dihapus!")
                st.session_state.mode_edit_masuk = False
                st.rerun()
                
            if st.session_state.mode_edit_masuk:
                st.markdown("---")
                st.markdown("### 📝 Form Edit Barang Masuk")
                with st.form("form_edit_masuk"):
                    edit_tgl = st.date_input("Ubah Tanggal", pd.to_datetime(item_terpilih["Tanggal"]))
                    list_barang = (df_master["Kode Barang"] + " - " + df_master["Nama Barang"]).tolist()
                    default_idx = df_master["Kode Barang"].tolist().index(item_terpilih["Kode Barang"])
                    edit_barang = st.selectbox("Ubah Barang", list_barang, index=default_idx)
                    edit_qty = st.number_input("Ubah Jumlah Masuk", min_value=1, value=int(item_terpilih["Jumlah Masuk"]), step=1)
                    
                    c_simpan, c_batal = st.columns(2)
                    btn_save = c_simpan.form_submit_button("💾 SIMPAN PERUBAHAN DATA")
                    btn_cancel = c_batal.form_submit_button("❌ BATAL EDIT")
                    
                    if btn_save:
                        edit_kode = edit_barang.split(" - ")[0].strip().upper()
                        df_masuk.at[indeks_pilihan, "Tanggal"] = str(edit_tgl)
                        df_masuk.at[indeks_pilihan, "Kode Barang"] = edit_kode
                        df_masuk.at[indeks_pilihan, "Jumlah Masuk"] = int(edit_qty)
                        
                        simpan_ke_excel(df_masuk, "Masuk")
                        st.success("🎉 Perubahan data masuk berhasil disimpan permanen!")
                        st.session_state.mode_edit_masuk = False
                        st.rerun()
                        
                    if btn_cancel:
                        st.session_state.mode_edit_masuk = False
                        st.rerun()

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
            st.info(f"Item Terpilih: **{item_terpilih['Nama Barang']}** | Jumlah: **{item_terpilih['Jumlah Keluar']}** | Keterangan: **{item_terpilih['Keterangan']}**")
            
            col_btn1, col_btn2 = st.columns(2)
            if col_btn1.button("✏️ EDIT DATA BARIS INI", key="btn_edit_k"):
                st.session_state.mode_edit_keluar = True
                st.rerun()
                
            if col_btn2.button("🗑️ HAPUS TRANSAKSI PERMANEN", type="primary", key="btn_del_k"):
                df_keluar = df_keluar.drop(df_keluar.index[indeks_pilihan]).reset_index(drop=True)
                simpan_ke_excel(df_keluar, "Keluar")
                st.success("✔️ Transaksi keluar berhasil dihapus!")
                st.session_state.mode_edit_keluar = False
                st.rerun()
                
            if st.session_state.mode_edit_keluar:
                st.markdown("---")
                st.markdown("### 📝 Form Edit Barang Keluar")
                with st.form("form_edit_keluar"):
                    edit_tgl = st.date_input("Ubah Tanggal", pd.to_datetime(item_terpilih["Tanggal"]))
                    
                    list_barang = (df_master["Kode Barang"] + " - " + df_master["Nama Barang"]).tolist()
                    default_idx = df_master["Kode Barang"].tolist().index(item_terpilih["Kode Barang"])
                    edit_barang = st.selectbox("Ubah Barang", list_barang, index=default_idx)
                    
                    edit_kode = edit_barang.split(" - ")[0].strip().upper()
                    stok_gudang = hitung_stok_sekarang(edit_kode)
                    if edit_kode == item_terpilih["Kode Barang"]:
                        stok_gudang += int(item_terpilih["Jumlah Keluar"])
                        
                    st.caption(f"Batas Maksimal Pengambilan Aman: **{stok_gudang}**")
                    edit_qty = st.number_input("Ubah Jumlah Keluar", min_value=1, value=int(item_terpilih["Jumlah Keluar"]), step=1)
                    edit_ket = st.text_input("Ubah Keterangan / Bagian", value=str(item_terpilih["Keterangan"]))
                    
                    c_simpan, c_batal = st.columns(2)
                    btn_save = c_simpan.form_submit_button("💾 SIMPAN PERUBAHAN DATA")
                    btn_cancel = c_batal.form_submit_button("❌ BATAL EDIT")
                    
                    if btn_save:
                        if edit_qty > stok_gudang:
                            st.error(f"❌ Transaksi Gagal! Jumlah keluar ({edit_qty}) melebihi stok yang ada ({stok_gudang}).")
                        elif edit_ket.strip() == "":
                            st.error("❌ Keterangan tidak boleh kosong!")
                        else:
                            df_keluar.at[indeks_pilihan, "Tanggal"] = str(edit_tgl)
                            df_keluar.at[indeks_pilihan, "Kode Barang"] = edit_kode
                            df_keluar.at[indeks_pilihan, "Jumlah Keluar"] = int(edit_qty)
                            df_keluar.at[indeks_pilihan, "Keterangan"] = edit_ket.strip()
                            
                            simpan_ke_excel(df_keluar, "Keluar")
                            st.success("🎉 Perubahan data keluar berhasil disimpan permanen!")
                            st.session_state.mode_edit_keluar = False
                            st.rerun()
                            
                    if btn_cancel:
                        st.session_state.mode_edit_keluar = False
                        st.rerun()

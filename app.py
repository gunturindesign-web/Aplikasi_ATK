import streamlit as st
import pandas as pd
import os
from io import BytesIO

# Nama file database Excel
DB_FILE = "database_atk.xlsx"

# Fungsi otomatis untuk membuat file Excel jika belum ada
if not os.path.exists(DB_FILE):
    with pd.ExcelWriter(DB_FILE, engine='openpyxl') as writer:
        pd.DataFrame(columns=["Kode Barang", "Nama Barang", "Stok Awal"]).to_excel(writer, sheet_name="Master", index=False)
        pd.DataFrame(columns=["Tanggal", "No Bukti", "Kode Barang", "Jumlah Masuk"]).to_excel(writer, sheet_name="Masuk", index=False)
        pd.DataFrame(columns=["Tanggal", "No Bukti", "Kode Barang", "Jumlah Keluar", "Keterangan"]).to_excel(writer, sheet_name="Keluar", index=False)

# Mengatur Tampilan Halaman Web
st.set_page_config(page_title="Aplikasi ATK Pro", layout="wide")
st.title("📦 APLIKASI PERSEDIAAN BAPPEBTI")
st.markdown("---")

# Membaca Data dari Excel
df_master = pd.read_excel(DB_FILE, sheet_name="Master")
df_masuk = pd.read_excel(DB_FILE, sheet_name="Masuk")
df_keluar = pd.read_excel(DB_FILE, sheet_name="Keluar")

# Memastikan kolom No Bukti ada
if "No Bukti" not in df_masuk.columns:
    df_masuk.insert(1, "No Bukti", "-")
if "No Bukti" not in df_keluar.columns:
    df_keluar.insert(1, "No Bukti", "-")

# Menu Navigasi di Samping (Sidebar)
menu = st.sidebar.selectbox("PILIH MENU:", [
    "📊 Dashboard & Stok", 
    "➕ Tambah Master Barang", 
    "📥 Catat Barang Masuk", 
    "📤 Catat Barang Keluar",
    "✏️ Edit / Kelola Data"
])

# --- 1. MENU DASHBOARD (DENGAN FILTER & DOWNLOAD) ---
if menu == "📊 Dashboard & Stok":
    st.subheader("Laporan Mutasi & Sisa Stok")
    
    if df_master.empty:
        st.info("Belum ada data barang. Silakan ke menu 'Tambah Master Barang' terlebih dahulu.")
    else:
        # Proses Hitung Stok Otomatis
        total_masuk = df_masuk.groupby("Kode Barang")["Jumlah Masuk"].sum().reset_index()
        total_keluar = df_keluar.groupby("Kode Barang")["Jumlah Keluar"].sum().reset_index()
        
        df_mutasi = df_master.merge(total_masuk, on="Kode Barang", how="left").fillna(0)
        df_mutasi = df_mutasi.merge(total_keluar, on="Kode Barang", how="left").fillna(0)
        
        df_mutasi["Stok Akhir"] = df_mutasi["Stok Awal"] + df_mutasi["Jumlah Masuk"] - df_mutasi["Jumlah Keluar"]
        df_mutasi["Status"] = df_mutasi["Stok Akhir"].apply(lambda x: "🟢 MASIH" if x > 0 else "🔴 HABIS")
        
        # --- FITUR BARU: FILTER PENCARIAN ---
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            cari_nama = st.text_input("🔍 Cari Nama atau Kode Barang:")
        with col_f2:
            pilih_status = st.selectbox("📌 Filter Status Stok:", ["Semua", "🟢 MASIH", "🔴 HABIS"])
        
        # Aplikasikan Filter ke Tabel
        if cari_nama:
            df_mutasi = df_mutasi[df_mutasi["Nama Barang"].str.contains(cari_nama, case=False) | df_mutasi["Kode Barang"].str.contains(cari_nama, case=False)]
        if pilih_status != "Semua":
            df_mutasi = df_mutasi[df_mutasi["Status"] == pilih_status]
        
        # Tampilkan Tabel Hasil Filter
        st.dataframe(df_mutasi, use_container_width=True)
        
        # --- FITUR BARU: TOMBOL DOWNLOAD EXCEL ---
        # Mengubah data dataframe mutasi menjadi file excel di dalam memori komputer
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_mutasi.to_excel(writer, index=False, sheet_name="Laporan_Mutasi")
        processed_data = output.getvalue()
        
        st.download_button(
            label="📥 Unduh Laporan Mutasi (Excel)",
            data=processed_data,
            file_name="Laporan_Mutasi_ATK.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# --- 2. MENU TAMBAH BARANG ---
elif menu == "➕ Tambah Master Barang":
    st.subheader("Tambah Barang Baru ke Sistem")
    with st.form("form_baru", clear_on_submit=True):
        kode = st.text_input("Kode Barang (Misal: ATK-01)")
        nama = st.text_input("Nama Barang (Misal: Pulpen)")
        stok_awal = st.number_input("Stok Awal Gudang", min_value=0, value=0)
        tombol = st.form_submit_button("Simpan Master Barang")
        
        if tombol:
            if kode in df_master["Kode Barang"].values:
                st.error("Kode barang ini sudah terdaftar!")
            elif kode == "" or nama == "":
                st.warning("Kode dan Nama tidak boleh kosong!")
            else:
                data_baru = pd.DataFrame([{"Kode Barang": kode, "Nama Barang": nama, "Stok Awal": stok_awal}])
                df_master = pd.concat([df_master, data_baru], ignore_index=True)
                with pd.ExcelWriter(DB_FILE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    df_master.to_excel(writer, sheet_name="Master", index=False)
                st.success(f"Berhasil menyimpan {nama}!")

# --- 3. MENU BARANG MASUK ---
elif menu == "📥 Catat Barang Masuk":
    st.subheader("Input Barang Masuk / Restock")
    if df_master.empty:
        st.warning("Silakan isi Master Barang terlebih dahulu.")
    else:
        with st.form("form_masuk", clear_on_submit=True):
            tgl = st.date_input("Tanggal Masuk")
            no_bukti = st.text_input("No. Bukti / Nota Masuk (Contoh: BM-001)")
            pilihan = st.selectbox("Pilih Barang", df_master["Kode Barang"] + " - " + df_master["Nama Barang"])
            kd_barang = pilihan.split(" - ")[0]
            jml = st.number_input("Jumlah Masuk", min_value=1)
            tombol = st.form_submit_button("Simpan Barang Masuk")
            
            if tombol:
                data_masuk = pd.DataFrame([{"Tanggal": str(tgl), "No Bukti": no_bukti, "Kode Barang": kd_barang, "Jumlah Masuk": jml}])
                df_masuk = pd.concat([df_masuk, data_masuk], ignore_index=True)
                with pd.ExcelWriter(DB_FILE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    df_masuk.to_excel(writer, sheet_name="Masuk", index=False)
                st.success("Data masuk berhasil disimpan!")

# --- 4. MENU BARANG KELUAR (DENGAN VALIDASI STOK) ---
elif menu == "📤 Catat Barang Keluar":
    st.subheader("Input Pengambilan / Barang Keluar")
    if df_master.empty:
        st.warning("Silakan isi Master Barang terlebih dahulu.")
    else:
        with st.form("form_keluar", clear_on_submit=True):
            tgl = st.date_input("Tanggal Keluar")
            no_bukti = st.text_input("No. Bukti / Nota Keluar (Contoh: BK-001)")
            pilihan = st.selectbox("Pilih Barang", df_master["Kode Barang"] + " - " + df_master["Nama Barang"])
            kd_barang = pilihan.split(" - ")[0]
            jml = st.number_input("Jumlah Keluar", min_value=1)
            ket = st.text_input("Keterangan / Bagian yang Mengambil")
            tombol = st.form_submit_button("Simpan Barang Keluar")
            
            if tombol:
                # --- FITUR BARU: HITUNG SISA STOK REAL-TIME UNTUK VALIDASI ---
                stok_awal_ini = df_master[df_master["Kode Barang"] == kd_barang]["Stok Awal"].values[0]
                total_masuk_ini = df_masuk[df_masuk["Kode Barang"] == kd_barang]["Jumlah Masuk"].sum()
                total_keluar_ini = df_keluar[df_keluar["Kode Barang"] == kd_barang]["Jumlah Keluar"].sum()
                stok_tersedia = stok_awal_ini + total_masuk_ini - total_keluar_ini
                
                # Cek apakah stok cukup atau tidak
                if jml > stok_tersedia:
                    st.error(f"❌ Transaksi Ditolak! Stok tidak mencukupi. Sisa stok {pilihan} saat ini hanya: {int(stok_tersedia)}")
                else:
                    data_keluar = pd.DataFrame([{"Tanggal": str(tgl), "No Bukti": no_bukti, "Kode Barang": kd_barang, "Jumlah Keluar": jml, "Keterangan": ket}])
                    df_keluar = pd.concat([df_keluar, data_keluar], ignore_index=True)
                    with pd.ExcelWriter(DB_FILE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                        df_keluar.to_excel(writer, sheet_name="Keluar", index=False)
                    st.success("Data keluar berhasil disimpan!")

# --- 5. MENU EDIT / KELOLA DATA ---
elif menu == "✏️ Edit / Kelola Data":
    st.subheader("Pengaturan & Modifikasi Data")
    
    sub_menu = st.radio("Pilih Data yang Ingin Dikelola:", ["Data Master Barang", "Data Barang Masuk", "Data Barang Keluar"], horizontal=True)
    st.markdown("---")
    
    if sub_menu == "Data Master Barang":
        st.write("### Daftar Master Barang")
        st.dataframe(df_master, use_container_width=True)
        
        if not df_master.empty:
            pilih_edit = st.selectbox("Pilih Kode Barang yang ingin diedit/hapus:", df_master["Kode Barang"])
            idx = df_master[df_master["Kode Barang"] == pilih_edit].index[0]
            
            with st.form("form_edit_master"):
                new_nama = st.text_input("Ubah Nama Barang:", value=df_master.loc[idx, "Nama Barang"])
                new_stok_awal = st.number_input("Ubah Stok Awal:", value=int(df_master.loc[idx, "Stok Awal"]))
                
                col1, col2 = st.columns(2)
                with col1:
                    btn_update = st.form_submit_button("🔥 Perbarui Data")
                with col2:
                    btn_hapus = st.form_submit_button("🗑️ Hapus Barang")
                
                if btn_update:
                    df_master.loc[idx, "Nama Barang"] = new_nama
                    df_master.loc[idx, "Stok Awal"] = new_stok_awal
                    with pd.ExcelWriter(DB_FILE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                        df_master.to_excel(writer, sheet_name="Master", index=False)
                    st.success("Data master berhasil diperbarui!")
                    st.rerun()
                    
                if btn_hapus:
                    df_master = df_master.drop(idx).reset_index(drop=True)
                    with pd.ExcelWriter(DB_FILE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                        df_master.to_excel(writer, sheet_name="Master", index=False)
                    st.success("Data barang berhasil dihapus dari sistem!")
                    st.rerun()

    elif sub_menu == "Data Barang Masuk":
        st.write("### Riwayat Barang Masuk")
        st.dataframe(df_masuk, use_container_width=True)
        
        if not df_masuk.empty:
            pilih_idx = st.number_input("Masukkan nomor baris (Index paling kiri) yang ingin dihapus:", min_value=0, max_value=len(df_masuk)-1, step=1)
            btn_hapus_masuk = st.button("🗑️ Hapus Transaksi Masuk Ini")
            
            if btn_hapus_masuk:
                df_masuk = df_masuk.drop(pilih_idx).reset_index(drop=True)
                with pd.ExcelWriter(DB_FILE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    df_masuk.to_excel(writer, sheet_name="Masuk", index=False)
                st.success("Transaksi masuk berhasil dihapus!")
                st.rerun()

    elif sub_menu == "Data Barang Keluar":
        st.write("### Riwayat Barang Keluar")
        st.dataframe(df_keluar, use_container_width=True)
        
        if not df_keluar.empty:
            pilih_idx_keluar = st.number_input("Masukkan nomor baris (Index paling kiri) yang ingin dihapus:", min_value=0, max_value=len(df_keluar)-1, step=1)
            btn_hapus_keluar = st.button("🗑️ Hapus Transaksi Keluar Ini")
            
            if btn_hapus_keluar:
                df_keluar = df_keluar.drop(pilih_idx_keluar).reset_index(drop=True)
                with pd.ExcelWriter(DB_FILE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    df_keluar.to_excel(writer, sheet_name="Keluar", index=False)
                st.success("Transaksi keluar berhasil dihapus!")
                st.rerun()

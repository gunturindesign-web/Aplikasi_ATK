# ==========================================
# 4. MENU: CATAT BARANG KELUAR (MULTI-ITEM DENGAN NOTA)
# ==========================================
elif menu == "📤 Catat Barang Keluar":
    st.subheader("Input Pengambilan / Barang Keluar (Multi-Item)")
    
    if df_master.empty:
        st.warning("⚠️ Isi Master Barang terlebih dahulu sebelum mencatat pengeluaran.")
    else:
        # Form Header Informasi Nota Keluar
        st.markdown("### 📋 Data Nota / Bukti Keluar")
        col_nota1, col_nota2 = st.columns(2)
        with col_nota1:
            tanggal_keluar = st.date_input("Tanggal Keluar")
            no_bukti = st.text_input("No. Bukti / Nota Keluar (Contoh: BK-001)").strip().upper()
        with col_nota2:
            bagian_pengambil = st.text_input("Keterangan / Bagian yang Mengambil").strip()

        st.markdown("---")

        # Layout Kolom Transaksi
        col_in, col_tbl = st.columns([1, 2])
        
        with col_in:
            st.markdown("### ➕ Tambah Barang")
            pilihan_barang = st.selectbox("Pilih Barang Keluar", df_master["Kode Barang"] + " - " + df_master["Nama Barang"])
            kode_barang = pilihan_barang.split(" - ")[0]
            nama_barang = pilihan_barang.split(" - ")[1]
            
            # Sistem Validasi Pengaman Stok
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
                st.dataframe(df_temp_keluar[["Nota", "Tanggal", "Nama Barang", "Jumlah Keluar", "Keterangan"]], width="stretch", index=False)
                
                c_batal, c_simpan = st.columns(2)
                if c_batal.button("🗑️ Kosongkan Keranjang", key="clear_keluar", use_container_width=True):
                    st.session_state.keranjang_keluar = []
                    st.rerun()
                    
                if c_simpan.button("💾 SIMPAN BARANG KELUAR", type="primary", key="save_keluar", use_container_width=True):
                    df_clean_keluar = df_temp_keluar[["Tanggal", "Kode Barang", "Jumlah Keluar", "Keterangan"]]
                    df_keluar = pd.concat([df_keluar, df_clean_keluar], ignore_index=True)
                    
                    with pd.ExcelWriter(DB_FILE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                        df_keluar.to_excel(writer, sheet_name="Keluar", index=False)
                        
                    st.session_state.keranjang_keluar = []
                    st.success(f"🎉 Sukses! Semua item untuk Nota {no_bukti} berhasil dibukukan!")
                    st.rerun()
            else:
                st.info("Keranjang pengeluaran kosong. Silakan lengkapi form nota di atas.")

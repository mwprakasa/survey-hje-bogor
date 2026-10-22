import hmac
from datetime import datetime
from zoneinfo import ZoneInfo

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Survey HJE Retail Area Bogor", page_icon="📋")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
TAB_MASTER = "Masterdata"
TAB_HASIL = "Hasil"
JUMLAH_KOLOM_DEPAN = 5  # Waktu, Kode Cust, Nama Outlet, Rayon, Zona


# ---------- Password akses (opsional) ----------
if "app_password" in st.secrets:
    if not st.session_state.get("lolos"):
        st.title("Survey HJE Retail Area Bogor")
        pw = st.text_input("Password akses", type="password")
        if pw:
            if hmac.compare_digest(pw.encode(), str(st.secrets["app_password"]).encode()):
                st.session_state["lolos"] = True
                st.rerun()
            else:
                st.error("Password salah")
        st.stop()


# ---------- Koneksi Google Sheets ----------
@st.cache_resource
def buka_spreadsheet():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=SCOPES
    )
    return gspread.authorize(creds).open(st.secrets["sheet_name"])


@st.cache_data(ttl=600)
def muat_master():
    baris = buka_spreadsheet().worksheet(TAB_MASTER).get_all_values()[1:]
    master = {}
    for r in baris:
        if len(r) >= 4 and str(r[0]).strip():
            master[str(r[0]).strip()] = (r[1].strip(), r[2].strip(), r[3].strip())
    return master


@st.cache_data(ttl=600)
def muat_brand():
    header = buka_spreadsheet().worksheet(TAB_HASIL).row_values(1)
    return [b.strip() for b in header[JUMLAH_KOLOM_DEPAN:] if b.strip()]


try:
    master = muat_master()
    brands = muat_brand()
except Exception as e:
    st.error(f"Gagal membaca Google Sheet: {e}")
    st.stop()

if not brands:
    st.error("Header brand di tab Hasil tidak ditemukan.")
    st.stop()


# ---------- Simpan data ----------
def simpan():
    kode = st.session_state.get("kode", "").strip()
    info = master.get(kode)
    if not info:
        st.session_state["pesan"] = ("error", "Kode Cust tidak ditemukan di masterdata.")
        return
    harga = [int(st.session_state.get(f"b_{i}") or 0) for i in range(len(brands))]
    waktu = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%Y-%m-%d %H:%M:%S")
    nilai_kode = int(kode) if kode.isdigit() else kode
    baris = [waktu, nilai_kode, info[0], info[1], info[2]] + harga
    try:
        buka_spreadsheet().worksheet(TAB_HASIL).append_row(baris, value_input_option="RAW")
    except Exception as e:
        st.session_state["pesan"] = ("error", f"Gagal menyimpan: {e}")
        return
    st.session_state["pesan"] = ("success", f"Tersimpan: {info[0]} ({kode})")
    st.session_state["kode"] = ""
    for i in range(len(brands)):
        st.session_state[f"b_{i}"] = 0


# ---------- Tampilan ----------
st.title("Survey HJE Retail Area Bogor")

pesan = st.session_state.pop("pesan", None)
if pesan:
    (st.success if pesan[0] == "success" else st.error)(pesan[1])

st.header("Customer")
kode = st.text_input("Kode Cust", key="kode").strip()

info = master.get(kode) if kode else None
if kode and not info:
    st.error("Kode Cust tidak ditemukan di masterdata.")

if info:
    st.text_input("Nama Outlet", value=info[0], disabled=True, key=f"nama_{kode}")
    st.text_input("Rayon", value=info[1], disabled=True, key=f"rayon_{kode}")
    st.text_input("Zona", value=info[2], disabled=True, key=f"zona_{kode}")

    st.header("Harga Jual Eceran")
    st.caption("Isi angka saja. Yang tidak diisi otomatis tersimpan 0.")
    with st.form("form_harga"):
        for i, brand in enumerate(brands):
            st.number_input(
                f"{brand} (Rp)", min_value=0, step=500, format="%d", key=f"b_{i}"
            )
        st.form_submit_button("Simpan Survey", on_click=simpan, type="primary")

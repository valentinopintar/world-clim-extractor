import streamlit as st
import pandas as pd
import rasterio
from rasterio.windows import Window
from io import BytesIO

def extract_from_zip(df, lon_col, lat_col, var, res, pixel_window, zip_url):
    coords = list(zip(df[lon_col], df[lat_col]))
    result = df.copy()

    gdal_cfg = {
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".zip,.tif",
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_USE_HEAD": "YES"
    }

    for m in range(1,13):
        mstr = f"{m:02d}"
        inside = f"wc2.1_{res}_{var}_{mstr}.tif"
        vsi_path = f"/vsizip//vsicurl/{zip_url}/{inside}"
        vals = []
        with rasterio.Env(**gdal_cfg):
            with rasterio.open(vsi_path) as src:
                if pixel_window:
                    for lon, lat in coords:
                        row, col = src.index(lon, lat)
                        win = Window(col - pixel_window//2,
                                     row - pixel_window//2,
                                     pixel_window, pixel_window)
                        arr = src.read(1, window=win, boundless=True)
                        vals.append(float(arr.mean()))
                else:
                    vals = [v[0] for v in src.sample(coords)]
        result[f"{var}_{res}_{mstr}"] = vals

    return result

# Streamlit UI
st.title("WorldClim ZIP Extractor")
uploaded = st.file_uploader("Upload CSV or XLSX", type=["csv","xlsx"])
if uploaded:
    df = pd.read_excel(uploaded) if uploaded.name.endswith(("xls","xlsx")) else pd.read_csv(uploaded)
    st.dataframe(df.head())
    lon_col = st.text_input("Longitude column", "Longitude")
    lat_col = st.text_input("Latitude column", "Latitude")
    var = st.selectbox("Variable", ["tmin","tmax","tavg","prec","srad","wind","vapr"])
    res = st.selectbox("Resolution", ["30s","2.5m","5m","10m"])
    pw = st.number_input("Pixel window (odd integer)", min_value=1, step=2, value=1)
    base_url = "geodata.ucdavis.edu/climate/worldclim/2_1/base"
    zip_url = f"{base_url}/wc2.1_{res}_{var}.zip"
    st.write(f"Using ZIP URL: {zip_url}")
    save_format = st.radio("Download format", ["CSV", "Excel (XLSX)"])
    file_name = st.text_input("Output filename (no extension)", "output")

    if st.button("Run extraction"):
        with st.spinner("Extracting..."):
            out = extract_from_zip(df, lon_col, lat_col, var, res, pw if pw>1 else None, zip_url)
        st.success("Done!")

        st.write("### First 10 rows of extracted data")
        st.dataframe(out.head(10))

        if save_format == "CSV":
            csv_bytes = out.to_csv(index=False).encode()
            st.download_button("Download CSV", data=csv_bytes, file_name=f"{file_name}.csv")
        else:
            xlsx_buffer = BytesIO()
            out.to_excel(xlsx_buffer, index=False, engine="openpyxl")
            xlsx_buffer.seek(0)
            st.download_button("Download Excel", data=xlsx_buffer, file_name=f"{file_name}.xlsx")

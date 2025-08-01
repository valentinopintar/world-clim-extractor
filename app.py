import streamlit as st
import pandas as pd
import rasterio
from rasterio.windows import Window
from io import BytesIO

def extract_from_zip(df, lon_col, lat_col, var, res, pixel_window, zip_url):
    """
    Read either monthly (12) or bioclimatic (19) variables from a WorldClim .zip file
    via remote access using GDAL's virtual filesystem. Returns a copy of `df`
    with added columns like 'bio_30s_5' or 'tmin_2.5m_07'.
    """
    coords = list(zip(df[lon_col], df[lat_col]))
    result = df.copy()

    gdal_cfg = {
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".zip,.tif",
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_USE_HEAD": "YES"
    }

    # Bioclim has exactly 19 layers; all others have 12 monthly values
    max_layer = 19 if var.lower() == "bio" else 12
    for i in range(1, max_layer + 1):
        if var.lower() == "bio":
            # Bioclim 19, starts with 1
            istr = str(i)
        else:
            istr = f"{i:02d}"
        inside = f"wc2.1_{res}_{var}_{istr}.tif"

        vsi_path = f"/vsizip/vsicurl/{zip_url}/{inside}"

        vals = []
        with rasterio.Env(**gdal_cfg):
            with rasterio.open(vsi_path) as src:
                if pixel_window and pixel_window > 1:
                    vals = []  # N×N focal mean
                    for lon, lat in coords:
                        row, col = src.index(lon, lat)
                        win = Window(
                            col - pixel_window // 2,
                            row - pixel_window // 2,
                            pixel_window,
                            pixel_window
                        )
                        arr = src.read(1, window=win, boundless=True)
                        vals.append(float(arr.mean()))
                else:
                    vals = [v[0] for v in src.sample(coords)]
        result[f"{var}_{res}_{istr}"] = vals


    return result

# --- Streamlit user interface ---
st.set_page_config(layout="wide")
st.title("🌍 WorldClim Extractor")

col1, col2 = st.columns([2, 1])

with col1:
    uploaded = st.file_uploader(
        "📄 Upload CSV or Excel file with coordinates",
        type=["csv", "xlsx"]
    )
    if uploaded:
        df = (
            pd.read_excel(uploaded)
            if uploaded.name.lower().endswith(("xls", "xlsx"))
            else pd.read_csv(uploaded)
        )
        st.subheader("📋 Preview of uploaded data")
        st.dataframe(df.head())

        lon_col = st.text_input("🧭 Longitude column", "Longitude")
        lat_col = st.text_input("🧭 Latitude column", "Latitude")
        var = st.selectbox("📌 Variable", ["bio","elev","tmin","tmax","tavg","prec","srad","wind","vapr"])
        res = st.selectbox("📏 Resolution", ["30s","2.5m","5m","10m"])
        pw = st.number_input(
            "🪟 Pixel window (odd integer)",
            min_value=1,
            step=2,
            value=1
        )

        base_url = "https://geodata.ucdavis.edu/climate/worldclim/2_1/base"
        zip_url = f"{base_url}/wc2.1_{res}_{var}.zip"
        st.markdown(f"📦 **Using ZIP URL**: [{zip_url}]({zip_url})")

        save_format = st.radio("💾 Download format", ["CSV", "Excel (XLSX)"])
        file_name = st.text_input("✏️ Output filename (no extension)", "output")

        if st.button("▶️ Run extraction"):
            with st.spinner("🔍 Extracting..."):
                out = extract_from_zip(
                    df,
                    lon_col,
                    lat_col,
                    var,
                    res,
                    pw if pw > 1 else None,
                    zip_url
                )
            st.success("✅ Extraction complete!")

            st.write("### 📈 First 10 rows of extracted data")
            st.dataframe(out.head(10))

            if save_format == "CSV":
                csv_bytes = out.to_csv(index=False).encode()
                st.download_button("⬇️ Download CSV", data=csv_bytes, file_name=f"{file_name}.csv")
            else:
                xlsx_buffer = BytesIO()
                out.to_excel(xlsx_buffer, index=False, engine="openpyxl")
                xlsx_buffer.seek(0)
                st.download_button("⬇️ Download Excel", data=xlsx_buffer, file_name=f"{file_name}.xlsx")

with col2:
    st.markdown("### ℹ️ **WorldClim Data Info**")
    st.markdown("""
    **Historical climate data**

    This is WorldClim version 2.1 climate data for **1970–2000**. Released in January 2020.

    Available variables:
    - Minimum, mean, and maximum **temperature**
    - **Precipitation**
    - **Solar radiation**, **wind speed**, **water vapor pressure**
    - 19 **bioclimatic variables**

    Each dataset comes as a ZIP file containing 12 GeoTIFFs, one for each **month**.
    For `"bio"` variables, a single ZIP contains 19 layers.

    Available spatial resolutions:
    - 30 seconds (~1 km²)
    - 2.5, 5, and 10 arc-minutes (~5–340 km²)

    **Citation**:
    > Fick, S.E. and R.J. Hijmans, 2017. *WorldClim 2: new 1km spatial resolution climate surfaces for global land areas*. Int. J. of Climatology 37 (12): 4302–4315.
    """)

    st.markdown("### 📥 Input File Format")
    st.markdown("""
    Upload an Excel or CSV file with at least two columns:
    - One for **Longitude**
    - One for **Latitude**

    Example:

    | Species Name        | Longitude | Latitude |
    |---------------------|-----------|----------|
    | *...... ....*       | 18.425556 | 43.7125  |
    | *...... ....*       | 18.406944 | 43.7219  |

    ### 🪟 Pixel window (odd integer ≥ 1)

    Choose:
    - **1** (or leave blank): Extract the **exact pixel value** at each coordinate (no averaging).
    - **3, 5, 7, …**: Compute the **mean of an N × N window** centered on each point (e.g. 3×3 focal mean) — useful to reduce local noise or capture neighbourhood gradient.

    If you don't need the mean, just set it to **1** and the app will retrieve the **raw raster value** directly.

    """)


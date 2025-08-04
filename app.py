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
st.markdown(
    """
    <style>
      /* bacground image */
      .stApp {
        background-image: url("https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57723/globe_east_2048.jpg");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
      }

      /* white bacground for description */
      .info-box {
        background-color: rgba(255, 255, 255, 0.90);
        padding: 1.5rem;
        border-radius: 0.375rem;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
      }

      /* ~~~ source link */
      .image-credit {
        position: fixed;
        bottom: 1rem;
        right: 1rem;
        font-size: 0.75rem;
        color: rgba(255, 255, 255, 0.87);
        text-shadow: 0 0 2px rgba(0, 0, 0, 0.8);
        z-index: 1000;
      }

      .image-credit a {
        color: inherit;
        text-decoration: none;
      }
      .image-credit a:hover {
        text-decoration: underline;
      }
    </style>

    <!-- overlay credit link -->
    <div class="image-credit">
      <a href="https://visibleearth.nasa.gov/images/57723/the-blue-marble" target="_blank">
        Photo: NASA/GSFC – Blue Marble 2002
      </a>
    </div>
    """,
    unsafe_allow_html=True,
)

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
    st.markdown("""
    <div class="info-box">
    ### ℹ️ **WorldClim Data Info**

    **Historical climate data**

    This app allows you to extract historical climate data from the **WorldClim v2.1** (Released in January 2020) dataset  
    for the period **1970–2000**.
    You don't need to download or unzip anything manually — the data is streamed remotely. ✅

    **Supported variables:**
    - 🌡️ Temperature: `tmin`, `tmax`, `tavg`
    - ☀️ Solar radiation: `srad`
    - 🌬️ Wind speed: `wind`
    - 💧 Water vapor pressure: `vapr`
    - ☔ Precipitation: `prec`
    - 🌱 Bioclimatic variables: `bio` (19 derived layers)
    - 🏔️ Elevation: `elev`

    **Spatial resolution options:**
    - `30s` (≈1 km²), `2.5m`, `5m`, `10m` (arc-minutes, ≈5–340 km²)

    Each dataset comes as a ZIP file containing 12 GeoTIFFs, one for each **month**.
    For `"bio"` variables, a single ZIP contains 19 layers.

    **Citation**:
    > Fick, S.E. and R.J. Hijmans, 2017. *WorldClim 2: new 1km spatial resolution climate surfaces for global land areas*. Int. J. of Climatology 37 (12): 4302–4315.

    ---
    ### 📥 **How to use the app**
    1. Upload a **CSV or Excel** file with at least two columns:  
       **Longitude** and **Latitude** 

    Example:

    | Species Name        | Longitude | Latitude |
    |---------------------|-----------|----------|
    | *...... ....*       | 18.425556 | 43.7125  |
    | *...... ....*       | 18.406944 | 43.7219  |
    
    2. Choose the climate **variable**, **resolution**, and optionally a **pixel window**  
   (for smoothing or averaging — see below).

    3. Select the **output format**: either **CSV** or **Excel (XLSX)**.

    4. Click **Run extraction** ▶️ to fetch the data remotely.

    5. Once extraction is complete, a **Download** button will appear for your chosen format.

    ### 🪟 **Pixel window (optional)**

    You can smooth the data by averaging values around each point:

    - **Set to 1** *(default)* to return the **exact pixel value** (no averaging).
    - **Set to 3, 5, 7, …** *(odd integers)* to return the **mean value over an N×N area**  
      centered at each coordinate — useful for reducing local noise.

    For example, a 3×3 window averages the 9 pixels surrounding your point.
    
    ℹ️ If you don't need the mean, just set it to **1** and the app will retrieve the **raw raster value** directly.
    </div>
    """,
    unsafe_allow_html=True)


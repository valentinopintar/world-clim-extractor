# 🌍 WorldClim Extractor App

This app allows users to extract climate variables (e.g., temperature, precipitation, bioclimatic indices) from **WorldClim 2.1** datasets directly from `.zip` archives, without downloading or unzipping them manually.

📌 Features:
- Upload your own CSV or Excel file with coordinates
- Select climate variable (`tmin`, `tmax`, `prec`, `bio`, etc.)
- Choose spatial resolution (`30s`, `2.5m`, `5m`, `10m`)
- Download extracted values in CSV or Excel format

🔗 **Live App:**  
👉 [https://world-clim-extractor.streamlit.app/](https://world-clim-extractor.streamlit.app/)

---

## 🔧 Technical Details

- Built with [Streamlit](https://streamlit.io/)
- Uses [Rasterio](https://rasterio.readthedocs.io/) to read `.tif` files within `.zip` archives via `/vsizip/vsicurl`
- Downloads data directly from the [WorldClim data server](https://geodata.ucdavis.edu/climate/worldclim/2_1/)

---

## 📂 Example Input

| Longitude | Latitude |
|-----------|----------|
| 15.98     | 45.81    |
| 17.00     | 43.50    |

---

## 📦 Installation (optional, for local development)

```bash
pip install -r requirements.txt
streamlit run app.py

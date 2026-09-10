# PVGIS 100-case scientific validation

## Streamlit

```bash
pip install -r requirements.txt
streamlit run pvgis_100case_validation_app.py
```

## Command line

```bash
python run_pvgis_100case_validation.py --start-year 2014 --end-year 2023
```

Outputs are written to `pvgis_100case_results/`, including CSV tables, JSON statistics and 300-dpi PNG figures.

See `PVGIS_100CASE_VALIDATION.md` for methodology.

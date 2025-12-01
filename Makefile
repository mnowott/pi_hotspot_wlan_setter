.PHONY: run_app
run_app: poetry run streamlit run src/hotspot_connection_setter/app.py --server.port 80 --server.address 0.0.0.0
create_venv:
ifeq ("$(wildcard ./venv/bin/activate)","")
	python3 -m venv venv;
endif
venv_dependencies:
	. venv/bin/activate; pip install -r requirements.txt;
run:
	@(PORT=$(or $(PORT), 5000);\
	HOST=$(or $(HOST), 0.0.0.0);\
	. venv/bin/activate; uvicorn main:app --host $${HOST} --port $${PORT} --log-config logging.yaml) 
deploy: create_venv venv_dependencies run

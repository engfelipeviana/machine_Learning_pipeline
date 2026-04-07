.PHONY: setup build up open-browsers start down clean reload-api

setup: build up

build:
	@echo "Construindo Imagens Master para Workers DinD do Airflow..."
	docker compose build builder-data-worker
	docker compose build builder-mlops-worker

up:
	@echo "Inicializando toda a nuvem da infraestrutura (Detached)..."
	docker compose up -d

open-browsers:
	@echo "Aguardar serviços iniciar, boot (15 segundos)..."
	sleep 15
	@echo "Abrindo URLs no navegador..."
	xdg-open "http://localhost:8088" || true
	xdg-open "http://localhost:9001" || true
	xdg-open "http://localhost:5000" || true
	xdg-open "http://localhost:8000/docs" || true
	xdg-open "http://localhost:8888" || true

start: build up open-browsers
	@echo "Ecossistema ativado com sucesso. Plataformas abertas!"

down:
	@echo "Desligando ecossistema de containers..."
	docker compose down

clean:
	@echo "Destruindo infraestrutura, redes orfãs e volumes de dados vitais..."
	docker compose down -v --remove-orphans

reload-api:
	@echo "Simulando Zero-Downtime Deploy: reiniciando o servidor FastAPI para recarregar o novo modelo Champion..."
	docker compose restart fastapi-server

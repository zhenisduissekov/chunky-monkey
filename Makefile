.PHONY: venv install run test-utils test-scraper clean reset

# Create a Python virtual environment in ./venv
venv:
	python3 -m venv venv

# Install dependencies into the venv
install: venv
	. venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

# Run the main orchestrator using the venv
run:
	. venv/bin/activate && PYTHONPATH=. python src/main.py

# Test the utils module
test-utils:
	. venv/bin/activate && python src/utils.py

# Test the uploader (uploads Markdown files to OpenAI Vector Store)
test-upload:
	. venv/bin/activate && python src/uploader.py

# Test the scraper module
test-scraper:
	. venv/bin/activate && python src/scraper.py

# Remove venv, __pycache__, and generated files (teardown)
clean:
	rm -rf venv __pycache__ src/__pycache__ articles/*.md logs/*

# Destroy everything (venv, cache, generated files) WITHOUT reinstalling dependencies
destroy:
	rm -rf venv __pycache__ src/__pycache__ articles/*.md logs/*

# Clean and reinstall everything from scratch
reset: clean install

# Remove all uploaded files and vector stores from OpenAI (development reset)
reset-openai:
	. venv/bin/activate && python src/openai_cleanup.py

# Full reset: local and OpenAI cleanup
reset-all: reset reset-openai

# Run all Python tests with pytest
test:
	. venv/bin/activate && PYTHONPATH=. pytest

# Build Docker image (native architecture)
docker-build:
	docker build -t chunky-monkey .

# Build Docker image for linux/amd64 (for cloud platforms like DigitalOcean)
docker-build-linux:
	docker build --platform linux/amd64 -t chunky-monkey .

# Run the app in Docker (requires .env in project root)
docker-run:
	docker run --rm --env-file .env chunky-monkey

# Remove chunky-monkey Docker image and any stopped containers
docker-reset:
	-docker rm $$(docker ps -a -q --filter ancestor=chunky-monkey) 2>/dev/null || true
	-docker rmi chunky-monkey 2>/dev/null || true

# Stop and remove all containers and the image for chunky-monkey
docker-stop:
	-docker rm -f $$(docker ps -a -q --filter ancestor=chunky-monkey) 2>/dev/null || true
	-docker rmi chunky-monkey 2>/dev/null || true

# Stop any running Python jobs (local, not Docker)
stop:
	-pkill -f "python src/main.py" 2>/dev/null || true

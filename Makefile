install:
	pip install -r requirements-dev.txt

test:
	pytest

coverage:
	pytest --cov=src

lint:
	flake8 src

format:
	black src

sort:
	isort src

build:
	sam build

deploy:
	sam deploy

local:
	sam local start-api

validate:
	sam validate
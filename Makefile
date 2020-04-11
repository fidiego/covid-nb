.DEFAULT_GOAL := help
OPEN=$(word 1, $(wildcard /usr/bin/xdg-open /usr/bin/open))
GIT_HEAD=$(shell git rev-parse --short HEAD)
GIT_BRANCH=$(shell git rev-parse --abbrev-ref HEAD)
DATE=$(shell date)

.PHONY: help
help: ## Print the help message
	@awk 'BEGIN {FS = ":.*?## "} /^[0-9a-zA-Z_-]+:.*?## / {printf "\033[36m%s\033[0m : %s\n", $$1, $$2}' $(MAKEFILE_LIST) | \
		sort | \
		column -s ':' -t

.PHONY: install
install: ## install python dependencies - includes dev dependencies
	@pipenv install --dev

.PHONY: run
run:   ## run in development mode: requires dev dependencies
	@export GIT_HEAD=$(GIT_HEAD) && export GIT_BRANCH=$(GIT_BRANCH) && pipenv run jupyter notebook

.PHONY: build
build:   ## build the docker containers
	@export GIT_HEAD=$(GIT_HEAD) && export GIT_BRANCH=$(GIT_BRANCH)                 && \
		pipenv run jupyter nbconvert --to notebook --inplace --execute  *.ipynb && \
		pipenv run python gen_html.py    && \
		git add .                        && \
		git commit -m 'updated: $(DATE)' && \
		git push

.PHONY: lint
lint: ## lint the codebase
	@export PYTHONDONTWRITEBYTECODE=1 && pipenv run flake8 . --statistics --count

.PHONY: version
version: ## print git version info
	@echo 'GIT_HEAD='$(GIT_HEAD) && echo 'GIT_BRANCH='$(GIT_BRANCH)

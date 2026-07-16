# Default to CPU if not specified
FLAVOR ?= cpu

# Define behavior based on the flavor
ifeq ($(FLAVOR),cpu)
TORCH_GROUP := cpu
else ifeq ($(FLAVOR),gpu)
TORCH_GROUP := gpu
else
$(error Unsupported FLAVOR $(FLAVOR), must be 'cpu' or 'gpu')
endif

install-tools: ## Install required utilities/tools
	@command -v pdm > /dev/null || { echo >&2 "pdm is not installed. Installing..."; pip3.12 install --no-cache-dir --upgrade pip pdm; }

pdm-lock-check: ## Check that the pdm.lock file is in a good shape
	pdm lock --check --group cpu --lockfile pdm.lock.cpu
	pdm lock --check --group gpu --lockfile pdm.lock.gpu

install-deps: install-tools pdm-lock-check ## Install all required dependencies, according to pdm.lock
	pdm sync --group $(TORCH_GROUP) --lockfile pdm.lock.$(TORCH_GROUP)

install-deps-test: install-tools pdm-lock-check ## Install all required dev dependencies, according to pdm.lock
	pdm sync --dev --group $(TORCH_GROUP) --lockfile pdm.lock.$(TORCH_GROUP)

update-deps: ## Check pyproject.toml for changes, update the lock file if needed, then sync.
	pdm update --update-all --group $(TORCH_GROUP) --lockfile pdm.lock.$(TORCH_GROUP)
	pdm update --update-all --dev --group $(TORCH_GROUP) --lockfile pdm.lock.$(TORCH_GROUP)
	pdm export --group $(TORCH_GROUP) --lockfile pdm.lock.$(TORCH_GROUP) -o requirements.$(TORCH_GROUP).txt

check-types: ## Checks type hints in sources
	mypy --explicit-package-bases --disallow-untyped-calls --disallow-untyped-defs --disallow-incomplete-defs scripts

format: ## Format the code into unified format
	black scripts
	ruff check scripts --fix --per-file-ignores=scripts/*:S101

verify: ## Verify the code using various linters
	black --check scripts
	ruff check scripts --per-file-ignores=scripts/*:S101

update-docs: ## Update the plaintext OCP docs in ocp-product-docs-plaintext/
	@set -e && for OCP_VERSION in $$(ls -1 ocp-product-docs-plaintext); do \
		scripts/get_ocp_plaintext_docs.sh $$OCP_VERSION; \
	done
	scripts/get_runbooks.sh

update-model: ## Update the local copy of the embedding model
	@rm -rf ./embeddings_model
	@python scripts/download_embeddings_model.py -l ./embeddings_model -r sentence-transformers/all-mpnet-base-v2

# Pick the registry from the branch (Prow sets PULL_BASE_REF); fall back to the
# current git branch for local runs. release* -> quay.io/triliodata,
# feature* -> quay.io/triliovault, everything else (master/main) -> eu.gcr.io.
PULL_BASE_REF ?= $(shell git rev-parse --abbrev-ref HEAD)
REGISTRY ?= $(shell case "$(PULL_BASE_REF)" in \
	release*) echo "quay.io/triliodata" ;; \
	feature*) echo "quay.io/triliovault" ;; \
	*) echo "eu.gcr.io/amazing-chalice-243510" ;; \
	esac)
IMAGE_NAME ?= tvk-lightspeed-rag-content
# Tag by branch: main/master -> master, feature* -> branch name,
# release* -> git tag, everything else (e.g. PR presubmits) -> PR head SHA.
IMAGE_TAG ?= $(shell case "$(PULL_BASE_REF)" in \
	main|master) echo "master" ;; \
	feature*) echo "$(PULL_BASE_REF)" ;; \
	release*) git describe --tags 2>/dev/null || git rev-parse --short HEAD ;; \
	*) echo "$(PULL_PULL_SHA)" ;; \
	esac)
IMAGE := $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

build-image: ## Build a linux/amd64 rag-content image tagged $(IMAGE).
	podman build --platform=linux/amd64 -t $(IMAGE) .

# Log in to the registry implied by $(REGISTRY). gcr.io uses the GCS service
# account (GOOGLE_APPLICATION_CREDENTIALS); quay orgs use the robot creds
# injected by the preset-quay-creds Prow preset.
registry-login: ## Log in to the registry selected by $(REGISTRY).
	@case "$(REGISTRY)" in \
		*gcr.io*) \
			echo "Logging in to gcr.io"; \
			docker login -u _json_key --password-stdin https://eu.gcr.io < "$${GOOGLE_APPLICATION_CREDENTIALS}" ;; \
		quay.io/triliovault) \
			echo "Logging in to quay.io/triliovault"; \
			echo "$${QUAY_STABLE_CI_PASSWORD}" | docker login -u "$${QUAY_STABLE_CI_USERNAME}" --password-stdin quay.io ;; \
		quay.io/triliodata) \
			echo "Logging in to quay.io/triliodata"; \
			echo "$${QUAY_STABLE_RELEASE_PASSWORD}" | docker login -u "$${QUAY_STABLE_RELEASE_USERNAME}" --password-stdin quay.io ;; \
		*) echo "No login configured for registry '$(REGISTRY)'" >&2; exit 1 ;; \
	esac

build-docker-image: registry-login
	docker buildx build --push --platform=linux/amd64 -t $(IMAGE) -f Containerfile

help: ## Show this help screen
	@echo 'Usage: make <OPTIONS> ... <TARGETS>'
	@echo ''
	@echo 'Available targets are:'
	@echo ''
	@grep -E '^[ a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ''

model-safetensors: ## Download model.safetensors to embeddings_model
	@if [ ! -f embeddings_model/model.safetensors ]; then \
		echo "Downloading model.safetensors..."; \
		wget "https://huggingface.co/sentence-transformers/all-mpnet-base-v2/resolve/9a3225965996d404b775526de6dbfe85d3368642/model.safetensors" -O embeddings_model/model.safetensors; \
	else \
		echo "model.safetensors already exists. Skipping download."; \
	fi

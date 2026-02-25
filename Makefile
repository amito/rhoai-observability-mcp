# Makefile for RHOAI Observability MCP Server

# =============================================================================
# Configuration
# =============================================================================

IMAGE_NAME ?= quay.io/rh-ee-amoren/rhoai-observability-mcp
IMAGE_TAG ?= latest
IMAGE := $(IMAGE_NAME):$(IMAGE_TAG)

# Container runtime detection (prefer podman)
CONTAINER_RUNTIME := $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)

# Build platform
PLATFORM ?= linux/amd64

# Deploy namespace
NAMESPACE ?= rhoai-obs-mcp

.PHONY: help build push deploy undeploy clean

# =============================================================================
# Help
# =============================================================================

help: ## Show this help message
	@echo "RHOAI Observability MCP Server"
	@echo ""
	@echo "Runtime: $(CONTAINER_RUNTIME)"
	@echo "Image:   $(IMAGE)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Container
# =============================================================================

build: ## Build the container image
	DOCKER_DEFAULT_PLATFORM=$(PLATFORM) $(CONTAINER_RUNTIME) build --platform=$(PLATFORM) -f Containerfile -t $(IMAGE) .

push: ## Push the container image to registry
	$(CONTAINER_RUNTIME) push $(IMAGE)

# =============================================================================
# OpenShift
# =============================================================================

deploy: ## Deploy to OpenShift (current namespace)
	oc apply -f deploy/

undeploy: ## Remove from OpenShift
	oc delete -f deploy/ --ignore-not-found

# =============================================================================
# Development
# =============================================================================

clean: ## Remove the container image
	-$(CONTAINER_RUNTIME) rmi $(IMAGE) 2>/dev/null || true

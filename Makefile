.PHONY: help dev-backend dev-frontend dev docker-build docker-push deploy install-openshift clean

REGISTRY ?= quay.io/your-registry
VERSION ?= latest
NAMESPACE ?= fleet-status

help:
	@echo "Fleet Status Dashboard - Available targets:"
	@echo "  make dev-backend      - Run backend in development mode"
	@echo "  make dev-frontend     - Run frontend in development mode"
	@echo "  make dev              - Run both backend and frontend"
	@echo "  make docker-build     - Build Docker images"
	@echo "  make docker-push      - Push Docker images to registry"
	@echo "  make deploy           - Deploy to OpenShift"
	@echo "  make install-openshift - Install from scratch on OpenShift"
	@echo "  make clean            - Remove build artifacts"

dev-backend:
	cd backend && python -m venv venv && \
	source venv/bin/activate && \
	pip install -r requirements.txt && \
	python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm install && npm run dev

dev:
	@echo "Starting backend and frontend..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo "Press Ctrl+C to stop both"
	@trap 'kill %1' EXIT; \
	(cd backend && python -m venv venv && source venv/bin/activate && \
	pip install -r requirements.txt && \
	python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000) & \
	(cd frontend && npm install && npm run dev) & \
	wait

docker-build:
	podman build -t $(REGISTRY)/fleet-status-backend:$(VERSION) ./backend
	podman build -t $(REGISTRY)/fleet-status-frontend:$(VERSION) ./frontend

docker-push:
	podman push $(REGISTRY)/fleet-status-backend:$(VERSION)
	podman push $(REGISTRY)/fleet-status-frontend:$(VERSION)

deploy:
	oc apply -f openshift/namespace.yaml
	oc apply -f openshift/configmap.yaml
	oc apply -f openshift/secret.yaml
	oc apply -f openshift/rbac.yaml
	oc apply -f openshift/backend-deployment.yaml
	oc apply -f openshift/frontend-deployment.yaml
	@echo "Waiting for deployments..."
	oc wait --for=condition=available --timeout=300s deployment/fleet-status-backend -n $(NAMESPACE)
	oc wait --for=condition=available --timeout=300s deployment/fleet-status-frontend -n $(NAMESPACE)
	@echo "Deployment complete!"
	@echo "Access dashboard at: https://$(shell oc get route fleet-status -n $(NAMESPACE) -o jsonpath='{.spec.host}' 2>/dev/null || echo 'route-pending')"

install-openshift: docker-build docker-push deploy

clean:
	rm -rf backend/venv backend/__pycache__ backend/.pytest_cache
	rm -rf frontend/node_modules frontend/.next
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

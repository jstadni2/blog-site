PYTHON ?= .venv/bin/python
PORT := 5010
E2E_BASE_URL := http://127.0.0.1:$(PORT)
E2E_ADMIN_USERNAME := e2e_admin
E2E_ADMIN_PASSWORD := e2e_password_123
E2E_ADMIN_PASSWORD_HASH := scrypt:32768:8:1$$zuPneWjIeelcktYR$$25169dcdf17b0512245540c5904c15938ff53fe55182b1af5c71524cf3afaba90348511c5b3d082644b9bdeaf87071f87abeb02506ed7c115debf29d1efe3ef7
E2E_DYNAMODB_TABLE_NAME := blog_posts_e2e
E2E_DYNAMODB_ENDPOINT_URL := http://127.0.0.1:8000
E2E_AWS_DEFAULT_REGION := us-east-1
E2E_AWS_ACCESS_KEY_ID := local
E2E_AWS_SECRET_ACCESS_KEY := local

.PHONY: e2e-server e2e-test

# Start the app with deterministic credentials used by the E2E suite.
e2e-server:
	FLASK_SKIP_DOTENV=1 \
	FLASK_APP=app.py \
	SECRET_KEY=e2e-secret-key \
	DYNAMODB_AUTO_INIT=1 \
	ADMIN_USERNAME=$(E2E_ADMIN_USERNAME) \
	ADMIN_PASSWORD_HASH='$(E2E_ADMIN_PASSWORD_HASH)' \
	DYNAMODB_TABLE_NAME=$(E2E_DYNAMODB_TABLE_NAME) \
	DYNAMODB_ENDPOINT_URL=$(E2E_DYNAMODB_ENDPOINT_URL) \
	AWS_DEFAULT_REGION=$(E2E_AWS_DEFAULT_REGION) \
	AWS_ACCESS_KEY_ID=$(E2E_AWS_ACCESS_KEY_ID) \
	AWS_SECRET_ACCESS_KEY=$(E2E_AWS_SECRET_ACCESS_KEY) \
	$(PYTHON) -m flask run --port $(PORT)

# Run Playwright + Pytest browser tests.
e2e-test:
	@set -e; \
	if ! lsof -iTCP:$(PORT) -sTCP:LISTEN >/dev/null 2>&1; then \
		echo "No server found on $(E2E_BASE_URL). Start it first with: make e2e-server" >&2; \
		exit 1; \
	fi; \
	if ! curl -fs $(E2E_BASE_URL)/admin/login >/dev/null 2>&1; then \
		echo "Server on $(E2E_BASE_URL) is not responding correctly at /admin/login" >&2; \
		exit 1; \
	fi; \
	if ! curl -sS -X POST $(E2E_BASE_URL)/admin/login \
		-H 'Content-Type: application/x-www-form-urlencoded' \
		--data 'username=$(E2E_ADMIN_USERNAME)&password=$(E2E_ADMIN_PASSWORD)' \
		-c /tmp/blog-site-e2e-cookie.txt \
		-D /tmp/blog-site-e2e-login-headers.txt \
		-o /dev/null; then \
		echo "Failed to submit admin login preflight request" >&2; \
		exit 1; \
	fi; \
	if ! grep -Eiq '^Location: .*/admin/?' /tmp/blog-site-e2e-login-headers.txt; then \
		echo "Preflight admin login did not redirect to dashboard. Ensure e2e-server is running from this Makefile with deterministic test credentials." >&2; \
		exit 1; \
	fi; \
	if ! curl -fs $(E2E_BASE_URL)/admin/ -b /tmp/blog-site-e2e-cookie.txt | grep -q 'Admin Dashboard'; then \
		echo "Preflight admin login failed. Ensure e2e-server is running from this Makefile with deterministic test credentials." >&2; \
		exit 1; \
	fi; \
	E2E_BASE_URL=$(E2E_BASE_URL) E2E_ADMIN_USERNAME=$(E2E_ADMIN_USERNAME) E2E_ADMIN_PASSWORD=$(E2E_ADMIN_PASSWORD) $(PYTHON) -m pytest -q tests/e2e

PYTHON ?= .venv/bin/python
PORT ?= 5010
E2E_ADMIN_USERNAME ?= e2e_admin
E2E_ADMIN_PASSWORD ?= e2e_password_123

.PHONY: e2e-server e2e-test

# Start the app with deterministic credentials used by the E2E suite.
e2e-server:
	FLASK_SKIP_DOTENV=1 \
	FLASK_APP=app.py \
	SECRET_KEY=e2e-secret-key \
	ADMIN_USERNAME=$(E2E_ADMIN_USERNAME) \
	ADMIN_PASSWORD_HASH="$$($(PYTHON) -c \"from werkzeug.security import generate_password_hash; print(generate_password_hash('$(E2E_ADMIN_PASSWORD)'))\")" \
	$(PYTHON) -m flask run --port $(PORT)

# Run Playwright + Pytest browser tests.
e2e-test:
	$(PYTHON) -m pytest -q tests/e2e

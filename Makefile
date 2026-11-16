# Genio OS — commandes uniques (المرحلة 7)
# كل الأمر خطوة وحدة، وبلا سحر: شوف الـ target قبل ما تشغّل.

PY ?= python3
# المسار يختار وحدو: داخل الريبو، ولا برّا الريبو إذا هو على noexec (sshfs)
# — التفاصيل في scripts/venv_path.sh. GENIO_VENV=/path يفرض مسار.
VENV ?= $(shell sh scripts/venv_path.sh)
# أسماء خاصة بجنبو باش ما تتضاربش مع متغيرات البيئة (PORT موجودة برشة)
GIO_HOST ?= 127.0.0.1
GIO_PORT ?= 8099

.PHONY: help venv install run test compile backup clean

help:
	@echo "make venv      — مسار الـ venv المستعمل ($(VENV))"
	@echo "make install   — إنشاء venv + تثبيت المتطلّبات"
	@echo "make run       — تشغيل المنصّة محليًا على $(GIO_HOST):$(GIO_PORT)"
	@echo "make test      — pytest (المجموعة كاملة)"
	@echo "make compile   — فحص syntax لكل الـ Python"
	@echo "make backup    — نسخة احتياطية للذاكرة والـ workspace والإعدادات"
	@echo "make clean     — حذف __pycache__ و .pytest_cache"

venv:
	@echo "$(VENV)"

install:
	@PYTHON="$(PY)" sh scripts/make_venv.sh "$(VENV)"

run:
	$(VENV)/bin/$(PY) -m uvicorn web.server:app --host $(GIO_HOST) --port $(GIO_PORT)

test:
	$(VENV)/bin/$(PY) -m pytest -q

compile:
	$(VENV)/bin/$(PY) -m compileall -q core web tests

backup:
	bash scripts/backup.sh

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf .pytest_cache

PROJECT=encyc-tng
USER=encyc
SHELL = /bin/bash

SRC_REPO=https://github.com/denshoproject/encyc-tng

INSTALL_BASE=/opt
INSTALLDIR=$(INSTALL_BASE)/encyc-tng
APPDIR=$(INSTALLDIR)/encyctng
REQUIREMENTS=$(INSTALLDIR)/requirements.txt
PIP_CACHE_DIR=$(INSTALL_BASE)/pip-cache

CWD := $(shell pwd)
INSTALL_STATIC=$(INSTALLDIR)/static

VIRTUALENV=$(INSTALLDIR)/venv/encyctng

CONF_BASE=/etc/encyc
CONF_PRODUCTION=$(CONF_BASE)/encyctng.cfg
CONF_LOCAL=$(CONF_BASE)/encyctng-local.cfg
CONF_SECRET=$(CONF_BASE)/encyctng-secret-key.txt

LOG_BASE=/var/log/encyc

MEDIA_BASE=/var/www/encyctng
MEDIA_ROOT=$(MEDIA_BASE)/media
STATIC_ROOT=$(MEDIA_BASE)/static

RUNSERVER_PORT=8082
SUPERVISOR_GUNICORN_CONF=/etc/supervisor/conf.d/encyctng.conf
NGINX_CONF=/etc/nginx/sites-available/encyctng.conf
NGINX_CONF_LINK=/etc/nginx/sites-enabled/encyctng.conf

# Release name e.g. jessie
DEBIAN_CODENAME := $(shell lsb_release -sc)
# Release numbers e.g. 8.10
DEBIAN_RELEASE := $(shell lsb_release -sr)
# Sortable major version tag e.g. deb8
DEBIAN_RELEASE_TAG = deb$(shell lsb_release -sr | cut -c1)

PYTHON_VERSION=
ifeq ($(DEBIAN_CODENAME), bookworm)
	PYTHON_VERSION=3.11.2
endif
ifeq ($(DEBIAN_CODENAME), trixie)
	PYTHON_VERSION=3.11.6
endif


.PHONY: help

help:
	@echo "encyc-tng Install Helper (see Makefile for more commands)"
	@echo ""
	@echo "install   - Does a complete install. Idempotent, so run as many times as you like."
	@echo "          IMPORTANT: Run 'adduser encyc' first to install encycddr user and group."
	@echo "shell     - Becomes the encyc user and runs a Python shell."
	@echo "runserver - Becomes the encyc user and runs the web application."
	@echo "uninstall - Deletes 'compiled' Python files. Leaves build dirs and configs."
	@echo "clean     - Deletes files created by building the program. Leaves configs."
	@echo ""


install: get-app install-app install-configs install-static

update: update-app

uninstall: uninstall-app

clean: clean-app

install-daemons: install-nginx install-redis install-supervisor

remove-daemons: remove-nginx remove-redis remove-supervisor

install-nginx:
	@echo ""
	@echo "Nginx ------------------------------------------------------------------"
	apt-get --assume-yes install nginx

remove-nginx:
	apt-get --assume-yes remove nginx

install-redis:
	@echo ""
	@echo "Redis ------------------------------------------------------------------"
	apt-get --assume-yes install redis-server

remove-redis:
	apt-get --assume-yes remove redis-server

install-supervisor:
	@echo ""
	@echo "Supervisor -------------------------------------------------------------"
	apt-get --assume-yes install supervisor

remove-supervisor:
	apt-get --assume-yes remove supervisor


install-virtualenv:
	@echo ""
	@echo "install-virtualenv -----------------------------------------------------"
	apt-get --assume-yes install python3-pip python3-venv
	source $(VIRTUALENV)/bin/activate; \
	pip3 install -U --cache-dir=$(PIP_CACHE_DIR) uv
	uv venv $(VIRTUALENV)

install-setuptools: install-virtualenv
	@echo ""
	@echo "install-setuptools -----------------------------------------------------"
	apt-get --assume-yes install python-dev
	source $(VIRTUALENV)/bin/activate; \
	uv pip install -U --cache-dir=$(PIP_CACHE_DIR) setuptools


get-app: get-encyc-tng

install-app: install-encyc-tng

uninstall-app: uninstall-encyc-tng

clean-app: clean-encyc-tng


get-encyc-tng:
	@echo ""
	@echo "get-encyc-tng -----------------------------------------------------"
	git pull

install-encyc-tng: install-virtualenv install-setuptools git-safe-dir install-redis
	@echo ""
	@echo "install encyc-tng -------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	uv pip install -U -r $(INSTALLDIR)/requirements.txt
	source $(VIRTUALENV)/bin/activate; \
	cd $(APPDIR)/ && python setup.py install
# logs dir
	-mkdir $(LOG_BASE)
	chown -R encyc.root $(LOG_BASE)
	chmod -R 755 $(LOG_BASE)
# static dir
	-mkdir -p $(STATIC_ROOT)
	chown -R encyc.root $(STATIC_ROOT)
	chmod -R 755 $(STATIC_ROOT)
# media dir
	-mkdir -p $(MEDIA_ROOT)
	chown -R encyc.root $(MEDIA_BASE)
	chmod -R 755 $(MEDIA_BASE)

git-safe-dir:
	@echo ""
	@echo "git-safe-dir -----------------------------------------------------------"
	sudo -u encyc git config --global --add safe.directory $(INSTALLDIR)

shell:
	source $(VIRTUALENV)/bin/activate; \
	python $(APPDIR)/manage.py shell

runserver:
	source $(VIRTUALENV)/bin/activate; \
	python $(APPDIR)/manage.py runserver 0.0.0.0:$(RUNSERVER_PORT)

uninstall-encyc-tng:
	cd $(APPDIR)
	source $(VIRTUALENV)/bin/activate; \
	-pip uninstall -r $(INSTALLDIR)/requirements.txt

clean-encyc-tng:
	-rm -Rf $(INSTALLDIR)/venv/
	-rm -Rf $(APPDIR)/build
	-rm -Rf $(APPDIR)/*.egg-info
	-rm -Rf $(APPDIR)/dist


clean-pip:
	-rm -Rf $(PIP_CACHE_DIR)/*


install-configs:
	@echo ""
	@echo "installing configs ----------------------------------------------------"
	-mkdir $(CONF_BASE)
	python -c 'import random; print "".join([random.choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)") for i in range(50)])' > $(CONF_SECRET)
	chown encyc.encyc $(CONF_SECRET)
	chmod 640 $(CONF_SECRET)
# web app settings
	cp $(INSTALLDIR)/conf/encyctng.cfg $(CONF_BASE)
	chown root.encyc $(CONF_PRODUCTION)
	chmod 640 $(CONF_PRODUCTION)
	touch $(CONF_LOCAL)
	chown root.encyc $(CONF_LOCAL)
	chmod 640 $(CONF_LOCAL)

uninstall-configs:
	-rm $(CONF_PRODUCTION)
	-rm $(CONF_LOCAL)
	-rm $(CONF_SECRET)

install-daemons-configs:
	@echo ""
	@echo "configuring daemons -------------------------------------------------"
# nginx
	cp $(INSTALLDIR)/conf/nginx.conf $(NGINX_CONF)
	chown root.root $(NGINX_CONF)
	chmod 644 $(NGINX_CONF)
	-ln -s $(NGINX_CONF) $(NGINX_CONF_LINK)
# supervisord
	cp $(INSTALLDIR)/conf/supervisor.conf $(SUPERVISOR_GUNICORN_CONF)
	chown root.root $(SUPERVISOR_GUNICORN_CONF)
	chmod 644 $(SUPERVISOR_GUNICORN_CONF)

uninstall-daemons-configs:
	-rm $(NGINX_CONF_LINK)
	-rm $(NGINX_CONF)
	-rm $(SUPERVISOR_GUNICORN_CONF)


install-static: collectstatic

collectstatic:
	@echo ""
	@echo "collectstatic -------------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	python $(APPDIR)/manage.py collectstatic --noinput

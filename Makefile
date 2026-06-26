PROJECT=encyc-tng
APP=encyctng
USER=encyc
SHELL = /bin/bash

APP_VERSION := $(shell cat VERSION)

SRC_REPO=https://github.com/denshoproject/encyc-tng
SRC_REPO_ASSETS=https://github.com/denshoproject/encyc-tng-assets.git
SRC_REPO_NVM=https://github.com/nvm-sh/nvm.git
SRC_REPO_VOCAB=https://github.com/denshoproject/densho-vocab.git

INSTALL_BASE=/opt
INSTALLDIR=$(INSTALL_BASE)/encyc-tng
INSTALL_ASSETS=/opt/encyc-tng-assets
APPDIR=$(INSTALLDIR)/encyctng
REQUIREMENTS=$(INSTALLDIR)/requirements.txt
PIP_CACHE_DIR=$(INSTALL_BASE)/pip-cache

CWD := $(shell pwd)
INSTALL_STATIC=$(INSTALLDIR)/static
INSTALL_NVM=$(INSTALLDIR)/.nvm
INSTALL_VOCAB=/opt/densho-vocab

VIRTUALENV=$(INSTALLDIR)/.venv

CONF_BASE=/etc/encyc
CONF_PRODUCTION=$(CONF_BASE)/encyctng.cfg
CONF_LOCAL=$(CONF_BASE)/encyctng-local.cfg
CONF_SECRET=$(CONF_BASE)/encyctng-secret-key.txt

LOG_BASE=/var/log/encyctng

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
	PYTHON_VERSION=3.13
endif

TGZ_BRANCH := $(shell python3 bin/package-branch.py)
TGZ_FILE=$(APP)_$(APP_VERSION)
TGZ_DIR=$(INSTALLDIR)/$(TGZ_FILE)
TGZ_TNG=$(TGZ_DIR)/encyc-tng

# Adding '-rcN' to VERSION will name the package "encyctng-release"
# instead of "encytng-BRANCH"
DEB_BRANCH := $(shell python3 bin/package-branch.py)
DEB_ARCH=amd64
DEB_NAME_TRIXIE=$(APP)-$(DEB_BRANCH)
# Application version, separator (~), Debian release tag e.g. deb8
# Release tag used because sortable and follows Debian project usage.
DEB_VERSION_TRIXIE=$(APP_VERSION)~deb13
DEB_FILE_TRIXIE=$(DEB_NAME_TRIXIE)_$(DEB_VERSION_TRIXIE)_$(DEB_ARCH).deb
DEB_VENDOR=Densho.org
DEB_MAINTAINER=<geoffrey.jost@densho.org>
DEB_DESCRIPTION=Densho Encyclopedia
DEB_BASE=opt/encyc-tng


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
	apt-get install --assume-yes extrepo
	extrepo enable uv
	apt-get install --assume-yes uv
	uv venv --relocatable --managed-python --allow-existing --python /usr/bin/python3

install-nodejs:
	@echo ""
	@echo "install-nodejs --------------------------------------------------------"
	if test -d $(INSTALL_NVM); \
	then cd $(INSTALL_NVM) && git pull; \
	else git clone $(SRC_REPO_NVM) $(INSTALL_NVM); \
	fi
	source $(INSTALL_NVM)/nvm.sh; nvm install
	source $(INSTALL_NVM)/nvm.sh; npm install


get-densho-vocab:
	@echo ""
	@echo "get-densho-vocab -------------------------------------------------------"
	if test -d $(INSTALL_VOCAB); \
	then cd $(INSTALL_VOCAB) && git pull; \
	else git clone $(SRC_REPO_VOCAB) $(INSTALL_VOCAB); \
	fi


get-app: get-encyc-tng get-encyc-tng-assets get-densho-vocab

install-app: install-encyc-tng

install-testing: install-encyc-tng-testing

uninstall-app: uninstall-encyc-tng

clean-app: clean-encyc-tng


get-encyc-tng: git-safe-dir
	@echo ""
	@echo "get-encyc-tng -----------------------------------------------------"
	git pull

get-encyc-tng-assets:
	@echo ""
	@echo "get-encyc-tng-assets --------------------------------------------------"
	if test -d $(INSTALL_ASSETS); \
	then cd $(INSTALL_ASSETS) && git pull; \
	else cd $(INSTALL_BASE) && git clone $(SRC_REPO_ASSETS); \
	fi

setup-encyc-tng:
	source $(VIRTUALENV)/bin/activate; uv sync

install-pyproject: install-virtualenv
	@echo ""
	@echo "install pyproject -------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; uv sync

install-encyc-tng: git-safe-dir install-encyc-tng-dirs install-configs install-redis install-pyproject npm-build
	@echo ""
	@echo "install encyc-tng -------------------------------------------------"
	apt-get install --assume-yes ffmpeg

install-encyc-tng-dirs:
	@echo ""
	@echo "install encyc-tng-dirs --------------------------------------------"
# logs dir
	-mkdir -p $(LOG_BASE)
	chown -R encyc:root $(LOG_BASE)
	chmod -R 755 $(LOG_BASE)
	-mkdir -p $(MEDIA_BASE)
# static dir
	ln -sf $(INSTALL_ASSETS)/static $(INSTALLDIR)/static
	ln -sf $(INSTALLDIR)/static $(STATIC_ROOT)
# media dir
	-mkdir -p $(MEDIA_ROOT)
	chown -R encyc:root $(MEDIA_BASE)
	chmod -R 755 $(MEDIA_BASE)

install-migration:
	@echo ""
	@echo "install migration -------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; uv pip install .[migration]

install-encyc-tng-testing:
	@echo ""
	@echo "install encyc-tng -------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; uv pip install .[testing]
	npm install -g pa11y-ci

git-safe-dir:
	@echo ""
	@echo "git-safe-dir -----------------------------------------------------------"
	sudo -u encyc git config --global --add safe.directory $(INSTALLDIR)
	sudo -u encyc git config --global --add safe.directory $(INSTALL_ASSETS)
	sudo -u encyc git config --global --add safe.directory $(INSTALL_VOCAB)

shell:
	source $(VIRTUALENV)/bin/activate; \
	python $(APPDIR)/manage.py shell

runserver:
	source $(VIRTUALENV)/bin/activate; \
	python $(APPDIR)/manage.py runserver 0.0.0.0:$(RUNSERVER_PORT)

migrate:
	source $(VIRTUALENV)/bin/activate; \
	python $(APPDIR)/manage.py migrate

uninstall-encyc-tng:
	cd $(APPDIR)
	source $(VIRTUALENV)/bin/activate; \
	-pip uninstall -r $(INSTALLDIR)/requirements.txt

clean-encyc-tng:
	source $(VIRTUALENV)/bin/activate; pyclean .
	-rm -Rf $(INSTALLDIR)/*.egg-info
	-rm -Rf $(INSTALLDIR)/.nvm/
	-rm -Rf $(INSTALLDIR)/build/
	-rm -Rf $(INSTALLDIR)/node_modules/
	-rm -Rf $(INSTALLDIR)/.venv/
	-rm -Rf $(INSTALLDIR)/venv/
	-rm -Rf $(APPDIR)/build/
	-rm -Rf $(APPDIR)/*.egg-info
	-rm -Rf $(APPDIR)/dist/
	-rm -Rf $(APPDIR)/static_compiled/

clean-pip:
	-rm -Rf $(PIP_CACHE_DIR)/*


install-configs:
	@echo ""
	@echo "installing configs ----------------------------------------------------"
	-mkdir -p $(CONF_BASE)
	python3 -c 'import random; print("".join([random.choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)") for i in range(50)]))' > $(CONF_SECRET)
	chown encyc:encyc $(CONF_SECRET)
	chmod 640 $(CONF_SECRET)
# web app settings
	cp $(INSTALLDIR)/conf/encyctng.cfg $(CONF_BASE)
	chown root:encyc $(CONF_PRODUCTION)
	chmod 640 $(CONF_PRODUCTION)
	touch $(CONF_LOCAL)
	chown root:encyc $(CONF_LOCAL)
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
	chown root:root $(NGINX_CONF)
	chmod 644 $(NGINX_CONF)
	-ln -s $(NGINX_CONF) $(NGINX_CONF_LINK)
# supervisord
	cp $(INSTALLDIR)/conf/supervisor.conf $(SUPERVISOR_GUNICORN_CONF)
	chown root:root $(SUPERVISOR_GUNICORN_CONF)
	chmod 644 $(SUPERVISOR_GUNICORN_CONF)

uninstall-daemons-configs:
	-rm $(NGINX_CONF_LINK)
	-rm $(NGINX_CONF)
	-rm $(SUPERVISOR_GUNICORN_CONF)


npm-build: install-nodejs collectstatic
	@echo ""
	@echo "npm-build -----------------------------------------------------------"
	source $(INSTALL_NVM)/nvm.sh; npm run build:prod

install-static: collectstatic

collectstatic: install-pyproject
	@echo ""
	@echo "collectstatic -------------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	python $(APPDIR)/manage.py collectstatic --noinput


test-encyc-tng-django:
	@echo ""
	@echo "test-encyc-tng ----------------------------------------"
	source $(VIRTUALENV)/bin/activate; cd $(INSTALLDIR); pytest --disable-warnings encyctng

test-encyc-tng-pa11y:
	@echo ""
	@echo "test-encyc-tng-accessibility ----------------------------------------"
	cd $(INSTALLDIR); pa11y-ci --config pa11y.config.js


tgz-local:
	rm -Rf $(TGZ_DIR)
	git clone $(INSTALLDIR) $(TGZ_TNG)
	git clone $(INSTALL_ASSETS) $(TGZ_ASSETS)
	cd $(TGZ_TNG); git checkout develop; git checkout master
	cd $(TGZ_ASSETS); git checkout develop; git checkout master
	tar czf $(TGZ_FILE).tgz $(TGZ_FILE)
	rm -Rf $(TGZ_DIR)


tgz:
	rm -Rf $(TGZ_DIR)
	git clone $(SRC_REPO) $(TGZ_TNG)
	git clone $(SRC_REPO_ASSETS) $(TGZ_ASSETS)
	cd $(TGZ_TNG); git checkout develop; git checkout master
	cd $(TGZ_ASSETS); git checkout develop; git checkout master
	tar czf $(TGZ_FILE).tgz $(TGZ_FILE)
	rm -Rf $(TGZ_DIR)

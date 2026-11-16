################################################################################
# BASE                                                                         #
################################################################################
FROM python:3.14-slim-trixie AS base

ARG POETRY_VERSION=1.8.3
ARG UID=1000
ARG GID=1000

RUN apt-get update -yqq && apt-get install -yqq --no-install-recommends \
  curl

# Where python should look for packages and modules when using import
ENV PYTHONPATH="/app"

# Ensure the stdout and stderr streams are sent straight to terminal
ENV PYTHONUNBUFFERED=1 

# Extend the socket timeout. Default would be 15s
ENV  PIP_DEFAULT_TIMEOUT=100 

RUN groupadd -g ${GID} -o app
RUN useradd -m -d /app -u ${UID} -g ${GID} -o -s /bin/bash app

# RUN apt-get update -yqq && apt-get install -yqq --no-install-recommends \
#   vim-tiny

WORKDIR /app

CMD ["tail", "-f", "/dev/null"]

################################################################################
# POETRY
################################################################################
#
# Both BUILD and DEVELOPMENT need poetry
# 
FROM base AS poetry

RUN pip install poetry==${POETRY_VERSION}

# Ensure that the virtual environment directory is in the project. This path
# will be be `/app/.venv/`
ENV  POETRY_VIRTUALENVS_IN_PROJECT=1 

# Create the virtual environment if it does not already exist
ENV  POETRY_VIRTUALENVS_CREATE=1 

################################################################################
# BUILD                                                                        #
################################################################################
#
# This step uses poetry to generate a requirements.txt file for PRODUCTION
#
FROM poetry AS build

# README.md is needed so that poetry command will work.
COPY pyproject.toml poetry.lock README.md ./

RUN poetry export --without dev -f requirements.txt --output requirements.txt

################################################################################
# DEVELOPMENT                                                                  #
################################################################################
#
# In development we want poetry in the container, so it inherits from the POETRY
# step.  This step is the place to install development-only sytem dependencies
#
FROM poetry AS development

RUN apt-get update -yqq && apt-get install -yqq --no-install-recommends \
  boxes

USER app

################################################################################
# PRODUCTION                                                                   #
################################################################################
FROM base AS production

# Setting this to 'off' actually turns off the cache. This is set to decrease
# the size of the image.
ENV  PIP_NO_CACHE_DIR=off 

# Speed up pip usage by not checking for the version
ENV  PIP_DISABLE_PIP_VERSION_CHECK=on 

COPY --chown=${UID}:${GID} . /app
COPY --chown=${UID}:${GID} --from=build "/app/requirements.txt" /app/requirements.txt

RUN pip install -r /app/requirements.txt

USER app

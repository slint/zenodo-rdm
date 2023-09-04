# Dockerfile that builds a fully functional image of your app.
#
# This image installs all Python dependencies for your application. It's based
# on Almalinux (https://github.com/inveniosoftware/docker-invenio)
# and includes Pip, Pipenv, Node.js, NPM and some few standard libraries
# Invenio usually needs.
#
# Note: It is important to keep the commands in this file in sync with your
# bootstrap script located in ./scripts/bootstrap.
FROM registry.cern.ch/inveniosoftware/almalinux:1

# Python dependencies
COPY Pipfile Pipfile.lock ./
COPY ./legacy ./legacy
RUN pipenv install --deploy --system --pre

# npm dependencies for assets
COPY package.json package-lock.json ${INVENIO_INSTANCE_PATH}/assets/
RUN npm install --prefix ${INVENIO_INSTANCE_PATH}/assets/

# Install Zenodo site code package
COPY ./site ./site
RUN pip install ./site
COPY ./ .

# Configuration, fixtures, templates, translations
COPY ./invenio.cfg ${INVENIO_INSTANCE_PATH}
COPY ./docker/uwsgi/ ${INVENIO_INSTANCE_PATH}
COPY ./templates/ ${INVENIO_INSTANCE_PATH}/templates/
COPY ./app_data/ ${INVENIO_INSTANCE_PATH}/app_data/
COPY ./translations ${INVENIO_INSTANCE_PATH}/translations

# Build assets
RUN cp -r ./static/. ${INVENIO_INSTANCE_PATH}/static/ && \
    cp -r ./assets/. ${INVENIO_INSTANCE_PATH}/assets/ && \
    invenio collect --verbose  && \
    invenio webpack create build

ENTRYPOINT [ "bash", "-l"]

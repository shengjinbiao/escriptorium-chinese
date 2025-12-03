FROM docker.io/library/node:12-alpine as frontend

WORKDIR /build
COPY ./front /build
RUN npm ci && npm run production

# Pull official base image
FROM registry.gitlab.com/scripta/escriptorium/base:dj-solo

# try to autodetect number of cpus available
# ENV NGINX_WORKER_PROCESSES auto

ARG VERSION_DATE="2025-08-28"
ENV VERSION_DATE=$VERSION_DATE
ENV FRONTEND_DIR=/usr/src/app/front
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# set work directory
WORKDIR /usr/src/app

# Install a Java 17 runtime for Spark/Passim alignment jobs.
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends openjdk-17-jre-headless openjdk-17-jdk && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    JAVA_HOME=$(dirname $(dirname $(readlink -f /usr/bin/java))) && \
    ln -sfn "${JAVA_HOME}" /opt/java-home
ENV JAVA_HOME=/opt/java-home
ENV PATH="${JAVA_HOME}/bin:${PATH}"

COPY ./app/entrypoint.sh /usr/src/app/entrypoint.sh
COPY ./app/manage.py /usr/src/app/manage.py
COPY ./app/requirements.txt /usr/src/app/requirements.txt
COPY ./app/uwsgi.ini /usr/src/app/uwsgi.ini

COPY ./app/apps /usr/src/app/apps
COPY ./app/escriptorium /usr/src/app/escriptorium
COPY ./app/locale /usr/src/app/locale
COPY ./app/homepage /usr/src/app/homepage
COPY ./app/contributors /usr/src/app/contributors
COPY --from=frontend /build/dist /usr/src/app/front

# run entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]

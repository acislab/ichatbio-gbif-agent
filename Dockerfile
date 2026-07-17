FROM ubuntu:24.04

RUN apt-get update -y \
      && apt-get install -y \
      python3-pip \
      python3.12-venv \
      pipx

ENV PATH="/root/.local/bin:$PATH"
RUN pipx install uv
RUN cp /root/.local/bin/uv /usr/local/bin/uv

RUN adduser --disabled-password nonroot
RUN mkdir /home/app && chown -R nonroot:nonroot /home/app
RUN mkdir -p /var/log/flask-app \
      && touch /var/log/flask-app/flask-app.err.log \
      && touch /var/log/flask-app/flask-app.out.log \
      && chown -R nonroot:nonroot /var/log/flask-app
RUN mkdir -p /home/app/logs && chown -R nonroot:nonroot /home/app/logs

WORKDIR /home/app

# Download GADM database
RUN apt-get update && apt-get install -y wget unzip \
      && mkdir -p src/gadm \
      && wget -O /tmp/gadm.zip https://geodata.ucdavis.edu/gadm/gadm4.1/gadm_410-gpkg.zip \
      && unzip /tmp/gadm.zip -d /tmp/gadm \
      && mv /tmp/gadm/*.gpkg src/gadm/gadm.gpkg \
      && rm -rf /tmp/gadm.zip /tmp/gadm \
      && chown -R nonroot:nonroot src/gadm

COPY --chown=nonroot:nonroot . .

USER nonroot

ENV VIRTUAL_ENV=/home/app/venv
ENV PATH="$VIRTUAL_ENV/bin:/usr/local/bin:$PATH"

RUN python3 -m venv $VIRTUAL_ENV
RUN uv pip install --no-cache --python $VIRTUAL_ENV/bin/python -e .
EXPOSE 9999

CMD ["python3", "-m", "src"]

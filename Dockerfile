ARG PYTHON_VERSION=3.12

FROM python:$PYTHON_VERSION-slim AS build

ENV PYTHONUNBUFFERED=1

WORKDIR /code

ARG XRAY_VERSION=v26.7.11

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl unzip gcc python3-dev libpq-dev \
    && ARCH=$(case "$(dpkg --print-architecture)" in amd64) echo "64";; arm64) echo "arm64-v8a";; armhf) echo "arm32-v7a";; i386) echo "32";; *) echo "64";; esac) \
    && curl -L -o /tmp/xray.zip "https://github.com/XTLS/Xray-core/releases/download/${XRAY_VERSION}/Xray-linux-${ARCH}.zip" \
    && unzip /tmp/xray.zip -d /tmp/xray \
    && mv /tmp/xray/xray /usr/local/bin/xray \
    && chmod +x /usr/local/bin/xray \
    && mkdir -p /usr/local/share/xray \
    && [ -f /tmp/xray/geoip.dat ] && mv /tmp/xray/geoip.dat /usr/local/share/xray/ || true \
    && [ -f /tmp/xray/geosite.dat ] && mv /tmp/xray/geosite.dat /usr/local/share/xray/ || true \
    && rm -rf /tmp/xray /tmp/xray.zip \
    && xray version \
    && rm -rf /var/lib/apt/lists/* \
    && echo "Downloading Russian geobase..." \
    && curl -L -o /tmp/geoip_RU.dat "https://raw.githubusercontent.com/runetfreedom/russia-v2ray-rules-dat/release/geoip.dat" \
    && curl -L -o /tmp/geosite_RU.dat "https://raw.githubusercontent.com/runetfreedom/russia-v2ray-rules-dat/release/geosite.dat" \
    && mv /tmp/geoip_RU.dat /usr/local/share/xray/geoip_RU.dat \
    && mv /tmp/geosite_RU.dat /usr/local/share/xray/geosite_RU.dat \
    && echo "Downloading custom geobase..." \
    && curl -L -o /tmp/geoip_custom.dat "https://iplist.opencck.org/?format=geoip&data=cidr4&native=1&group=ai&group=anime&group=art&group=discord&group=education&group=finance&group=games&group=hosting&group=jetbrains&group=messengers&group=music&group=news&group=porn&group=shop&group=socials&group=tools&group=torrent&group=video&group=youtube" \
    && curl -L -o /tmp/geosite_custom.dat "https://iplist.opencck.org/?format=geosite&data=domains&wildcard=1&group=ai&group=anime&group=art&group=discord&group=education&group=finance&group=games&group=hosting&group=jetbrains&group=messengers&group=music&group=news&group=porn&group=shop&group=socials&group=tools&group=torrent&group=video&group=youtube" \
    && mv /tmp/geoip_custom.dat /usr/local/share/xray/geoip_custom.dat \
    && mv /tmp/geosite_custom.dat /usr/local/share/xray/geosite_custom.dat \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /code/
RUN python3 -m pip install --upgrade pip "setuptools<71" \
    && pip install --no-cache-dir --upgrade -r /code/requirements.txt

FROM python:$PYTHON_VERSION-slim

ENV PYTHON_LIB_PATH=/usr/local/lib/python${PYTHON_VERSION%.*}/site-packages
WORKDIR /code

RUN rm -rf $PYTHON_LIB_PATH/*

COPY --from=build $PYTHON_LIB_PATH $PYTHON_LIB_PATH
COPY --from=build /usr/local/bin /usr/local/bin
COPY --from=build /usr/local/share/xray /usr/local/share/xray

COPY . /code

RUN ln -s /code/marzban-cli.py /usr/bin/marzban-cli \
    && chmod +x /usr/bin/marzban-cli \
    && marzban-cli completion install --shell bash

CMD ["bash", "-c", "alembic upgrade head; python main.py"]

FROM debian:stable-slim

# Install common OS-level dependencies
RUN <<EOF
    apt-get --quiet --yes update
    apt-get --quiet --yes install --no-install-recommends \
        build-essential \
        libpq-dev \
        git \
        lsb-release \
        make \
        sudo \
        ca-certificates \
        curl
EOF

ARG UID=1000
ARG GID=1000
ARG USERNAME=encyc
RUN <<EOF
    # Create the unprivileged user and group. If you have issues with file
    # ownership, you may need to adjust the UID and GID build args to match your
    # local user.
    groupadd --gid $GID $USERNAME
    useradd --gid $GID --uid $UID --create-home -G sudo $USERNAME
EOF


RUN mkdir -p /opt/encyc-tng && chown -R $UID:$GID /opt/encyc-tng && git config --global --add safe.directory /opt/encyc-tng
WORKDIR /opt/encyc-tng

RUN git clone --quiet https://github.com/denshoproject/encyc-core /opt/encyc-core && git -C /opt/encyc-core tag wagtail

COPY --chown=encyc . .

RUN mkdir /etc/encyc && ln -s $PWD/conf/encyctng-local-docker.cfg /etc/encyc/encyctng-local.cfg

RUN make get-app
RUN make install-app
RUN make install-configs

RUN make install-static

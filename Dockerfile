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

# Create the config directory and copy the config files
RUN mkdir -p /etc/encyc && \
    cp conf/encyctng.cfg /etc/encyc/core.cfg && \
    cp conf/encyctng-local-docker.cfg /etc/encyc/core-local.cfg && \
    chown -R $UID:$GID /etc/encyc

# Create log directory with proper permissions
RUN mkdir -p /opt/encyc-tng/log && \
    chown -R $UID:$GID /opt/encyc-tng/log && \
    chmod 755 /opt/encyc-tng/log

RUN make git-safe-dir
RUN make install-app
RUN make install-configs

RUN make install-static

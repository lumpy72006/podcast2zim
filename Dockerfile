# Build frontend
FROM node:24-alpine AS zimui

WORKDIR /src/zimui
COPY zimui/package.json zimui/yarn.lock ./
RUN yarn install --frozen-lockfile
COPY zimui/ .
RUN yarn build

# Build the scraper
FROM python:3.14-trixie
LABEL "org.opencontainers.image.source"="https://github.com/lumpy72006/podcast2zim"

# Install necessary dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    wget \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir -U \
    pip

RUN mkdir -p /output
WORKDIR /output

# copy pyproject.toml and its dependencies
COPY README.md /src/
COPY scraper/pyproject.toml /src/scraper/
COPY scraper/src/podcast2zim/__about__.py /src/scraper/src/podcast2zim/__about__.py

# install dependencies
RUN pip install --no-cache-dir /src/scraper/

# copy code
COPY scraper/src /src/scraper/src

# copy zimui build output
COPY --from=zimui /src/scraper/src/podcast2zim/zimui /src/scraper/src/podcast2zim/zimui

# copy associated artifacts
COPY *.md LICENSE /src/ 

# install + cleanup
RUN pip install --no-cache-dir /src/scraper \
    && rm -rf /src/scraper

ENTRYPOINT ["podcast2zim"]
CMD ["--help"]

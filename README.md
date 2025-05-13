# Terminus Env Metrics Exporter

A Prometheus exporter that collects site environment metrics from Pantheon site via Terminus
and exposes them for monitoring.

## TL;DR

This tool turns [this](https://docs.pantheon.io/terminus/commands/env-metrics):

```bash
terminus env:metrics my-pantheon-site.live --format=json --period=day --datapoints=1
{
    "timeseries": {
        "xxxxxxxxx": {
            "datetime": "2025-05-11T00:00:00",
            "visits": xxx,
            "pages_served": xxx,
            "cache_hits": xxx,
            "cache_misses": xxx,
            "cache_hit_ratio": "xx.xx%"
        }
    }
}
```

into this:

```
# HELP terminus_env_visits Number of visits
# TYPE terminus_env_visits gauge
terminus_env_visits{env="live",site="my-pantheon-site"} xxx
# HELP terminus_env_pages_served Pages served
# TYPE terminus_env_pages_served gauge
terminus_env_pages_served{env="live",site="my-pantheon-site"} xxx
# HELP terminus_env_cache_hits Cache hits
# TYPE terminus_env_cache_hits gauge
terminus_env_cache_hits{env="live",site="my-pantheon-site"} xxx
# HELP terminus_env_cache_misses Cache misses
# TYPE terminus_env_cache_misses gauge
terminus_env_cache_misses{env="live",site="my-pantheon-site"} xxx
# HELP terminus_env_cache_hit_ratio Cache hit ratio (percent)
# TYPE terminus_env_cache_hit_ratio gauge
terminus_env_cache_hit_ratio{env="live",site="my-pantheon-site"} xx.xx
```

It uses [Terminus](https://docs.pantheon.io/terminus/install) so if you plan to use
this tool without Docker you'll need to install `Terminus` first.

## Features

- Gathers metrics like visits, pages served, cache hits/misses, and cache hit ratio.
- Exposes metrics over HTTP for Prometheus to scrape.
- Configurable via YAML config file.
- Supports debug logging with `-d` flag.

## Requirements

- Python 3.7+
- [Terminus CLI](https://docs.pantheon.io/terminus)
- [Pantheon Machine token](https://docs.pantheon.io/machine-tokens) for Terminus authentication

## Local Installation (without Docker)

1. Clone this repo:

    ```bash
    git clone https://github.com/dunterov/terminus-env-metrics-exporter.git
    cd terminus-env-metrics-exporter
    ```

2. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Docker build

This is the recommended way as this project includes `Dockerimage` with all dependencies included.
To build the image run the following command:

```bash
docker build -t terminus-env-metrics-exporter:latest .
```

## Config Example (.config.yaml)

```yaml
port: 9114
interval: 60
token: <your-terminus-machine-token>
sites:
  - site: example-site
    env: live
  - site: another-site
    env: dev
```

Alternatively, the token can be supplied via the `MACHINE_TOKEN` environment variable.

## Usage

```bash
Prometheus exporter for Terminus env:metrics

Usage:
  terminus_env_metrics_exporter.py [-c <config_file>] [-d]
  terminus_env_metrics_exporter.py (-h | --help)

Options:
  -c <config_file>     Path to config file [default: .config.yaml]
  -d                   Enable verbose output (DEBUG level)
  -h --help            Show this help message.
```

The application can be executed with Docker as shown below:

```bash
docker run -v `pwd`/.config.yaml:/app/.config.yaml -p 9114:9114 terminus-env-metrics-exporter:latest
```

or (if Pantheon machine token is provided over environment variable)

```bash
export MACHINE_TOKEN=<PUT TOKEN HERE>
docker run -v `pwd`/.config.yaml:/app/.config.yaml -p 9114:9114 -e MACHINE_TOKEN=${MACHINE_TOKEN} terminus-env-metrics-exporter:latest
```

## Prometheus Configuration
Add this target to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'terminus_exporter'
    static_configs:
      - targets: ['localhost:9114']
```

The underlying command, `terminus env:metrics` provides data for previous day only so
it makes sense to set scrape interval as high as possible.

## Exported Metrics

- `terminus_env_visits`
- `terminus_env_pages_served`
- `terminus_env_cache_hits`
- `terminus_env_cache_misses`
- `terminus_env_cache_hit_ratio`

Each metric is labeled with `site` and `env`.

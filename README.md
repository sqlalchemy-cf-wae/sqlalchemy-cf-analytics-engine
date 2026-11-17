# sqlalchemy-cf-analytics-engine

A read-only DBAPI driver and SQLAlchemy dialect for
[Cloudflare Workers Analytics Engine](https://developers.cloudflare.com/analytics/analytics-engine/).
It lets SQLAlchemy-based tools, such as Apache Superset and pandas, query
Analytics Engine datasets through Cloudflare's SQL API.

> **Status:** early development. The driver and dialect are not implemented yet.

## Connection string

```
cfwae://{account_id}:{api_token}@
```

The API token needs the **Account Analytics: Read** permission. Requests always
go to Cloudflare's API; the host part of the URI is ignored.

## Sampled data

Analytics Engine may store only a sample of the data points written to it. Each
stored row has a `_sample_interval` column saying how many data points it
represents, so aggregate with it instead of counting rows:

| You want | Write |
|---|---|
| Number of events | `SUM(_sample_interval)` |
| Sum of `double1` | `SUM(_sample_interval * double1)` |
| Average of `double1` | `SUM(_sample_interval * double1) / SUM(_sample_interval)` |

## Development

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pytest
```

## License

Apache License 2.0. See [LICENSE](LICENSE).

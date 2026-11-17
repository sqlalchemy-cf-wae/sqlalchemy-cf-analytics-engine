#!/usr/bin/env bash
# Run every query the driver, dialect and engine spec depend on, and save each
# raw reply to tests/fixtures/responses/<name>.txt (body, then the HTTP code).
# Review the files before committing them.
set -euo pipefail

cd "$(dirname "$0")"
OUT=../../tests/fixtures/responses
mkdir -p "$OUT"

DS=cfwae_demo

probe() {
  local name=$1 sql=$2
  echo "== $name"
  ./query.sh "$sql" > "$OUT/$name.txt" || true
  tail -1 "$OUT/$name.txt"
}

# Discovery
probe show_tables              "SHOW TABLES FORMAT JSON"
probe describe_table           "DESCRIBE $DS FORMAT JSON"

# Plain results and type names in "meta"
probe select_all_columns       "SELECT * FROM $DS ORDER BY timestamp DESC LIMIT 3 FORMAT JSON"
probe select_zero_rows         "SELECT blob1 FROM $DS WHERE blob1 = 'no-such-path' FORMAT JSON"
probe format_default           "SELECT blob1, double1 FROM $DS LIMIT 2"

# What Superset will generate
probe time_grain_hour          "SELECT toStartOfInterval(timestamp, INTERVAL '1' HOUR) AS hour, SUM(_sample_interval) AS requests FROM $DS GROUP BY hour ORDER BY hour FORMAT JSON"
probe time_grain_day           "SELECT toStartOfInterval(timestamp, INTERVAL '1' DAY) AS day, SUM(_sample_interval) AS requests FROM $DS GROUP BY day ORDER BY day FORMAT JSON"
probe to_datetime_filter       "SELECT count() AS n FROM $DS WHERE timestamp >= toDateTime('2026-01-01 00:00:00') FORMAT JSON"
probe to_date_filter           "SELECT count() AS n FROM $DS WHERE timestamp >= toDate('2026-01-01') FORMAT JSON"
probe to_datetime_date_only    "SELECT count() AS n FROM $DS WHERE timestamp >= toDateTime('2026-01-01') FORMAT JSON"
probe now_minus_interval       "SELECT count() AS n FROM $DS WHERE timestamp > NOW() - INTERVAL '1' DAY FORMAT JSON"
probe like_filter              "SELECT count() AS n FROM $DS WHERE blob5 LIKE 'O%' FORMAT JSON"
probe limit_offset             "SELECT blob1, timestamp FROM $DS ORDER BY timestamp LIMIT 2 OFFSET 1 FORMAT JSON"
probe order_by_unselected      "SELECT blob1 FROM $DS ORDER BY timestamp LIMIT 2 FORMAT JSON"
probe subquery_alias           "SELECT path FROM (SELECT blob1 AS path FROM $DS) AS virtual_table LIMIT 1 FORMAT JSON"
probe table_alias              "SELECT x.blob1 FROM $DS x LIMIT 1 FORMAT JSON"
probe quoted_identifier        "SELECT \"blob1\" FROM \"$DS\" LIMIT 1 FORMAT JSON"
probe backtick_identifier      "SELECT \`blob1\` FROM \`$DS\` LIMIT 1 FORMAT JSON"
probe subquery                 "SELECT path, n FROM (SELECT blob1 AS path, SUM(_sample_interval) AS n FROM $DS GROUP BY path) ORDER BY n DESC LIMIT 3 FORMAT JSON"
probe join                     "SELECT a.blob1 FROM $DS AS a JOIN $DS AS b ON a.blob1 = b.blob1 LIMIT 1 FORMAT JSON"
probe quoted_value_backslash   "SELECT count() AS n FROM $DS WHERE blob5 = 'O\\'Malley' FORMAT JSON"
probe quoted_value_doubled     "SELECT count() AS n FROM $DS WHERE blob5 = 'O''Malley' FORMAT JSON"
probe trailing_semicolon       "SELECT 1 AS one FORMAT JSON;"
probe leading_comment          "-- tag
SELECT 1 AS one FORMAT JSON"

# Errors
probe error_unknown_table      "SELECT * FROM no_such_dataset FORMAT JSON"
probe error_unknown_column     "SELECT no_such_column FROM $DS FORMAT JSON"
probe error_bad_sql            "SELEC 1"
probe error_write              "INSERT INTO $DS (blob1) VALUES ('x')"

echo "Saved to tests/fixtures/responses/"

"""Optional BigQuery path. Never required to run FirstSign.

Two things live here:
  * `load_history`: export the daily counts (pin x group x day) to a BigQuery table.
  * `forecast_baselines`: ask BigQuery's AI.FORECAST (TimesFM) for the expected units per pin and group,
    so the baseline can come from a learned forecast instead of the local weekday-aware median.

Run `python -m app.bq` from backend/ with GOOGLE_CLOUD_PROJECT set and `google-cloud-bigquery` installed to load
the history and print the forecast next to the local baseline. The live API computes its baseline locally
(SIGNAL_BACKEND is reported by /api/health); this module is the documented upgrade path, not a runtime dependency.

Status: written against the documented AI.FORECAST table-function syntax; it was not executed in the
development environment (no BigQuery project was attached), so treat it as a reviewed design, not a tested path.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

log = logging.getLogger("firstsign.bq")

HISTORY_TABLE = "daily_counts"


def _client(project: str) -> Any:
    from google.cloud import bigquery  # lazy: optional dependency

    return bigquery.Client(project=project)


def load_history(project: str, dataset: str, history: pd.DataFrame, location: str = "asia-south1") -> str:
    """Create the dataset if needed and load history (date, pin, group, units, chemists_ordering). Returns the table id."""
    from google.cloud import bigquery

    client = _client(project)
    dataset_ref = bigquery.Dataset(f"{project}.{dataset}")
    dataset_ref.location = location
    client.create_dataset(dataset_ref, exists_ok=True)
    table_id = f"{project}.{dataset}.{HISTORY_TABLE}"
    frame = history.assign(date=pd.to_datetime(history["date"]).dt.date)
    job = client.load_table_from_dataframe(
        frame, table_id, job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    )
    job.result()
    log.info("loaded %d rows into %s", len(frame), table_id)
    return table_id


def forecast_sql(project: str, dataset: str, horizon: int = 7) -> str:
    """AI.FORECAST over the daily table, one series per (pin, group_id), trained on days before the last 7."""
    table = f"`{project}.{dataset}.{HISTORY_TABLE}`"
    return f"""
SELECT pin, `group` AS group_id, forecast_timestamp AS date, forecast_value AS baseline
FROM AI.FORECAST(
  (SELECT TIMESTAMP(date) AS ts, pin, `group`, units
   FROM {table}
   WHERE date <= DATE_SUB((SELECT MAX(date) FROM {table}), INTERVAL 7 DAY)),
  data_col => 'units',
  timestamp_col => 'ts',
  id_cols => ['pin', 'group'],
  horizon => {horizon}
)
""".strip()


def forecast_baselines(project: str, dataset: str, horizon: int = 7) -> pd.DataFrame:
    """Run the forecast and return a frame with columns pin, group_id, date, baseline."""
    client = _client(project)
    frame = client.query(forecast_sql(project, dataset, horizon)).to_dataframe()
    frame["date"] = pd.to_datetime(frame["date"]).dt.tz_localize(None).dt.normalize()
    return frame


if __name__ == "__main__":
    import sys

    from .config import Settings
    from .store import Reference

    cfg = Settings.from_env()
    ref = Reference.load(cfg.data_dir)
    print("loading", load_history(cfg.google_cloud_project, cfg.bq_dataset, ref.history, cfg.google_cloud_region))
    print(forecast_baselines(cfg.google_cloud_project, cfg.bq_dataset).head(20).to_string())
    sys.exit(0)

"""Analysis engine: computes pricing metrics from fetched DataFrames."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from omaha.core.config.schema import OntologyObjectConfig, RootConfig

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    object_name: str
    metrics: dict[str, Any]
    summary: str


def compute_price_metrics(df: pd.DataFrame, price_column: str) -> dict[str, float]:
    """Compute min/max/mean/median/std/count for *price_column* in *df*.

    Raises:
        KeyError: if *price_column* is not in *df*.
        ValueError: if the column contains non-numeric data.
    """
    series = df[price_column]  # raises KeyError if missing

    if not pd.api.types.is_numeric_dtype(series):
        raise ValueError(
            f"Price column '{price_column}' contains non-numeric data; "
            "cannot compute price metrics."
        )

    if series.empty:
        logger.debug("Empty DataFrame for column '%s'; returning zero metrics.", price_column)
        return {"min": 0, "max": 0, "mean": 0, "median": 0, "std": 0, "count": 0}

    return {
        "min": float(series.min()),
        "max": float(series.max()),
        "mean": float(series.mean()),
        "median": float(series.median()),
        "std": float(series.std(ddof=0)),
        "count": int(series.count()),
    }


def analyze_object(obj: OntologyObjectConfig, df: pd.DataFrame) -> AnalysisResult:
    """Analyse a single ontology object and return an :class:`AnalysisResult`.

    Raises:
        ValueError: if no price/cost property is found on *obj*.
    """
    price_prop = next(
        (p for p in obj.properties if "price" in p.name.lower() or "cost" in p.name.lower()),
        None,
    )
    if price_prop is None:
        raise ValueError(
            f"Object '{obj.name}' has no property whose name contains 'price' or 'cost'."
        )

    logger.info("Analysing object '%s' using column '%s'.", obj.name, price_prop.column)
    metrics = compute_price_metrics(df, price_prop.column)

    summary = (
        f"{obj.name}: {metrics['count']} records - "
        f"mean={metrics['mean']:.2f}, min={metrics['min']:.2f}, max={metrics['max']:.2f}"
    )
    return AnalysisResult(object_name=obj.name, metrics=metrics, summary=summary)


def run_analysis(
    config: RootConfig, data: dict[str, pd.DataFrame]
) -> list[AnalysisResult]:
    """Run analysis for every object in *config* that has a corresponding DataFrame."""
    results: list[AnalysisResult] = []
    for obj in config.ontology.objects:
        if obj.name not in data:
            logger.debug("No data for object '%s'; skipping.", obj.name)
            continue
        logger.info("Running analysis for object '%s'.", obj.name)
        try:
            result = analyze_object(obj, data[obj.name])
        except ValueError as exc:
            logger.warning("Skipping object '%s': %s", obj.name, exc)
            continue
        results.append(result)
    return results

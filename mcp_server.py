"""MCP server exposing safe CSV analysis tools."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from mcp.server.fastmcp import FastMCP

from tools import DatasetTools

mcp = FastMCP("data-analyst-agent")

DEFAULT_CSV = Path(__file__).parent / "data" / "sales.csv"
_df: pd.DataFrame | None = None
_tools: DatasetTools | None = None


def _get_tools() -> DatasetTools:
    global _df, _tools
    if _tools is None:
        _df = pd.read_csv(DEFAULT_CSV)
        _tools = DatasetTools(_df, charts_dir=Path("results/charts"))
    return _tools


@mcp.tool()
def get_schema() -> str:
    """Return column names, dtypes, row count, and sample values."""
    return json.dumps(_get_tools().get_schema(), indent=2)


@mcp.tool()
def group_and_aggregate(
    group_by: list[str],
    metric_column: str,
    agg: str = "sum",
) -> str:
    """Group by columns and compute an aggregate metric."""
    result = _get_tools().group_and_aggregate(group_by, metric_column, agg)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def top_n(column: str, n: int = 5, group_by: str | None = None) -> str:
    """Return top N rows ranked by a numeric column."""
    kwargs = {"column": column, "n": n}
    if group_by:
        kwargs["group_by"] = group_by
    result = _get_tools().top_n(**kwargs)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def make_chart(
    chart_type: str,
    x_column: str,
    y_column: str,
    title: str,
    group_by: str | None = None,
    agg: str = "sum",
) -> str:
    """Create a bar or line chart and return the saved file path."""
    kwargs = {
        "chart_type": chart_type,
        "x_column": x_column,
        "y_column": y_column,
        "title": title,
        "agg": agg,
    }
    if group_by:
        kwargs["group_by"] = group_by
    result = _get_tools().make_chart(**kwargs)
    return json.dumps(result, indent=2)


@mcp.tool()
def compare_periods(
    date_column: str,
    metric_column: str,
    period_a_start: str,
    period_a_end: str,
    period_b_start: str,
    period_b_end: str,
    group_by: str | None = None,
) -> str:
    """Compare a metric between two date ranges."""
    kwargs = {
        "date_column": date_column,
        "metric_column": metric_column,
        "period_a_start": period_a_start,
        "period_a_end": period_a_end,
        "period_b_start": period_b_start,
        "period_b_end": period_b_end,
    }
    if group_by:
        kwargs["group_by"] = group_by
    result = _get_tools().compare_periods(**kwargs)
    return json.dumps(result, indent=2, default=str)


if __name__ == "__main__":
    mcp.run()

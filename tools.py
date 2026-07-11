"""Safe CSV analysis tools — no arbitrary code execution."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Allowed columns and operators — validation layer for prompt-injection defense
ALLOWED_OPERATORS = {"eq", "ne", "gt", "gte", "lt", "lte", "contains"}
ALLOWED_AGGS = {"sum", "mean", "count", "min", "max", "median"}
CHART_AGGS = {"sum", "mean", "count"}
MAX_FILTER_PREVIEW = 10
MAX_TOP_N = 50
OUTLIER_IQR_MULTIPLIER = 1.5

# Strip injection patterns from string inputs
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"system\s*:",
    r"<\s*/?\s*script",
    r"execute\s+code",
    r"run\s+python",
    r"__import__",
    r"os\.system",
    r"subprocess",
]


def sanitize_string(value: str) -> str:
    """Remove common prompt-injection phrases from user-supplied strings."""
    cleaned = value
    for pattern in INJECTION_PATTERNS:
        cleaned = re.sub(pattern, "[filtered]", cleaned, flags=re.IGNORECASE)
    return cleaned[:500]


def json_safe(obj: Any) -> Any:
    """Recursively convert pandas/numpy types to JSON-serializable Python types."""
    if isinstance(obj, dict):
        return {json_safe_key(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, pd.Timedelta):
        return str(obj)
    if isinstance(obj, pd.Period):
        return str(obj)
    if isinstance(obj, np.datetime64):
        return str(obj)
    if isinstance(obj, np.timedelta64):
        return str(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        val = float(obj)
        return None if np.isnan(val) else val
    if isinstance(obj, np.bool_):
        return bool(obj)
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    try:
        if pd.isna(obj):
            return None
    except (ValueError, TypeError):
        pass
    if hasattr(obj, "item"):
        return json_safe(obj.item())
    return str(obj)


def json_safe_key(key: Any) -> str | int | float | bool | None:
    """Convert any dict key to a JSON-compatible type."""
    if key is None or isinstance(key, bool):
        return key
    if isinstance(key, int) and not isinstance(key, bool):
        return key
    if isinstance(key, float):
        return key
    if isinstance(key, str):
        return key
    return str(key)


def safe_json_dumps(obj: Any) -> str:
    """Serialize tool results to JSON without Timestamp/numpy errors."""
    import json

    return json.dumps(json_safe(obj))


def df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert DataFrame rows to JSON-safe records."""
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%d")
        elif out[col].map(lambda v: isinstance(v, (pd.Timestamp, pd.Period))).any():
            out[col] = out[col].astype(str)
    return json_safe(out.to_dict(orient="records"))


def validate_column(df: pd.DataFrame, column: str) -> str:
    if column not in df.columns:
        raise ValueError(f"Unknown column '{column}'. Available: {list(df.columns)}")
    return column


def validate_columns(df: pd.DataFrame, columns: list[str]) -> list[str]:
    return [validate_column(df, col) for col in columns]


class DatasetTools:
    """Executes safe, validated operations on a pandas DataFrame."""

    def __init__(self, df: pd.DataFrame, charts_dir: Path | None = None):
        self.df = df.copy()
        self.charts_dir = charts_dir or Path("results/charts")
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        self._parse_dates()

    def _parse_dates(self) -> None:
        for col in self.df.columns:
            if "date" in col.lower():
                try:
                    self.df[col] = pd.to_datetime(self.df[col])
                except (ValueError, TypeError):
                    pass

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        handlers = {
            "get_schema": self.get_schema,
            "profile_dataset": self.profile_dataset,
            "describe_column": self.describe_column,
            "filter_rows": self.filter_rows,
            "group_and_aggregate": self.group_and_aggregate,
            "top_n": self.top_n,
            "compare_periods": self.compare_periods,
            "make_chart": self.make_chart,
        }
        if tool_name not in handlers:
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            result = handlers[tool_name](**arguments)
            return json_safe(result)
        except (ValueError, KeyError, TypeError) as exc:
            return {"error": str(exc)}

    def get_schema(self) -> dict[str, Any]:
        columns = []
        for col in self.df.columns:
            sample = self.df[col].dropna().head(3).tolist()
            columns.append(
                {
                    "name": col,
                    "dtype": str(self.df[col].dtype),
                    "null_count": int(self.df[col].isna().sum()),
                    "sample_values": [str(v) for v in sample],
                }
            )
        return {"row_count": len(self.df), "columns": columns}

    def profile_dataset(self) -> dict[str, Any]:
        numeric = self.df.select_dtypes(include=[np.number])
        categorical = self.df.select_dtypes(exclude=[np.number])

        profile: dict[str, Any] = {
            "numeric_summary": json_safe(numeric.describe().to_dict()) if not numeric.empty else {},
            "categorical_counts": {},
        }
        for col in categorical.columns:
            profile["categorical_counts"][col] = json_safe(
                self.df[col].value_counts().head(10).to_dict()
            )
        return profile

    def describe_column(self, column: str) -> dict[str, Any]:
        column = validate_column(self.df, sanitize_string(column))
        series = self.df[column]
        result: dict[str, Any] = {
            "column": column,
            "dtype": str(series.dtype),
            "null_count": int(series.isna().sum()),
            "unique_count": int(series.nunique()),
        }
        if pd.api.types.is_numeric_dtype(series):
            desc = series.describe()
            result["stats"] = {k: float(v) for k, v in desc.items()}
            q1, q3 = series.quantile(0.25), series.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - OUTLIER_IQR_MULTIPLIER * iqr
            upper = q3 + OUTLIER_IQR_MULTIPLIER * iqr
            outliers = series[(series < lower) | (series > upper)]
            result["outliers"] = {
                "count": int(len(outliers)),
                "lower_bound": float(lower),
                "upper_bound": float(upper),
                "sample_values": json_safe(outliers.head(5).tolist()),
            }
        else:
            result["top_values"] = json_safe(series.value_counts().head(10).to_dict())
        return result

    def filter_rows(
        self, column: str, operator: str, value: Any
    ) -> dict[str, Any]:
        column = validate_column(self.df, sanitize_string(column))
        if operator not in ALLOWED_OPERATORS:
            raise ValueError(f"Operator must be one of {ALLOWED_OPERATORS}")

        if isinstance(value, str):
            value = sanitize_string(value)

        series = self.df[column]
        if pd.api.types.is_numeric_dtype(series) and not isinstance(value, (int, float)):
            try:
                value = float(value)
            except (ValueError, TypeError):
                pass

        ops = {
            "eq": series == value,
            "ne": series != value,
            "gt": series > value,
            "gte": series >= value,
            "lt": series < value,
            "lte": series <= value,
            "contains": series.astype(str).str.contains(str(value), case=False, na=False),
        }
        mask = ops[operator]
        filtered = self.df[mask]
        preview = filtered.head(MAX_FILTER_PREVIEW)
        return {
            "matching_rows": len(filtered),
            "preview": df_to_records(preview),
        }

    def group_and_aggregate(
        self,
        group_by: list[str],
        metric_column: str,
        agg: str,
    ) -> dict[str, Any]:
        group_by = validate_columns(self.df, [sanitize_string(c) for c in group_by])
        metric_column = validate_column(self.df, sanitize_string(metric_column))
        if agg not in ALLOWED_AGGS:
            raise ValueError(f"Aggregation must be one of {ALLOWED_AGGS}")

        grouped = self.df.groupby(group_by)[metric_column].agg(agg).reset_index()
        grouped.columns = list(group_by) + [f"{metric_column}_{agg}"]
        return {"results": df_to_records(grouped)}

    def top_n(
        self,
        column: str,
        n: int,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        column = validate_column(self.df, sanitize_string(column))
        n = min(max(1, int(n)), MAX_TOP_N)

        if group_by:
            group_by = validate_column(self.df, sanitize_string(group_by))
            ranked = (
                self.df.groupby(group_by)[column]
                .sum()
                .sort_values(ascending=False)
                .head(n)
                .reset_index()
            )
            return {"results": df_to_records(ranked)}
        ranked = self.df.nlargest(n, column)
        return {"results": df_to_records(ranked)}

    def compare_periods(
        self,
        date_column: str,
        metric_column: str,
        period_a_start: str,
        period_a_end: str,
        period_b_start: str,
        period_b_end: str,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        date_column = validate_column(self.df, sanitize_string(date_column))
        metric_column = validate_column(self.df, sanitize_string(metric_column))

        df = self.df.copy()
        df[date_column] = pd.to_datetime(df[date_column])

        a_start, a_end = pd.Timestamp(period_a_start), pd.Timestamp(period_a_end)
        b_start, b_end = pd.Timestamp(period_b_start), pd.Timestamp(period_b_end)

        mask_a = (df[date_column] >= a_start) & (df[date_column] <= a_end)
        mask_b = (df[date_column] >= b_start) & (df[date_column] <= b_end)

        if group_by:
            group_by = validate_column(self.df, sanitize_string(group_by))
            a_vals = df.loc[mask_a].groupby(group_by)[metric_column].sum()
            b_vals = df.loc[mask_b].groupby(group_by)[metric_column].sum()
            all_groups = sorted(set(a_vals.index) | set(b_vals.index))
            comparisons = []
            for g in all_groups:
                a_val = float(a_vals.get(g, 0))
                b_val = float(b_vals.get(g, 0))
                change = ((b_val - a_val) / a_val * 100) if a_val else None
                comparisons.append(
                    json_safe({
                        group_by: g,
                        "period_a_total": a_val,
                        "period_b_total": b_val,
                        "change_pct": round(change, 2) if change is not None else None,
                    })
                )
            return {"comparisons": comparisons}

        a_total = float(df.loc[mask_a, metric_column].sum())
        b_total = float(df.loc[mask_b, metric_column].sum())
        change = ((b_total - a_total) / a_total * 100) if a_total else None
        return {
            "period_a": {"start": period_a_start, "end": period_a_end, "total": a_total},
            "period_b": {"start": period_b_start, "end": period_b_end, "total": b_total},
            "change_pct": round(change, 2) if change is not None else None,
        }

    def make_chart(
        self,
        chart_type: str,
        x_column: str,
        y_column: str,
        title: str,
        group_by: str | None = None,
        agg: str = "sum",
    ) -> dict[str, Any]:
        x_column = validate_column(self.df, sanitize_string(x_column))
        y_column = validate_column(self.df, sanitize_string(y_column))
        title = sanitize_string(title)
        if agg not in CHART_AGGS:
            raise ValueError(f"Chart aggregation must be one of {CHART_AGGS}")

        df = self.df.copy()
        if pd.api.types.is_datetime64_any_dtype(df[x_column]):
            df[x_column] = df[x_column].dt.to_period("M").astype(str)

        fig, ax = plt.subplots(figsize=(10, 6))

        if group_by:
            group_by = validate_column(self.df, sanitize_string(group_by))
            pivot = df.groupby([x_column, group_by])[y_column].agg(agg).unstack(fill_value=0)
            if chart_type == "bar":
                pivot.plot(kind="bar", ax=ax)
            else:
                pivot.plot(kind="line", ax=ax, marker="o")
        else:
            grouped = df.groupby(x_column)[y_column].agg(agg)
            if chart_type == "bar":
                grouped.plot(kind="bar", ax=ax)
            else:
                grouped.plot(kind="line", ax=ax, marker="o")

        ax.set_title(title)
        ax.set_xlabel(x_column)
        ax.set_ylabel(f"{y_column} ({agg})")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        filename = f"chart_{uuid.uuid4().hex[:8]}.png"
        filepath = self.charts_dir / filename
        fig.savefig(filepath, dpi=100)
        plt.close(fig)

        return {"chart_path": str(filepath), "title": title}

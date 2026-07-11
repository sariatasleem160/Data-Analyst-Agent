"""JSON schemas for safe CSV analysis tools."""

TOOL_SCHEMAS = [
    {
        "name": "get_schema",
        "description": "Return column names, dtypes, row count, and sample values for the loaded dataset.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "profile_dataset",
        "description": "Return summary statistics for all numeric columns and value counts for categorical columns.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "describe_column",
        "description": "Detailed statistics for a single column (numeric or categorical).",
        "input_schema": {
            "type": "object",
            "properties": {
                "column": {
                    "type": "string",
                    "description": "Name of the column to describe.",
                }
            },
            "required": ["column"],
        },
    },
    {
        "name": "filter_rows",
        "description": "Filter rows by a column condition. Returns matching row count and a preview of up to 10 rows.",
        "input_schema": {
            "type": "object",
            "properties": {
                "column": {"type": "string", "description": "Column to filter on."},
                "operator": {
                    "type": "string",
                    "enum": ["eq", "ne", "gt", "gte", "lt", "lte", "contains"],
                    "description": "Comparison operator.",
                },
                "value": {
                    "description": "Value to compare against (string or number).",
                },
            },
            "required": ["column", "operator", "value"],
        },
    },
    {
        "name": "group_and_aggregate",
        "description": "Group by one or more columns and compute aggregate metrics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "group_by": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Columns to group by.",
                },
                "metric_column": {
                    "type": "string",
                    "description": "Numeric column to aggregate.",
                },
                "agg": {
                    "type": "string",
                    "enum": ["sum", "mean", "count", "min", "max", "median"],
                    "description": "Aggregation function.",
                },
            },
            "required": ["group_by", "metric_column", "agg"],
        },
    },
    {
        "name": "top_n",
        "description": "Return the top N rows ranked by a numeric column (descending).",
        "input_schema": {
            "type": "object",
            "properties": {
                "column": {
                    "type": "string",
                    "description": "Numeric column to rank by.",
                },
                "n": {
                    "type": "integer",
                    "description": "Number of top rows to return.",
                    "minimum": 1,
                    "maximum": 50,
                },
                "group_by": {
                    "type": "string",
                    "description": "Optional column to group before ranking (e.g. product).",
                },
            },
            "required": ["column", "n"],
        },
    },
    {
        "name": "compare_periods",
        "description": "Compare a metric between two date ranges (e.g. Q2 vs Q3).",
        "input_schema": {
            "type": "object",
            "properties": {
                "date_column": {
                    "type": "string",
                    "description": "Date column name.",
                },
                "metric_column": {
                    "type": "string",
                    "description": "Numeric column to compare.",
                },
                "period_a_start": {
                    "type": "string",
                    "description": "Start date for period A (YYYY-MM-DD).",
                },
                "period_a_end": {
                    "type": "string",
                    "description": "End date for period A (YYYY-MM-DD).",
                },
                "period_b_start": {
                    "type": "string",
                    "description": "Start date for period B (YYYY-MM-DD).",
                },
                "period_b_end": {
                    "type": "string",
                    "description": "End date for period B (YYYY-MM-DD).",
                },
                "group_by": {
                    "type": "string",
                    "description": "Optional column to break comparison by (e.g. customer_segment).",
                },
            },
            "required": [
                "date_column",
                "metric_column",
                "period_a_start",
                "period_a_end",
                "period_b_start",
                "period_b_end",
            ],
        },
    },
    {
        "name": "make_chart",
        "description": "Create a bar or line chart and save it to results/charts/. Returns the file path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line"],
                    "description": "Chart type.",
                },
                "x_column": {"type": "string", "description": "X-axis column."},
                "y_column": {"type": "string", "description": "Y-axis numeric column."},
                "group_by": {
                    "type": "string",
                    "description": "Optional column for grouping/coloring series.",
                },
                "title": {"type": "string", "description": "Chart title."},
                "agg": {
                    "type": "string",
                    "enum": ["sum", "mean", "count"],
                    "description": "Aggregation for y values when grouping.",
                },
            },
            "required": ["chart_type", "x_column", "y_column", "title"],
        },
    },
]

TOOL_NAMES = {schema["name"] for schema in TOOL_SCHEMAS}

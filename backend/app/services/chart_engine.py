"""
Chart type selection engine based on data characteristics.
"""
from typing import List, Dict, Any, Optional
import re


class ChartEngine:
    """Rule-based chart type selector."""

    DATE_PATTERNS = [
        r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        r'\d{4}/\d{2}/\d{2}',  # YYYY/MM/DD
        r'\d{2}-\d{2}-\d{4}',  # DD-MM-YYYY
    ]

    def select_chart_type(self, data: List[Dict[str, Any]]) -> Optional[str]:
        """
        Select chart type based on data characteristics.

        Rules:
        - Time series (date column) → line
        - Categorical + numeric (≤10 categories) → bar
        - Percentage data (sum=100%) → pie
        - Two numeric columns → scatter
        - Otherwise → None (table only)
        """
        if not data or len(data) == 0:
            return None

        columns = list(data[0].keys())

        # Check for time series
        if self._has_date_column(data, columns):
            return "line"

        # Check for categorical + numeric
        if self._is_categorical_numeric(data, columns):
            return "bar"

        # Check for percentage data
        if self._is_percentage_data(data, columns):
            return "pie"

        # Check for two numeric columns
        if self._has_two_numeric_columns(data, columns):
            return "scatter"

        return None

    def _has_date_column(self, data: List[Dict[str, Any]], columns: List[str]) -> bool:
        """Check if data has a date column."""
        for col in columns:
            if any(keyword in col.lower() for keyword in ['date', 'time', 'day', 'month', 'year']):
                # Check if values match date patterns
                sample_value = str(data[0].get(col, ''))
                for pattern in self.DATE_PATTERNS:
                    if re.match(pattern, sample_value):
                        return True
        return False

    def _is_categorical_numeric(self, data: List[Dict[str, Any]], columns: List[str]) -> bool:
        """Check if data has categorical + numeric structure."""
        if len(columns) != 2:
            return False

        # Check if one column is string and one is numeric
        col1, col2 = columns
        val1 = data[0].get(col1)
        val2 = data[0].get(col2)

        is_cat_num = isinstance(val1, str) and isinstance(val2, (int, float))
        is_num_cat = isinstance(val2, str) and isinstance(val1, (int, float))

        if not (is_cat_num or is_num_cat):
            return False

        # Check category count ≤ 10
        cat_col = col1 if isinstance(val1, str) else col2
        unique_categories = set(row[cat_col] for row in data)
        return len(unique_categories) <= 10

    def _is_percentage_data(self, data: List[Dict[str, Any]], columns: List[str]) -> bool:
        """Check if data represents percentages (sum ≈ 100%)."""
        if len(columns) != 2:
            return False

        # Find numeric column
        numeric_col = None
        for col in columns:
            if isinstance(data[0].get(col), (int, float)):
                numeric_col = col
                break

        if not numeric_col:
            return False

        # Check if sum is close to 100
        total = sum(row.get(numeric_col, 0) for row in data)
        return 95 <= total <= 105

    def _has_two_numeric_columns(self, data: List[Dict[str, Any]], columns: List[str]) -> bool:
        """Check if data has exactly two numeric columns."""
        numeric_count = sum(
            1 for col in columns
            if isinstance(data[0].get(col), (int, float))
        )
        return numeric_count == 2

    def build_chart_config(self, data: List[Dict[str, Any]], chart_type: str) -> Optional[Dict[str, Any]]:
        """
        Build ECharts configuration based on chart type.

        Returns ECharts option object or None.
        """
        if not data or not chart_type:
            return None

        if chart_type == "line":
            return self._build_line_config(data)
        elif chart_type == "bar":
            return self._build_bar_config(data)
        elif chart_type == "pie":
            return self._build_pie_config(data)
        elif chart_type == "scatter":
            return self._build_scatter_config(data)

        return None

    def _build_line_config(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build line chart config."""
        columns = list(data[0].keys())
        x_col = columns[0]  # Assume first column is X axis
        y_col = columns[1]  # Assume second column is Y axis

        return {
            "xAxis": {
                "type": "category",
                "data": [row[x_col] for row in data]
            },
            "yAxis": {
                "type": "value"
            },
            "series": [{
                "type": "line",
                "data": [row[y_col] for row in data]
            }],
            "tooltip": {"trigger": "axis"}
        }

    def _build_bar_config(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build bar chart config."""
        columns = list(data[0].keys())
        cat_col = columns[0]
        val_col = columns[1]

        # Determine which is categorical
        if isinstance(data[0][cat_col], (int, float)):
            cat_col, val_col = val_col, cat_col

        return {
            "xAxis": {
                "type": "category",
                "data": [row[cat_col] for row in data]
            },
            "yAxis": {
                "type": "value"
            },
            "series": [{
                "type": "bar",
                "data": [row[val_col] for row in data]
            }],
            "tooltip": {"trigger": "axis"}
        }

    def _build_pie_config(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build pie chart config."""
        columns = list(data[0].keys())
        name_col = columns[0]
        value_col = columns[1]

        # Determine which is name and which is value
        if isinstance(data[0][name_col], (int, float)):
            name_col, value_col = value_col, name_col

        return {
            "series": [{
                "type": "pie",
                "data": [
                    {"name": row[name_col], "value": row[value_col]}
                    for row in data
                ]
            }],
            "tooltip": {"trigger": "item"}
        }

    def _build_scatter_config(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build scatter chart config."""
        columns = list(data[0].keys())
        numeric_cols = [
            col for col in columns
            if isinstance(data[0][col], (int, float))
        ]

        x_col, y_col = numeric_cols[0], numeric_cols[1]

        return {
            "xAxis": {"type": "value"},
            "yAxis": {"type": "value"},
            "series": [{
                "type": "scatter",
                "data": [[row[x_col], row[y_col]] for row in data]
            }],
            "tooltip": {"trigger": "item"}
        }

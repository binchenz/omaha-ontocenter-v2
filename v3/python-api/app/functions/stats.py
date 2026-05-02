"""Built-in compute functions for ontology objects."""


def growth_rate(current: float, previous: float) -> dict:
    """Calculate growth rate between two periods."""
    if previous == 0:
        return {"rate": None, "absolute_change": current, "status": "no_baseline"}
    rate = (current - previous) / previous
    return {
        "rate": round(rate, 4),
        "rate_percent": f"{round(rate * 100, 1)}%",
        "absolute_change": round(current - previous, 2),
        "direction": "up" if rate > 0 else "down" if rate < 0 else "flat",
    }


def moving_average(values: list[float], window: int = 3) -> dict:
    """Calculate simple moving average."""
    if len(values) < window:
        return {"average": None, "error": f"Need at least {window} values"}
    avg = sum(values[-window:]) / window
    return {
        "average": round(avg, 2),
        "window": window,
        "values_used": len(values[-window:]),
    }

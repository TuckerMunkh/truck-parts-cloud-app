def normalize_code(value: str) -> str:
    return (value or "").strip().upper()

def money(value) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0

def commission_rate(price: float) -> float:
    price = money(price)
    if price <= 250:
        return 0.30
    if price <= 1500:
        return 0.20
    return 0.12

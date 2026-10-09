def calculate_total(quantity, unit_price):
    if (type(quantity) is not int or type(unit_price) is not int
            or not 0 <= quantity <= 1_000_000
            or not 0 <= unit_price <= 1_000_000_000):
        raise ValueError("invalid_arguments")
    return {"total": quantity * unit_price, "currency": "VND"}


TOOL_MAP = {"calculate_total": calculate_total}

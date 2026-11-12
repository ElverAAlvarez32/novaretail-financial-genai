"""Generadores de datos sintéticos de NovaRetail.

Este paquete contiene funciones reproducibles para construir
los catálogos, las transacciones, los movimientos operativos,
los estados financieros y el presupuesto de la empresa ficticia
NovaRetail Colombia S.A.S.
"""

from __future__ import annotations

from novaretail.generation.balance_sheet import (
    BALANCE_SHEET_COLUMNS,
    generate_balance_sheet,
)
from novaretail.generation.budget import (
    BUDGET_COLUMNS,
    generate_budget,
)
from novaretail.generation.cash_flow import (
    CASH_FLOW_COLUMNS,
    generate_cash_flow,
)
from novaretail.generation.customers import (
    CUSTOMER_COLUMNS,
    generate_customers,
)
from novaretail.generation.financial_statements import (
    INCOME_STATEMENT_COLUMNS,
    generate_income_statement,
)
from novaretail.generation.generator import (
    TABLE_ORDER,
    GeneratedData,
    generate_all_data,
)
from novaretail.generation.inventory import (
    INVENTORY_COLUMNS,
    generate_inventory,
)
from novaretail.generation.marketing import (
    MARKETING_COLUMNS,
    generate_marketing,
)
from novaretail.generation.orders import (
    ORDER_COLUMNS,
    generate_orders,
)
from novaretail.generation.products import (
    PRODUCT_COLUMNS,
    generate_products,
)
from novaretail.generation.returns import (
    RETURN_COLUMNS,
    generate_returns,
)


__all__ = [
    "BALANCE_SHEET_COLUMNS",
    "BUDGET_COLUMNS",
    "CASH_FLOW_COLUMNS",
    "CUSTOMER_COLUMNS",
    "GeneratedData",
    "INCOME_STATEMENT_COLUMNS",
    "INVENTORY_COLUMNS",
    "MARKETING_COLUMNS",
    "ORDER_COLUMNS",
    "PRODUCT_COLUMNS",
    "RETURN_COLUMNS",
    "TABLE_ORDER",
    "generate_all_data",
    "generate_balance_sheet",
    "generate_budget",
    "generate_cash_flow",
    "generate_customers",
    "generate_income_statement",
    "generate_inventory",
    "generate_marketing",
    "generate_orders",
    "generate_products",
    "generate_returns",
]
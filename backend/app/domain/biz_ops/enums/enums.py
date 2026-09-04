"""BIZ-OPS 共享枚举 - 业务操作进销存编排域。"""

from __future__ import annotations

from enum import Enum


class FeatureScope(str, Enum):
    """功能开关作用域粒度。"""
    MODULE = "module"
    SUB_FEATURE = "sub_feature"


class ScopeLevel(str, Enum):
    """策略作用域层级 - 三层继承（仓库→公司→租户）。"""
    TENANT = "tenant"
    COMPANY = "company"
    WAREHOUSE = "warehouse"


class TaxScopeLevel(str, Enum):
    """税务配置作用域层级 - 两层继承（公司→租户）。"""
    TENANT = "tenant"
    COMPANY = "company"


class RuleType(str, Enum):
    """业务规则类型。"""
    VALIDATION = "validation"
    INTERCEPTION = "interception"
    LINKAGE = "linkage"


class RuleAction(str, Enum):
    """拦截规则动作。"""
    REJECT = "reject"
    WARN = "warn"


class PricingType(str, Enum):
    """定价策略类型。"""
    SUPPLIER_AGREEMENT = "supplier_agreement"
    FRAMEWORK = "framework"
    RFQ = "rfq"
    COST_PLUS = "cost_plus"
    HISTORY_COMPARE = "history_compare"
    CUSTOMER_AGREEMENT = "customer_agreement"
    DISCOUNT = "discount"
    PROMOTION = "promotion"
    MEMBER = "member"
    TIER = "tier"
    VOLUME_PRICE = "volume_price"


class TaxType(str, Enum):
    """税种。"""
    VAT = "vat"
    CONSUMPTION = "consumption"
    CUSTOMS = "customs"
    SURTAX = "surtax"


class TaxFlag(str, Enum):
    """含税标志。"""
    TAX_INCLUSIVE = "tax_inclusive"
    TAX_EXCLUSIVE = "tax_exclusive"


class TaxDirection(str, Enum):
    """进项销项方向。"""
    INPUT = "input"
    OUTPUT = "output"


class InvStrategyType(str, Enum):
    """库存策略类型。"""
    SAFETY_STOCK = "safety_stock"
    ALERT = "alert"
    REORDER = "reorder"
    AGING = "aging"
    ABC = "abc"


class ExecutionResult(str, Enum):
    """策略执行结果。"""
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    WARN = "warn"


class TimeoutStrategy(str, Enum):
    """超时策略。"""
    ALLOW = "allow"
    DENY = "deny"
    AUTO_APPROVE = "auto_approve"
    AUTO_REJECT = "auto_reject"
    AUTO_ESCALATE = "auto_escalate"
    WARN_ONLY = "warn_only"


class RoutingStrategyType(str, Enum):
    """审批人路由策略类型。"""
    ROLE = "role"
    DEPT = "dept"
    AMOUNT = "amount"
    SKU = "sku"
    SCRIPT = "script"


class OperationType(str, Enum):
    """业务操作类型。"""
    PURCHASE_ORDER_CREATE = "purchase_order_create"
    PURCHASE_ORDER_SUBMIT = "purchase_order_submit"
    PURCHASE_RECEIPT = "purchase_receipt"
    PURCHASE_RETURN = "purchase_return"
    SALES_ORDER_CREATE = "sales_order_create"
    SALES_ORDER_SUBMIT = "sales_order_submit"
    SALES_SHIPMENT = "sales_shipment"
    SALES_RETURN = "sales_return"
    INVENTORY_INBOUND = "inventory_inbound"
    INVENTORY_OUTBOUND = "inventory_outbound"
    INVENTORY_TRANSFER = "inventory_transfer"
    INVENTORY_COUNT = "inventory_count"
    INVENTORY_ADJUST = "inventory_adjust"
    WAREHOUSE_RECEIVING = "warehouse_receiving"
    WAREHOUSE_PUTAWAY = "warehouse_putaway"
    WAREHOUSE_PICKING = "warehouse_picking"
    WAREHOUSE_TRANSFER = "warehouse_transfer"
    WAREHOUSE_SHIPPING = "warehouse_shipping"
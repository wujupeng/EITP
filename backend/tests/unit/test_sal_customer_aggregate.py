"""SAL CustomerAggregate / CustomerCategoryAggregate 单元测试 - 客户治理工作流 + 银行账户脱敏 + 多地址多联系人 + 分类启停。

覆盖 DRAFT→SUBMITTED→APPROVED→ACTIVE→DISABLED→ACTIVE 主路径、REJECTED/CANCELLED 终态、
submit 缺编码/名称拒绝、add_address/add_contact、银行账户脱敏、CustomerCategory ACTIVE↔DISABLED 流转。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.sales.aggregates.customer_aggregate import CustomerAggregate
from app.domain.sales.aggregates.customer_category_aggregate import CustomerCategoryAggregate
from app.domain.sales.entities.customer_address import AddressType, CustomerAddress
from app.domain.sales.entities.customer_contact import CustomerContact
from app.domain.sales.value_objects.category_status import CategoryStatus
from app.domain.sales.value_objects.customer_vo import BankAccount, CustomerStatus, CustomerType
from app.interfaces.middleware.error_handler import SALError, SALErrorCode


def _customer() -> CustomerAggregate:
    return CustomerAggregate(customer_code="C-001", customer_name="Acme Corp")


def _active_customer() -> CustomerAggregate:
    c = _customer()
    c.submit()
    c.approve(uuid4())
    c.publish()
    return c


class CustomerAggregateTest:
    """CustomerAggregate 治理工作流状态机与地址/联系人/脱敏测试。"""

    def test_default_status_is_draft(self) -> None:
        c = CustomerAggregate()
        assert c.status == CustomerStatus.DRAFT
        assert c.is_active is False
        assert c.can_receive_orders is False
        assert c.published_version == 0

    def test_submit_without_code_rejected(self) -> None:
        c = CustomerAggregate(customer_name="Acme")
        with pytest.raises(SALError) as exc:
            c.submit()
        assert exc.value.code == SALErrorCode.CUSTOMER_NOT_FOUND

    def test_submit_without_name_rejected(self) -> None:
        c = CustomerAggregate(customer_code="C-001")
        with pytest.raises(SALError) as exc:
            c.submit()
        assert exc.value.code == SALErrorCode.CUSTOMER_NOT_FOUND

    def test_submit_transitions_to_submitted(self) -> None:
        c = _customer()
        c.submit()
        assert c.status == CustomerStatus.SUBMITTED
        assert c.governance_state == "submitted"

    def test_full_lifecycle_to_active(self) -> None:
        c = _active_customer()
        assert c.status == CustomerStatus.ACTIVE
        assert c.published_version == 1
        assert c.is_active is True
        assert c.can_receive_orders is True

    def test_approve_sets_governance_state(self) -> None:
        c = _customer()
        c.submit()
        c.approve(uuid4())
        assert c.status == CustomerStatus.APPROVED
        assert c.governance_state == "approved"

    def test_publish_increments_version(self) -> None:
        c = _customer()
        c.submit()
        c.approve(uuid4())
        c.publish()
        assert c.published_version == 1
        c.disable()
        c.enable()
        # 重新启用不再次发布，版本不变
        assert c.published_version == 1

    def test_disable_then_enable_cycle(self) -> None:
        c = _active_customer()
        c.disable()
        assert c.status == CustomerStatus.DISABLED
        assert c.can_receive_orders is False
        c.enable()
        assert c.status == CustomerStatus.ACTIVE
        assert c.can_receive_orders is True

    def test_reject_from_submitted_is_terminal(self) -> None:
        c = _customer()
        c.submit()
        c.reject(uuid4())
        assert c.status == CustomerStatus.REJECTED
        with pytest.raises(SALError) as exc:
            c.approve(uuid4())
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_cancel_from_draft(self) -> None:
        c = _customer()
        c.cancel()
        assert c.status == CustomerStatus.CANCELLED

    def test_cancel_from_submitted(self) -> None:
        c = _customer()
        c.submit()
        c.cancel()
        assert c.status == CustomerStatus.CANCELLED

    def test_cancelled_is_terminal(self) -> None:
        c = _customer()
        c.cancel()
        with pytest.raises(SALError) as exc:
            c.submit()
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_submit_from_submitted_rejected(self) -> None:
        c = _customer()
        c.submit()
        with pytest.raises(SALError) as exc:
            c.submit()
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_approve_from_draft_rejected(self) -> None:
        c = _customer()
        with pytest.raises(SALError) as exc:
            c.approve(uuid4())
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_publish_from_submitted_rejected(self) -> None:
        c = _customer()
        c.submit()
        with pytest.raises(SALError) as exc:
            c.publish()
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_disable_from_active_only(self) -> None:
        c = _customer()
        c.submit()
        c.approve(uuid4())
        with pytest.raises(SALError) as exc:
            c.disable()
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_enable_from_active_rejected(self) -> None:
        c = _active_customer()
        with pytest.raises(SALError) as exc:
            c.enable()
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_add_address_sets_customer_id_and_appends(self) -> None:
        c = _customer()
        addr = CustomerAddress(address_type=AddressType.DEFAULT, city="Shanghai")
        c.add_address(addr)
        assert addr.customer_id == c.customer_id
        assert len(c.addresses) == 1
        assert c.default_address is addr

    def test_add_shipping_address(self) -> None:
        c = _customer()
        addr = CustomerAddress(address_type=AddressType.SHIPPING, city="Beijing")
        c.add_address(addr)
        assert c.shipping_address is addr
        assert addr.is_shipping is True

    def test_add_billing_address(self) -> None:
        c = _customer()
        addr = CustomerAddress(address_type=AddressType.BILLING, city="Shenzhen")
        c.add_address(addr)
        assert addr.is_billing is True
        assert addr.is_shipping is False

    def test_default_address_none_when_absent(self) -> None:
        c = _customer()
        assert c.default_address is None
        assert c.shipping_address is None

    def test_add_contact_sets_customer_id_and_appends(self) -> None:
        c = _customer()
        contact = CustomerContact(name="Alice", phone="13800000000")
        c.add_contact(contact)
        assert contact.customer_id == c.customer_id
        assert len(c.contacts) == 1

    def test_assign_categories_deduplicates(self) -> None:
        c = _customer()
        cat1, cat2 = uuid4(), uuid4()
        c.assign_categories([cat1, cat2])
        c.assign_categories([cat1])  # 重复应去重
        assert set(c.category_ids) == {cat1, cat2}

    def test_customer_type_defaults_corporate(self) -> None:
        c = CustomerAggregate()
        assert c.customer_type == CustomerType.CORPORATE


class BankAccountTest:
    """BankAccount 银行账户脱敏值对象测试。"""

    def test_from_raw_masks_all_but_last_four(self) -> None:
        acct = BankAccount.from_raw("ICBC", "6222021234567890")
        assert acct.account_number_masked == "************7890"
        assert acct.last_four == "7890"

    def test_from_raw_short_account_not_masked(self) -> None:
        acct = BankAccount.from_raw("ICBC", "1234")
        assert acct.account_number_masked == "1234"
        assert acct.last_four == "1234"

    def test_from_raw_empty_account(self) -> None:
        acct = BankAccount.from_raw("ICBC", "")
        assert acct.account_number_masked == ""
        assert acct.last_four == ""

    def test_last_four_for_three_digit_account(self) -> None:
        acct = BankAccount.from_raw("ICBC", "123")
        assert acct.last_four == "123"


class CustomerCategoryAggregateTest:
    """CustomerCategoryAggregate 启停状态机与编码测试。"""

    def test_default_status_is_active(self) -> None:
        cat = CustomerCategoryAggregate(category_code="VIP", category_name="VIP 客户")
        assert cat.status == CategoryStatus.ACTIVE
        assert cat.is_active is True

    def test_disable_from_active(self) -> None:
        cat = CustomerCategoryAggregate(category_code="VIP")
        cat.disable()
        assert cat.status == CategoryStatus.DISABLED
        assert cat.is_active is False

    def test_enable_from_disabled(self) -> None:
        cat = CustomerCategoryAggregate(category_code="VIP")
        cat.disable()
        cat.enable()
        assert cat.status == CategoryStatus.ACTIVE
        assert cat.is_active is True

    def test_disable_from_disabled_rejected(self) -> None:
        cat = CustomerCategoryAggregate(category_code="VIP")
        cat.disable()
        with pytest.raises(SALError) as exc:
            cat.disable()
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_enable_from_active_rejected(self) -> None:
        cat = CustomerCategoryAggregate(category_code="VIP")
        with pytest.raises(SALError) as exc:
            cat.enable()
        assert exc.value.code == SALErrorCode.ORDER_INVALID_STATE_TRANSITION

    def test_category_code_uniqueness_by_identity(self) -> None:
        # 编码唯一性由仓储层唯一约束保证；聚合层仅承载 code 属性。
        cat_a = CustomerCategoryAggregate(category_code="VIP")
        cat_b = CustomerCategoryAggregate(category_code="VIP")
        assert cat_a.category_code == cat_b.category_code
        assert cat_a.category_id != cat_b.category_id
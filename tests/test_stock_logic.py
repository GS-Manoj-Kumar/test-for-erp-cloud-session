"""Balance / transfer rules for Inventory. Plain pytest, no bench.

A tiny in-memory "ledger" (a dict of balances) stands in for Stock Ledger Entry.
"""

import pytest

from cabinet_erp.inventory.stock_logic import (
    DISPATCH, IN_PROCESS, ISSUE, RECEIPT, RECEIVED, RETURN, SENT, TRANSFER,
    apply_legs, ledger_conditions, location_errors, location_title, material_status,
    movement_errors, movement_legs, needs_urgent_approval, net_changes, pivot_balances,
    reverse_legs, running_balances, shortage_errors,
)

ITEM = "CORE-18-8X4"
EB = "EB-C1-2MM"


class Ledger:
    """Submit / cancel movements the way StockMovement does, against a dict."""

    def __init__(self):
        self.bal = {}

    def balance(self, loc, state, item):
        return self.bal.get((loc, state, item), 0)

    def _post(self, legs):
        errors = shortage_errors(legs, self.balance)
        if errors:
            raise ValueError(errors)
        self.bal = apply_legs(self.bal, legs)

    def submit(self, mtype, loc, items, target=None, from_state=None):
        legs = movement_legs(mtype, loc, items, target_location=target, from_state=from_state)
        self._post(legs)
        return legs

    def cancel(self, legs):
        self._post(reverse_legs(legs))


def items(qty, item=ITEM, rate=1500):
    return [{"stock_item": item, "qty": qty, "rate": rate}]


# --- legs per movement type -------------------------------------------------

def test_receipt_adds_received():
    legs = movement_legs(RECEIPT, "LOC-1", items(10))
    assert legs == [{"stock_item": ITEM, "location": "LOC-1", "state": RECEIVED, "qty_change": 10.0, "rate": 1500.0}]


@pytest.mark.parametrize("mtype,from_state,out_state,in_state", [
    (ISSUE, None, RECEIVED, IN_PROCESS),
    (RETURN, None, IN_PROCESS, RECEIVED),
    (DISPATCH, IN_PROCESS, IN_PROCESS, SENT),
    (DISPATCH, RECEIVED, RECEIVED, SENT),
])
def test_state_changes_stay_in_location(mtype, from_state, out_state, in_state):
    legs = movement_legs(mtype, "LOC-1", items(4), from_state=from_state)
    assert [(l["location"], l["state"], l["qty_change"]) for l in legs] == [
        ("LOC-1", out_state, -4.0), ("LOC-1", in_state, 4.0)]


def test_transfer_moves_received_between_locations():
    legs = movement_legs(TRANSFER, "LOC-A", items(3), target_location="LOC-B")
    assert [(l["location"], l["state"], l["qty_change"]) for l in legs] == [
        ("LOC-A", RECEIVED, -3.0), ("LOC-B", RECEIVED, 3.0)]


def test_every_movement_nets_to_zero_except_receipt():
    for mtype, kw in [(ISSUE, {}), (RETURN, {}), (DISPATCH, {"from_state": RECEIVED}),
                      (TRANSFER, {"target_location": "LOC-B"})]:
        legs = movement_legs(mtype, "LOC-A", items(5), **kw)
        assert sum(l["qty_change"] for l in legs) == 0, mtype


def test_reverse_legs_negates_and_does_not_mutate():
    legs = movement_legs(ISSUE, "LOC-1", items(2))
    rev = reverse_legs(legs)
    assert [l["qty_change"] for l in rev] == [2.0, -2.0]
    assert [l["qty_change"] for l in legs] == [-2.0, 2.0]


# --- balance validation -----------------------------------------------------

def test_full_lifecycle():
    led = Ledger()
    led.submit(RECEIPT, "LOC-1", items(10))
    led.submit(ISSUE, "LOC-1", items(6))
    led.submit(RETURN, "LOC-1", items(1))
    led.submit(DISPATCH, "LOC-1", items(5), from_state=IN_PROCESS)
    assert led.balance("LOC-1", RECEIVED, ITEM) == 5
    assert led.balance("LOC-1", IN_PROCESS, ITEM) == 0
    assert led.balance("LOC-1", SENT, ITEM) == 5


def test_cannot_issue_more_than_received():
    led = Ledger()
    led.submit(RECEIPT, "LOC-1", items(2))
    with pytest.raises(ValueError, match="have 2, need 3"):
        led.submit(ISSUE, "LOC-1", items(3))
    assert led.balance("LOC-1", RECEIVED, ITEM) == 2  # nothing posted


def test_cannot_dispatch_from_empty_state():
    led = Ledger()
    led.submit(RECEIPT, "LOC-1", items(5))
    with pytest.raises(ValueError):
        led.submit(DISPATCH, "LOC-1", items(1), from_state=IN_PROCESS)


def test_balance_is_per_location_state_and_item():
    led = Ledger()
    led.submit(RECEIPT, "LOC-1", items(5))
    led.submit(RECEIPT, "LOC-1", items(5, item=EB))
    with pytest.raises(ValueError):
        led.submit(ISSUE, "LOC-2", items(1))           # other location
    led.submit(ISSUE, "LOC-1", items(5, item=EB))
    assert led.balance("LOC-1", RECEIVED, ITEM) == 5   # other item untouched


def test_same_item_twice_in_one_movement_is_checked_together():
    led = Ledger()
    led.submit(RECEIPT, "LOC-1", items(5))
    two_rows = items(3) + items(3)
    with pytest.raises(ValueError, match="need 6"):
        led.submit(ISSUE, "LOC-1", two_rows)


def test_cancel_receipt_after_it_was_used_is_blocked():
    led = Ledger()
    receipt = led.submit(RECEIPT, "LOC-1", items(5))
    led.submit(ISSUE, "LOC-1", items(4))
    with pytest.raises(ValueError):
        led.cancel(receipt)


def test_cancel_restores_balances():
    led = Ledger()
    led.submit(RECEIPT, "LOC-1", items(5))
    issue = led.submit(ISSUE, "LOC-1", items(4))
    led.cancel(issue)
    assert led.balance("LOC-1", RECEIVED, ITEM) == 5
    assert led.balance("LOC-1", IN_PROCESS, ITEM) == 0


def test_float_qty_rounding():
    led = Ledger()
    led.submit(RECEIPT, "LOC-1", items(0.1, item=EB))
    led.submit(RECEIPT, "LOC-1", items(0.2, item=EB))
    led.submit(ISSUE, "LOC-1", items(0.3, item=EB))    # 0.1 + 0.2 must cover 0.3
    assert led.balance("LOC-1", RECEIVED, EB) == 0


def test_net_changes():
    legs = movement_legs(ISSUE, "L", items(2)) + movement_legs(ISSUE, "L", items(1))
    assert net_changes(legs) == {("L", RECEIVED, ITEM): -3.0, ("L", IN_PROCESS, ITEM): 3.0}


# --- transfer rules ---------------------------------------------------------

def test_transfer_between_projects():
    led = Ledger()
    led.submit(RECEIPT, "LOC-P1", items(8))
    led.submit(TRANSFER, "LOC-P1", items(3), target="LOC-P2")
    assert led.balance("LOC-P1", RECEIVED, ITEM) == 5
    assert led.balance("LOC-P2", RECEIVED, ITEM) == 3
    with pytest.raises(ValueError):
        led.submit(TRANSFER, "LOC-P1", items(6), target="LOC-P2")


def test_in_process_stock_cannot_be_transferred():
    led = Ledger()
    led.submit(RECEIPT, "LOC-P1", items(2))
    led.submit(ISSUE, "LOC-P1", items(2))
    with pytest.raises(ValueError):
        led.submit(TRANSFER, "LOC-P1", items(1), target="LOC-P2")


def test_needs_urgent_approval():
    assert needs_urgent_approval("P0001", "P0002")
    assert not needs_urgent_approval("P0001", "P0001")   # e.g. project -> its own order
    assert not needs_urgent_approval(None, "P0002")      # general store -> project
    assert not needs_urgent_approval("P0001", None)


def _errors(**kw):
    base = dict(movement_type=TRANSFER, location="LOC-A", target_location="LOC-B", items=items(1))
    base.update(kw)
    return movement_errors(**base)


def test_project_transfer_requires_urgent_and_reason():
    errs = _errors(location_project="P0001", target_project="P0002")
    assert any("Urgent" in e for e in errs) and any("Reason" in e for e in errs)
    assert _errors(location_project="P0001", target_project="P0002", is_urgent=1, reason="Site waiting") == []
    assert any("Reason" in e for e in _errors(location_project="P0001", target_project="P0002",
                                               is_urgent=1, reason="   "))


def test_transfer_from_general_store_needs_no_approval():
    assert _errors(location_project=None, target_project="P0002") == []


def test_transfer_needs_two_locations():
    assert any("Target Location" in e for e in _errors(target_location=None))
    assert any("different" in e for e in _errors(target_location="LOC-A"))


def test_movement_item_checks():
    assert any("at least one item" in e for e in movement_errors(RECEIPT, "L", items=[]))
    assert any("greater than 0" in e for e in movement_errors(RECEIPT, "L", items=items(0)))
    assert any("Stock Item" in e for e in movement_errors(RECEIPT, "L", items=[{"qty": 1}]))
    assert any("Dispatch" in e for e in movement_errors(DISPATCH, "L", from_state=SENT, items=items(1)))
    assert movement_errors(RECEIPT, "L", items=items(1)) == []


# --- locations --------------------------------------------------------------

def test_location_scope_requires_link():
    assert location_errors("General") == []
    assert location_errors("Client") != []
    assert location_errors("Client", client="C0001") == []
    assert location_errors("Project", client="C0001") != []
    assert location_errors("Order", production_order="P0001-ORD-01") == []
    assert location_errors("Warehouse") != []


def test_location_title():
    assert location_title("General") == "General Store"
    assert location_title("Client", client="C0001", names={"C0001": "Sharma"}) == "Client: C0001 - Sharma"
    assert location_title("Project", project="P0001") == "Project: P0001"
    assert location_title("Order", production_order="P0001-ORD-01") == "Order: P0001-ORD-01"


# --- report helpers ---------------------------------------------------------

def test_pivot_balances():
    rows = [
        {"location": "L2", "stock_item": ITEM, "state": RECEIVED, "qty": 1},
        {"location": "L1", "stock_item": ITEM, "state": RECEIVED, "qty": 5},
        {"location": "L1", "stock_item": ITEM, "state": IN_PROCESS, "qty": 2},
        {"location": "L1", "stock_item": EB, "state": SENT, "qty": 0},   # zero row dropped
    ]
    out = pivot_balances(rows)
    assert [(r["location"], r["stock_item"]) for r in out] == [("L1", ITEM), ("L2", ITEM)]
    assert out[0]["received"] == 5 and out[0]["in_process"] == 2 and out[0]["total"] == 7


def test_running_balances_with_opening():
    rows = [
        {"location": "L1", "state": RECEIVED, "stock_item": ITEM, "qty_change": 5},
        {"location": "L1", "state": RECEIVED, "stock_item": ITEM, "qty_change": -2},
        {"location": "L1", "state": IN_PROCESS, "stock_item": ITEM, "qty_change": 2},
    ]
    out = running_balances({("L1", RECEIVED, ITEM): 10}, rows)
    assert [r["balance"] for r in out] == [15, 13, 2]


def test_material_status():
    lines = [
        {"stock_item": ITEM, "description": "18.0mm", "kind": "core", "order_qty": 8},
        {"stock_item": ITEM, "description": "18.0mm", "kind": "core", "order_qty": 2},  # summed
        {"stock_item": None, "description": "C4_1.0mm", "kind": "edge_band", "order_qty": 2.4},
    ]
    stock = {ITEM: {"received": 3, "in_process": 4, "sent": 1}, "HINGE": {"received": 10}}
    out = material_status(lines, stock)
    core = out[0]
    assert core["required"] == 10 and core["shortfall"] == 2
    hinge = next(r for r in out if r["stock_item"] == "HINGE")
    assert hinge["required"] == 0 and hinge["shortfall"] == 0
    unmapped = out[-1]
    assert unmapped["stock_item"] == "" and unmapped["shortfall"] == 2.4


def test_ledger_conditions_use_params_only():
    where, params = ledger_conditions({"client": "C0001'; drop table x;--", "state": RECEIVED,
                                       "from_date": "2026-01-01", "to_date": "2026-12-31", "junk": "x"})
    assert "drop" not in where
    assert params["client"].startswith("C0001'")
    assert "`client` = %(client)s" in where and "posting_date >= %(from_date)s" in where
    assert "junk" not in where
    w2, _ = ledger_conditions({"from_date": "2026-01-01"}, from_date=False)
    assert "from_date" not in w2

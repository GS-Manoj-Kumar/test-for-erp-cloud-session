from cabinet_erp.clients.crm_logic import became_won, client_values_from_deal, primary_contact_of


def test_became_won():
    assert became_won("Negotiation", "Won")
    assert became_won(None, "Won")            # created as Won
    assert not became_won("Won", "Won")       # saving again does nothing
    assert not became_won("Won", "Lost")


def test_b2b_deal_with_organization():
    deal = {"name": "CRM-DEAL-0001", "organization": "Lotus Interiors", "email": "a@lotus.example.com",
            "mobile_no": "+91 90000 00002", "first_name": "Ravi"}
    v = client_values_from_deal(deal, {"organization_name": "Lotus Interiors Pvt Ltd"}, "CONTACT-1")
    assert v == {"client_name": "Lotus Interiors Pvt Ltd", "client_type": "B2B", "crm_organization": "Lotus Interiors",
                 "crm_deal": "CRM-DEAL-0001", "primary_contact": "CONTACT-1", "phone": "+91 90000 00002",
                 "email": "a@lotus.example.com"}


def test_b2c_deal_uses_person_name():
    v = client_values_from_deal({"name": "D2", "first_name": "Anita", "last_name": "Sharma", "phone": "123"})
    assert v["client_name"] == "Anita Sharma" and v["client_type"] == "B2C"
    assert v["crm_organization"] is None and v["phone"] == "123"
    assert client_values_from_deal({"name": "D3", "lead_name": "Lead X"})["client_name"] == "Lead X"
    assert client_values_from_deal({"name": "D4"})["client_name"] == "D4"


def test_primary_contact():
    assert primary_contact_of([{"contact": "A"}, {"contact": "B", "is_primary": 1}]) == "B"
    assert primary_contact_of([{"contact": "A"}, {"contact": "B"}]) == "A"
    assert primary_contact_of([]) is None and primary_contact_of(None) is None

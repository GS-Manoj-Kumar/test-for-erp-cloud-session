"""CRM Deal -> Cabinet Client rules. Pure Python, no Frappe imports."""

WON = "Won"


def became_won(old_status, new_status):
	return new_status == WON and old_status != WON


def deal_client_name(deal, organization_name=None):
	if organization_name:
		return organization_name
	person = " ".join(p for p in (deal.get("first_name"), deal.get("last_name")) if p).strip()
	return person or deal.get("lead_name") or deal.get("name") or ""


def client_values_from_deal(deal, organization=None, primary_contact=None):
	"""Values for a new Cabinet Client. A deal with an organization becomes B2B, otherwise B2C."""
	org_name = (organization or {}).get("organization_name") or deal.get("organization")
	return {
		"client_name": deal_client_name(deal, org_name),
		"client_type": "B2B" if deal.get("organization") else "B2C",
		"crm_organization": deal.get("organization") or None,
		"crm_deal": deal.get("name"),
		"primary_contact": primary_contact or None,
		"phone": deal.get("mobile_no") or deal.get("phone") or None,
		"email": deal.get("email") or None,
	}


def primary_contact_of(contacts):
	"""contacts: rows of CRM Deal's contacts table [{contact, is_primary}]."""
	rows = [c for c in contacts or [] if c.get("contact")]
	for c in rows:
		if c.get("is_primary"):
			return c["contact"]
	return rows[0]["contact"] if rows else None

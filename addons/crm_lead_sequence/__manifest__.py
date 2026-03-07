{
    "name": "CRM Lead Sequential Number",
    "version": "19.0.1.0.0",
    "summary": "Add unique LN number to leads (format LNDDMMYYN)",
    "category": "CRM",
    "author": "Auto",
    "depends": ["crm"],
    "data": [
        "data/ir_sequence.xml",
        "views/crm_lead_views.xml",
    ],
    "installable": True,
    "application": False,
}

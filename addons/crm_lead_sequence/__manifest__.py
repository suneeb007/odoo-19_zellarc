{
    "name": "CRM Lead Sequence",
    "version": "1.0.0",
    "summary": "Assign unique daily lead numbers like LNYYMMDD1",
    "category": "CRM",
    "depends": ["crm"],
    "data": [
        "security/ir.model.access.csv",
        "views/crm_lead_sequence_views.xml",
    ],
    "installable": True,
    "application": False,
}

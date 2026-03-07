{
    "name": "CRM Lead Sequential Number",
    "version": "19.0.1.0.0",
    "summary": "Add unique LN number to leads (format LNDDMMYYN)",
    "category": "CRM",
    "author": "Auto",
    "license": "LGPL-3",
    "depends": ["crm", "travel_flight_booking"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "views/crm_lead_sequence_views.xml",
        "views/sale_order_inherit_views.xml",
    ],
    "installable": True,
    "application": False,
}

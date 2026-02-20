{
    "name": "Air Tickets",
    "version": "19.0.1.0.0",
    "summary": "Create and manage flight ticket bookings and create sales orders",
    "category": "Sales/Travel",
    "author": "You",
    "website": "",
    "license": "LGPL-3",
    "depends": ["base", "sale", "uom", "mail", "purchase", "website"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "data/actions.xml",
        "data/open_booking_actions.xml",
        "data/open_order_from_booking.xml",
        "views/flight_booking_views.xml",
        "views/order_inherit_views.xml",
        "views/flight_booking_bulk_views.xml",
    ],
    "images": [
        "static/description/icon-v2.png",
    ],
    "assets": {
        "web.assets_backend": [
            "travel_flight_booking/static/src/css/flight_booking.css",
            "travel_flight_booking/static/src/js/bulk_button_list.js",
            "travel_flight_booking/static/src/js/bulk_download_wizard.js",
        ],
    },
    "installable": True,
    "application": True,
}

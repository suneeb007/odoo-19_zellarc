{
    "name": "Sale - Access via Log Note Author",
    "version": "1.0.0",
    "summary": "Grant read access to sale orders when user authored a log note on them",
    "description": "When a user is mentioned or authored a log note (mail.message) on a sale order, allow that user to read the related sale.order even if they only have 'own documents' access.",
    "category": "Sales",
    "author": "Auto-patch",
    "depends": [
        "sale",
        "mail"
    ],
    "data": [],
    "post_init_hook": "create_lognote_rules",
    "uninstall_hook": "uninstall_lognote_rules",
    "installable": True,
    "application": False,
}

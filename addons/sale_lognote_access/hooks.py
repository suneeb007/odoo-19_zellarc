from odoo import api, SUPERUSER_ID


def _create_rules(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    IrModel = env['ir.model']
    IrRule = env['ir.rule']

    # blacklist core models to avoid breaking administrative access
    BLACKLIST = {
        'res.company', 'res.users', 'res.partner', 'res.groups',
        'ir.rule', 'ir.model', 'ir.model.access', 'ir.config_parameter',
        'res.lang', 'res.country', 'res.country.state'
    }

    models = IrModel.search([])
    for m in models:
        model_name = m.model
        if model_name in BLACKLIST or model_name.startswith('ir.'):
            continue
        try:
            Model = env[model_name]
        except Exception:
            continue
        # check if model has message_ids field (i.e., mail.thread)
        if 'message_ids' in getattr(Model, '_fields', {}):
            rule_name = 'Read if lognote author - %s' % model_name
            # avoid duplicates
            existing = IrRule.search([('name', '=', rule_name)])
            if existing:
                continue
            # allow access when the current user either created the message,
            # is the partner author of the message, or is listed among the
            # message partner followers (mentions)
            domain = "['|', '|', ('message_ids.create_uid', '=', user.id), ('message_ids.author_id', '=', user.partner_id.id), ('message_partner_ids', 'in', user.partner_id.id)]"
            IrRule.create({
                'name': rule_name,
                'model_id': m.id,
                'domain_force': domain,
                'perm_read': True,
                'perm_write': True,
                'perm_create': False,
                'perm_unlink': False,
            })


def _uninstall_rules(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    IrRule = env['ir.rule']
    rules = IrRule.search([('name', 'like', 'Read if lognote author -')])
    if rules:
        rules.unlink()


def create_lognote_rules(env):
    # Support different call signatures: (cr, registry), env (Environment), or registry
    if hasattr(env, 'cr'):
        return _create_rules(env.cr, getattr(env, 'registry', None))
    if isinstance(env, tuple) and len(env) >= 2:
        return _create_rules(env[0], env[1])
    # assume env is registry.Registry
    if hasattr(env, 'cursor'):
        with env.cursor() as cr:
            return _create_rules(cr, env)


def uninstall_lognote_rules(env):
    if hasattr(env, 'cr'):
        return _uninstall_rules(env.cr, getattr(env, 'registry', None))
    if isinstance(env, tuple) and len(env) >= 2:
        return _uninstall_rules(env[0], env[1])
    if hasattr(env, 'cursor'):
        with env.cursor() as cr:
            return _uninstall_rules(cr, env)

from . import hooks
from . import models
from .hooks import create_lognote_rules as _create_lognote_rules, uninstall_lognote_rules as _uninstall_lognote_rules


def create_lognote_rules(cr, registry=None):
	return _create_lognote_rules(cr if registry is None else (cr, registry))


def uninstall_lognote_rules(cr, registry=None):
	return _uninstall_lognote_rules(cr if registry is None else (cr, registry))


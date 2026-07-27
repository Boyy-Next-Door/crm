"""Backfill System Settings.language to zh for existing sites.

The install hook already sets this on fresh sites, but sites created before
the set_default_system_language() function was added still have language='en'.
This patch applies the same logic retroactively.
"""

import frappe


def execute():
	current = frappe.db.get_single_value("System Settings", "language")
	if not current or current == "en":
		frappe.db.set_single_value("System Settings", "language", "zh")

	admin_lang = frappe.db.get_value("User", "Administrator", "language")
	if not admin_lang or admin_lang == "en":
		frappe.db.set_value("User", "Administrator", "language", "zh")

	frappe.db.commit()

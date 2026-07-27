"""Create the `require_password_reset` custom field on User.

The field lets the CRM tell the frontend to force a password-set modal on
users that were just created via the invitation flow. `install.py` already
creates this on fresh installs; this patch backfills existing sites so a
`bench migrate` after a code update wires everything up without a manual
step.
"""

import frappe

from crm.install import add_user_require_password_reset_field


def execute():
	add_user_require_password_reset_field()
	frappe.clear_cache(doctype="User")

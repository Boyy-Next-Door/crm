import frappe
from frappe import _
from frappe.utils.password import update_password


@frappe.whitelist()
def set_own_password(new_password: str):
	"""Let the current logged-in user set their own password.

	Used by the "you were just invited — please set a password" modal on the
	CRM frontend. Enforces Frappe's own password strength policy (via
	`update_password`), and once the password is set, clears the
	`require_password_reset` flag on the user so the modal doesn't re-appear.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("You must be logged in to set a password"), frappe.PermissionError)

	if not new_password or not isinstance(new_password, str):
		frappe.throw(_("Password is required"))

	# `update_password` applies the site's password strength policy and
	# refreshes the auth hash. Raising on weak passwords is what we want —
	# the frontend catches the exception and shows the message.
	update_password(user=user, pwd=new_password)

	# Clear our custom flag so the modal disappears on next boot.
	if frappe.db.get_value("User", user, "require_password_reset"):
		frappe.db.set_value("User", user, "require_password_reset", 0)

	return {"ok": True}


@frappe.whitelist(allow_guest=True)
def oauth_providers():
	from frappe.utils.html_utils import get_icon_html
	from frappe.utils.oauth import get_oauth2_authorize_url, get_oauth_keys
	from frappe.utils.password import get_decrypted_password

	out = []
	providers = frappe.get_all(
		"Social Login Key",
		filters={"enable_social_login": 1},
		fields=["name", "client_id", "base_url", "provider_name", "icon"],
		order_by="name",
	)

	for provider in providers:
		client_secret = get_decrypted_password("Social Login Key", provider.name, "client_secret")
		if not client_secret:
			continue

		icon = None
		if provider.icon:
			if provider.provider_name == "Custom":
				icon = get_icon_html(provider.icon, small=True)
			else:
				icon = f"<img src='{provider.icon}' alt={provider.provider_name}>"

		if provider.client_id and provider.base_url and get_oauth_keys(provider.name):
			out.append(
				{
					"name": provider.name,
					"provider_name": provider.provider_name,
					"auth_url": get_oauth2_authorize_url(provider.name, "/crm"),
					"icon": icon,
				}
			)
	return out

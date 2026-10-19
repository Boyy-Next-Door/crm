import frappe
from bs4 import BeautifulSoup
from frappe import _
from frappe.core.api.file import get_max_file_size
from frappe.translate import get_all_translations
from frappe.utils import cstr, split_emails, validate_email_address

from crm.utils import is_frappe_version


@frappe.whitelist(allow_guest=True)
def get_translations():
	if frappe.session.user != "Guest":
		language = frappe.db.get_value("User", frappe.session.user, "language")
	else:
		language = frappe.db.get_single_value("System Settings", "language")

	return get_all_translations(language)


@frappe.whitelist()
def get_user_signature():
	user = frappe.session.user
	user_email_signature = (
		frappe.db.get_value(
			"User",
			user,
			"email_signature",
		)
		if user
		else None
	)

	signature = user_email_signature or frappe.db.get_value(
		"Email Account",
		{"default_outgoing": 1, "add_signature": 1},
		"signature",
	)

	if not signature:
		return

	soup = BeautifulSoup(signature, "html.parser")
	html_signature = soup.find("div", {"class": "ql-editor read-mode"})
	_signature = None
	if html_signature:
		_signature = html_signature.renderContents()
	content = ""
	if cstr(_signature) or signature:
		content = f'<br><p class="signature">{signature}</p>'
	return content


def check_app_permission():
	if frappe.session.user == "Administrator":
		return True

	allowed_modules = []

	if is_frappe_version("15"):
		allowed_modules = frappe.config.get_modules_from_all_apps_for_user()
	elif is_frappe_version("16", above=True):
		from frappe.utils.modules import get_modules_from_all_apps_for_user

		allowed_modules = get_modules_from_all_apps_for_user()

	allowed_modules = [x["module_name"] for x in allowed_modules]
	if "FCRM" not in allowed_modules:
		return False

	roles = frappe.get_roles()
	if any(role in ["System Manager", "Sales User", "Sales Manager"] for role in roles):
		return True

	return False


def _redirect(location: str):
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = location


@frappe.whitelist(allow_guest=True)
def accept_invitation(key: str | None = None):
	"""Land an invitee in the CRM, or on the login page -- never on a traceback.

	This is reached by clicking a link in an email, so the caller is a person,
	not code. `frappe.throw` here renders a raw 417 stack trace that tells them
	nothing actionable, and the observed response is to click the link again and
	again. Every failure mode -- key already used, expired, or never valid --
	has the same correct next step: the login page.
	"""
	from crm.fcrm.doctype.crm_invitation.crm_invitation import user_has_password

	if not key:
		return _redirect("/login")

	result = frappe.db.get_all("CRM Invitation", filters={"key": key}, pluck="name")
	if not result:
		return _redirect("/login")

	invitation = frappe.get_doc("CRM Invitation", result[0])

	# A second click on an already-accepted invitation is expected, not an
	# error: the key deliberately outlives acceptance until the user has set a
	# password (see CRMInvitation.accept). accept() throws on anything but
	# Pending, so skip it and just restore their session.
	if invitation.status == "Pending":
		invitation.accept()
		invitation.reload()

	if invitation.status != "Accepted":
		return _redirect("/login")

	# Once a password exists the link has outlived its purpose, whoever set it
	# (this flow, an admin, or forgot-password). Retire it here too, not just in
	# set_own_password -- otherwise an old invitation email stays a standing
	# credential that hands out sessions forever.
	if user_has_password(invitation.email):
		frappe.db.set_value("CRM Invitation", invitation.name, "key", None)
		# Frappe only auto-commits write methods; this is a GET, so without an
		# explicit commit the key survives the request and the link keeps
		# working. (The branch below gets away with it only because login_as
		# commits a session as a side effect.)
		frappe.db.commit()
		return _redirect("/login")

	frappe.local.login_manager.login_as(invitation.email)
	return _redirect("/crm")


@frappe.whitelist()
def invite_by_email(emails: str, role: str):
	frappe.only_for(["Sales Manager", "System Manager"], True)

	user_roles = frappe.get_roles(frappe.session.user)

	if role == "System Manager" and "System Manager" not in user_roles:
		frappe.throw(_("You are not allowed to invite System Managers"), frappe.PermissionError)

	if role == "Sales Manager" and "System Manager" not in user_roles:
		frappe.throw(_("You are not allowed to invite Sales Managers"), frappe.PermissionError)

	if role not in ["System Manager", "Sales Manager", "Sales User"]:
		frappe.throw(_("Cannot invite for this role"), frappe.PermissionError)

	if not emails:
		return

	email_string = validate_email_address(emails, throw=False)
	email_list = split_emails(email_string)
	if not email_list:
		return
	existing_members = frappe.db.get_all("User", filters={"email": ["in", email_list]}, pluck="email")
	existing_invites = frappe.db.get_all(
		"CRM Invitation",
		filters={
			"email": ["in", email_list],
			"role": ["in", ["System Manager", "Sales Manager", "Sales User"]],
		},
		pluck="email",
	)

	to_invite = list(set(email_list) - set(existing_members) - set(existing_invites))

	for email in to_invite:
		frappe.get_doc(doctype="CRM Invitation", email=email, role=role).insert(ignore_permissions=True)

	return {
		"existing_members": existing_members,
		"existing_invites": existing_invites,
		"to_invite": to_invite,
	}


@frappe.whitelist(methods=["DELETE", "POST"])
def delete_attachment(doctype: str, docname: str, file_url: str):
	if not frappe.has_permission(doctype, doc=docname, ptype="write"):
		frappe.throw(_("You don't have permission to delete this attachment"), frappe.PermissionError)

	file_name = frappe.db.get_value(
		"File",
		{"file_url": file_url, "attached_to_doctype": doctype, "attached_to_name": docname},
		"name",
	)
	if file_name:
		frappe.delete_doc("File", file_name)


@frappe.whitelist()
def get_file_uploader_defaults(doctype: str):
	max_number_of_files = None
	make_attachments_public = False
	if doctype:
		meta = frappe.get_meta(doctype)
		max_number_of_files = meta.get("max_attachments")
		make_attachments_public = meta.get("make_attachments_public")

	return {
		"allowed_file_types": frappe.get_system_settings("allowed_file_extensions"),
		"max_file_size": get_max_file_size(),
		"max_number_of_files": max_number_of_files,
		"make_attachments_public": bool(make_attachments_public),
	}

# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class CRMInvitation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		accepted_at: DF.Datetime | None
		email: DF.Data
		email_sent_at: DF.Datetime | None
		invited_by: DF.Link | None
		key: DF.Data | None
		role: DF.Literal["", "Sales User", "Sales Manager", "System Manager"]
		status: DF.Literal["", "Pending", "Accepted", "Expired"]
	# end: auto-generated types

	def before_insert(self):
		frappe.utils.validate_email_address(self.email, True)

		self.key = frappe.generate_hash(length=12)
		self.invited_by = frappe.session.user
		self.status = "Pending"

	def after_insert(self):
		self.invite_via_email()

	def invite_via_email(self):
		invite_link = frappe.utils.get_url(f"/api/method/crm.api.accept_invitation?key={self.key}")
		if frappe.local.dev_server:
			print(f"Invite link for {self.email}: {invite_link}")  # nosemgrep

		title = "Frappe CRM"
		template = "crm_invitation"

		frappe.sendmail(
			recipients=self.email,
			subject=_("You have been invited to join {0}").format(title),
			template=template,
			args={"title": title, "invite_link": invite_link},
			now=True,
		)
		self.db_set("email_sent_at", frappe.utils.now())

	@frappe.whitelist()
	def accept_invitation(self):
		frappe.only_for(["System Manager", "Sales Manager"], True)
		self.accept()

	def accept(self):
		if self.status != "Pending":
			frappe.throw(_("Invalid or expired key"))

		is_new_user = not frappe.db.exists("User", self.email)
		user = self.create_user_if_not_exists()

		# Force the user's language to match the site's default (typically zh),
		# even if they're an existing user who previously had English. This
		# ensures a consistent language experience for all CRM access, whether
		# they're freshly invited or re-invited after being removed.
		default_lang = (
			frappe.db.get_single_value("System Settings", "language") or "zh"
		)

		frappe.logger().info(f"[CRM Invitation] accept: email={self.email}, is_new_user={is_new_user}, user.language before={user.language!r}, default_lang={default_lang!r}")

		if user.language != default_lang:
			frappe.logger().info(f"[CRM Invitation] Setting language from {user.language!r} to {default_lang!r}")
			user.language = default_lang

		user.append_roles(self.role)
		if self.role == "System Manager":
			user.append_roles("Sales Manager", "Sales User")
		elif self.role == "Sales Manager":
			user.append_roles("Sales User")
		if self.role == "Sales User":
			self.update_module_in_user(user, "FCRM")
		user.save(ignore_permissions=True)

		# Verify it stuck
		frappe.logger().info(f"[CRM Invitation] After save: user.language={user.language!r}, DB check={frappe.db.get_value('User', self.email, 'language')!r}")

		# Flag the user so the frontend can force them through a password-set
		# flow on first CRM load. Only for accounts we just created via the
		# invite flow — pre-existing users already have a password.
		if is_new_user:
			frappe.db.set_value("User", user.name, "require_password_reset", 1)

		self.status = "Accepted"
		self.accepted_at = frappe.utils.now()
		self.key = None
		self.save(ignore_permissions=True)

	def update_module_in_user(self, user, module):
		block_modules = frappe.get_all(
			"Module Def",
			fields=["name as module"],
			filters={"name": ["!=", module]},
		)

		if block_modules:
			user.set("block_modules", block_modules)

	def create_user_if_not_exists(self):
		if not frappe.db.exists("User", self.email):
			first_name = self.email.split("@")[0].title()
			# Inherit the site's default language (see System Settings.language,
			# which the CRM install hook forces to Simplified Chinese). Falling
			# back to "zh" so a freshly invited user never lands on an
			# untranslated English UI just because System Settings hasn't been
			# read yet.
			default_lang = (
				frappe.db.get_single_value("System Settings", "language") or "zh"
			)
			user = frappe.get_doc(
				doctype="User",
				user_type="System User",
				email=self.email,
				send_welcome_email=0,
				first_name=first_name,
				language=default_lang,
			).insert(ignore_permissions=True)
		else:
			user = frappe.get_doc("User", self.email)
		return user


def expire_invitations():
	"""expire invitations after 3 days"""
	from frappe.utils import add_days, now

	days = 3
	invitations_to_expire = frappe.db.get_all(
		"CRM Invitation", filters={"status": "Pending", "creation": ["<", add_days(now(), -days)]}
	)
	for invitation in invitations_to_expire:
		invitation = frappe.get_doc("CRM Invitation", invitation.name)
		invitation.status = "Expired"
		invitation.save(ignore_permissions=True)

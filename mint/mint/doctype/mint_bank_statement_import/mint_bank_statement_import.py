# Copyright (c) 2025, The Commit Company (Algocode Technologies Pvt. Ltd.) and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class MintBankStatementImport(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from mint.mint.doctype.mint_bank_statement_import_transactions.mint_bank_statement_import_transactions import MintBankStatementImportTransactions

		amended_from: DF.Link | None
		bank_account: DF.Link
		currency: DF.Link | None
		error: DF.Code | None
		file: DF.Attach | None
		file_type: DF.Literal["PDF"]
		status: DF.Literal["Not Started", "Completed", "Error"]
		transactions: DF.Table[MintBankStatementImportTransactions]
	# end: auto-generated types

	def before_validate(self):

		account = frappe.get_cached_value("Bank Account", self.bank_account, "account")
		self.currency = frappe.get_cached_value("Account", account, "account_currency")
		# For all string amounts, compute the actual amount and type
		for transaction in self.transactions:
			if transaction.string_amount:
				amount, tx_type = self.parse_string_amount(transaction.string_amount)
				transaction.amount = amount
				transaction.type = tx_type

	def parse_string_amount(self, string_amount: str):
		"""
		Parse the string amount and return the amount and type
		"""
		# If the string has "cr" - then it's a deposit. Else it's a withdrawal
		if "cr" in string_amount.lower():
			return string_amount.lower().replace("cr", "").replace(" ", ""), "Deposit"
		else:
			return string_amount.lower().replace("dr", "").replace(" ", ""), "Withdrawal"

	
	@frappe.whitelist()
	def process_file(self):

		if not self.file:
			frappe.throw(_("Please upload a file"))

		if self.file_type == "PDF":
			self.process_pdf()
		else:
			frappe.throw(_("Invalid file type"))
	
	def process_pdf(self):
		"""
		Process the PDF using Google Document AI and extract the transactions.
		"""
		from mint.apis.google_ai import run_bank_statement_processor
		
		transactions = run_bank_statement_processor(self.file)
		# Order the transactions by date
		transactions.sort(key=lambda x: frappe.utils.getdate(x.get("date")))
		self.transactions = []
		for transaction in transactions:
			self.append("transactions", {
				"date": transaction.get("date"),
				"amount": transaction.get("amount"),
				"type": transaction.get("type"),
				"description": transaction.get("description")
			})
	
	def before_submit(self):
		# Validate all rows have an amount and a type
		for transaction in self.transactions:
			if not transaction.get("amount") or not transaction.get("type"):
				frappe.throw(_("All rows must have an amount and a type. Missing in row {0}").format(transaction.get("idx")))
		
	def on_submit(self):
		if not self.transactions:
			frappe.throw(_("No transactions found"))

		from mint.apis.statement_import import get_transaction_key

		dates = [transaction.date for transaction in self.transactions if transaction.date]
		filters = {"bank_account": self.bank_account, "docstatus": ["!=", 2]}
		if dates:
			filters["date"] = ["between", [min(dates), max(dates)]]

		existing_transaction_keys = {
			get_transaction_key(row.date, row.withdrawal, row.deposit, row.reference_number, row.description)
			for row in frappe.get_all("Bank Transaction", filters=filters, fields=["date", "withdrawal", "deposit", "reference_number", "description"])
		}

		for transaction in self.transactions:
			# Rows already imported in a previous submission of this document (e.g. before it was
			# cancelled and amended) should not be re-inserted.
			if transaction.get("imported"):
				continue

			withdrawal = transaction.get("amount") if transaction.get("type") == "Withdrawal" else 0
			deposit = transaction.get("amount") if transaction.get("type") == "Deposit" else 0
			transaction_key = get_transaction_key(transaction.get("date"), withdrawal, deposit, transaction.get("reference"), transaction.get("description"))

			if transaction_key in existing_transaction_keys:
				transaction.imported = 1
				continue

			bank_tx = frappe.get_doc({
				"doctype": "Bank Transaction",
				"date": transaction.get("date"),
				"status": "Unreconciled",
				"bank_account": self.bank_account,
				"withdrawal": withdrawal,
				"deposit": deposit,
				"description": transaction.get("description"),
				"reference_number": transaction.get("reference"),
				"currency": self.currency,
			})
			bank_tx.insert()
			bank_tx.submit()
			existing_transaction_keys.add(transaction_key)
			transaction.imported = 1


		

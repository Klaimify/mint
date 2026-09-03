# Copyright (c) 2026, The Commit Company (Algocode Technologies Pvt. Ltd.) and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class MintInvoiceFilterField(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		document_type: DF.Literal["Both", "Sales Invoice", "Purchase Invoice"]
		fieldname: DF.Data
		fieldtype: DF.Literal["Data", "Link", "Select", "Date", "Int", "Float", "Check"]
		filter_level: DF.Literal["Invoice", "Item"]
		label: DF.Data
		options: DF.SmallText | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types
	pass

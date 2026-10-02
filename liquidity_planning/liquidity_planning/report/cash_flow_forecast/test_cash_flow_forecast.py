# Copyright (c) 2026, ALYF GmbH and contributors
# For license information, please see license.txt

import frappe
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_first_day, get_last_day, today

from liquidity_planning.liquidity_planning.report.cash_flow_forecast.cash_flow_forecast import (
	CashFlowForecast,
)


def get_forecast():
	forecast = CashFlowForecast(
		frappe._dict(
			company="_Test Company",
			filter_based_on="Date Range",
			period_start_date=get_first_day(today()),
			period_end_date=get_last_day(today()),
			periodicity="Monthly",
			presentation_currency="INR",
		)
	)
	forecast.get_data()
	return forecast


class TestCashFlowForecast(FrappeTestCase):
	def test_closed_orders_are_not_counted(self):
		sales_order = make_sales_order(transaction_date=today())
		purchase_order = create_purchase_order(transaction_date=today())

		before_closing = get_forecast()
		sales_order.update_status("Closed")
		purchase_order.update_status("Closed")
		after_closing = get_forecast()

		self.assertEqual(
			before_closing.sales_orders["total"] - after_closing.sales_orders["total"],
			sales_order.grand_total,
		)
		self.assertEqual(
			before_closing.purchase_orders["total"] - after_closing.purchase_orders["total"],
			purchase_order.grand_total,
		)

# Copyright (c) 2023, ALYF GmbH and contributors
# For license information, please see license.txt

import frappe
from erpnext.accounts.report.financial_statements import (get_columns,
                                                          get_period_list)
from erpnext.accounts.report.utils import convert
from frappe import _
from frappe.utils import today


class LiquidityForecast:
	def __init__(self, filters):
		self.filters = filters

		self.time_periods = get_period_list(
			filters.from_fiscal_year,
			filters.to_fiscal_year,
			filters.period_start_date,
			filters.period_end_date,
			filters.filter_based_on,
			filters.periodicity,
			company=filters.company,
		)

		self.filters.period_start_date = self.time_periods[0]["year_start_date"]
		self.company_filter = (
			{"company": self.filters.company} if self.filters.company else {}
		)

	def run(self):
		return (
			get_columns(
				self.filters.periodicity,
				self.time_periods,
				0,
				company=self.filters.company,
			),
			self.get_data(),
			self.get_message(),
			self.get_chart_data(),
			self.get_report_summary(),
		)

	def get_data(self):
		empty_row = {
			"account": "",
			"indent": 0.0,
			"currency": self.filters.presentation_currency,
		}

		self.calculate_sales_orders_submitted_and_billed()
		self.calculate_sales_orders_scheduled()
		self.calculate_sales_orders()
		self.calculate_sales_invoices()
		self.calculate_income()

		self.calculate_purchase_orders_submitted_and_billed()
		self.calculate_purchase_orders_scheduled()
		self.calculate_purchase_orders()
		self.calcualte_purchase_invoices()
		self.calcualte_salaries()
		self.calculate_expense_claims()
		self.calculate_expenses()

		self.calculate_total_income()
		self.calculate_total_expenses()
		self.calculate_net_cash_flow()

		self.calculate_totals()

		return [
			self.income,
			self.sales_orders,
			self.sales_orders_submitted,
			self.sales_orders_billed,
			self.sales_orders_scheduled,
			self.sales_invoices,
			empty_row,
			self.expenses,
			self.purchase_orders,
			self.purchase_orders_submitted,
			self.purchase_orders_billed,
			self.purchase_orders_scheduled,
			self.purchase_invoices,
			self.salaries,
			self.expense_claims,
			empty_row,
			self.total_income,
			self.total_expenses,
			self.net_cash_flow,
		]

	def calculate_income(self):
		self.income = {
			"account": _("Income"),
			"indent": 0.0,
			"is_group": 1,
			"currency": self.filters.presentation_currency,
			"bold": 1,
		}

		for key in [period["key"] for period in self.time_periods] + ["total"]:
			self.income.update(
				{key: (self.sales_orders.get(key, 0)) + (self.sales_invoices.get(key, 0))}
			)

	def calculate_sales_orders(self):
		self.sales_orders = {
			"account": _("Sales Orders"),
			"indent": 1.0,
			"is_group": 1,
			"currency": self.filters.presentation_currency,
		}

		for key in [period["key"] for period in self.time_periods] + ["total"]:
			self.sales_orders.update(
				{
					key: (self.sales_orders_submitted.get(key, 0))
					+ (self.sales_orders_billed.get(key, 0))
					+ (self.sales_orders_scheduled.get(key, 0))
				}
			)

	def calculate_sales_orders_submitted_and_billed(self):
		self.sales_orders_submitted = {
			"account": _("Sales Orders (Submitted)"),
			"indent": 2.0,
			"currency": self.filters.presentation_currency,
		}

		self.sales_orders_billed = {
			"account": _("Sales Orders (Billed)"),
			"indent": 2.0,
			"currency": self.filters.presentation_currency,
		}

		filters = self.company_filter.copy()

		amount_submitted_total = 0.0
		amount_billed_total = 0.0

		for period in self.time_periods:
			amount_submitted = 0.0
			amount_billed = 0.0

			filters.update(
				{
					"status": ["not in", "Draft, Cancelled"],
					"transaction_date": [
						"between",
						[period["from_date"], period["to_date"]],
					],
				}
			)

			sales_orders = frappe.get_all(
				"Sales Order",
				filters=filters,
				fields=[
					"name",
					"grand_total",
					"per_billed",
					"currency",
				],
			)

			for sales_order in sales_orders:
				amount_submitted_tmp = sales_order["grand_total"]
				amount_billed_tmp = sales_order["grand_total"] * sales_order["per_billed"] / 100

				if self.filters.presentation_currency != sales_order.currency:
					amount_submitted_tmp = convert(
						amount_submitted_tmp,
						self.filters.presentation_currency,
						sales_order.currency,
						today(),
					)
					amount_billed_tmp = convert(
						amount_billed_tmp,
						self.filters.presentation_currency,
						sales_order.currency,
						today(),
					)

				amount_submitted += amount_submitted_tmp
				amount_submitted_total += amount_submitted_tmp
				amount_billed -= amount_billed_tmp
				amount_billed_total -= amount_billed_tmp

				self.sales_orders_submitted.update({period["key"]: amount_submitted})
				self.sales_orders_billed.update({period["key"]: amount_billed})

		self.sales_orders_submitted.update({"total": amount_submitted_total})
		self.sales_orders_billed.update({"total": amount_billed_total})

	def calculate_sales_orders_scheduled(self):
		self.sales_orders_scheduled = {
			"account": _("Sales Orders (Scheduled)"),
			"indent": 2.0,
			"currency": self.filters.presentation_currency,
		}

		amount_total = 0.0

		for period in self.time_periods:
			amount = 0.0

			filters = {
				"status": ["=", "Active"],
				"reference_doctype": ["=", "Sales Order"],
			}

			auto_repeats = frappe.get_all(
				"Auto Repeat",
				filters=filters,
				fields=[
					"name",
					"reference_document",
				],
			)

			for auto_repeat in auto_repeats:
				auto_repeat_doc = frappe.get_doc("Auto Repeat", auto_repeat.name)
				sales_order = frappe.get_doc("Sales Order", auto_repeat.reference_document)

				if self.filters.company and sales_order.company != self.filters.company:
					break

				schedule_details = auto_repeat_doc.get_auto_repeat_schedule()

				amount_tmp = 0.0

				for schedule_detail in schedule_details:
					if (
						period["from_date"] <= schedule_detail["next_scheduled_date"] <= period["to_date"]
					):
						amount_tmp += sales_order.grand_total

				if self.filters.presentation_currency != sales_order.currency:
					amount_tmp = convert(
						amount_tmp,
						self.filters.presentation_currency,
						sales_order.currency,
						today(),
					)

				amount += amount_tmp
				amount_total += amount_tmp

				self.sales_orders_scheduled.update({period["key"]: amount})

		self.sales_orders_scheduled.update({"total": amount_total})

	def calculate_sales_invoices(self):
		self.sales_invoices = {
			"account": _("Sales Invoices"),
			"indent": 1.0,
			"currency": self.filters.presentation_currency,
		}

		filters = self.company_filter.copy()

		amount_total = 0.0

		for period in self.time_periods:
			amount = 0.0

			filters.update(
				{
					"status": ["not in", "Draft, Cancelled"],
					"due_date": [
						"between",
						[period["from_date"], period["to_date"]],
					],
				}
			)

			sales_invoices = frappe.get_all(
				"Sales Invoice",
				filters=filters,
				fields=[
					"name",
					"grand_total",
					"currency",
				],
			)

			for sales_invoice in sales_invoices:
				amount_tmp = sales_invoice["grand_total"]

				if self.filters.presentation_currency != sales_invoice.currency:
					amount_tmp = convert(
						amount_tmp,
						self.filters.presentation_currency,
						sales_invoice.currency,
						today(),
					)

				amount += amount_tmp
				amount_total += amount_tmp

				self.sales_invoices.update({period["key"]: amount})

		self.sales_invoices.update({"total": amount_total})

	def calculate_expenses(self):
		self.expenses = {
			"account": _("Expenses"),
			"indent": 0.0,
			"is_group": 1,
			"currency": self.filters.presentation_currency,
			"bold": 1,
		}

		for key in [period["key"] for period in self.time_periods] + ["total"]:
			self.expenses.update(
				{
					key: (self.purchase_orders.get(key, 0))
					+ (self.purchase_invoices.get(key, 0))
					+ (self.salaries.get(key, 0))
					+ (self.expense_claims.get(key, 0))
				}
			)

	def calculate_purchase_orders(self):
		self.purchase_orders = {
			"account": _("Purchase Orders"),
			"indent": 1.0,
			"is_group": 1,
			"currency": self.filters.presentation_currency,
		}

		for key in [period["key"] for period in self.time_periods] + ["total"]:
			self.purchase_orders.update(
				{
					key: (self.purchase_orders_submitted.get(key, 0))
					+ (self.purchase_orders_billed.get(key, 0))
					+ (self.purchase_orders_scheduled.get(key, 0))
				}
			)

	def calculate_purchase_orders_submitted_and_billed(self):
		self.purchase_orders_submitted = {
			"account": _("Purchase Orders (Submitted)"),
			"indent": 2.0,
			"currency": self.filters.presentation_currency,
		}

		self.purchase_orders_billed = {
			"account": _("Purchase Orders (Billed)"),
			"indent": 2.0,
			"currency": self.filters.presentation_currency,
		}

		filters = self.company_filter.copy()

		amount_submitted_total = 0.0
		amount_billed_total = 0.0

		for period in self.time_periods:
			amount_submitted = 0.0
			amount_billed = 0.0

			filters.update(
				{
					"status": ["not in", "Draft, Cancelled"],
					"transaction_date": [
						"between",
						[period["from_date"], period["to_date"]],
					],
				}
			)

			purchase_orders = frappe.get_all(
				"Purchase Order",
				filters=filters,
				fields=[
					"name",
					"grand_total",
					"per_billed",
					"currency",
				],
			)

			for purchase_order in purchase_orders:
				amount_submitted_tmp = purchase_order["grand_total"]
				amount_billed_tmp = (
					purchase_order["grand_total"] * purchase_order["per_billed"] / 100
				)

				if self.filters.presentation_currency != purchase_order.currency:
					amount_submitted_tmp = convert(
						amount_submitted_tmp,
						self.filters.presentation_currency,
						purchase_order.currency,
						today(),
					)
					amount_billed_tmp = convert(
						amount_billed_tmp,
						self.filters.presentation_currency,
						purchase_order.currency,
						today(),
					)

				amount_submitted += amount_submitted_tmp
				amount_submitted_total += amount_submitted_tmp
				amount_billed -= amount_billed_tmp
				amount_billed_total -= amount_billed_tmp

				self.purchase_orders_submitted.update({period["key"]: amount_submitted})
				self.purchase_orders_billed.update({period["key"]: amount_billed})

		self.purchase_orders_submitted.update({"total": amount_submitted_total})
		self.purchase_orders_billed.update({"total": amount_billed_total})

	def calculate_purchase_orders_scheduled(self):
		self.purchase_orders_scheduled = {
			"account": _("Purchase Orders (Scheduled)"),
			"indent": 2.0,
			"currency": self.filters.presentation_currency,
		}

		amount_total = 0.0

		for period in self.time_periods:
			amount = 0.0

			filters = {
				"status": ["=", "Active"],
				"reference_doctype": ["=", "Purchase Order"],
			}

			auto_repeats = frappe.get_all(
				"Auto Repeat",
				filters=filters,
				fields=[
					"name",
					"reference_document",
				],
			)

			for auto_repeat in auto_repeats:
				auto_repeat_doc = frappe.get_doc("Auto Repeat", auto_repeat.name)
				purchase_order = frappe.get_doc("Purchase Order", auto_repeat.reference_document)

				if self.filters.company and purchase_order.company != self.filters.company:
					break

				schedule_details = auto_repeat_doc.get_auto_repeat_schedule()

				amount_tmp = 0.0

				for schedule_detail in schedule_details:
					if (
						period["from_date"] <= schedule_detail["next_scheduled_date"] <= period["to_date"]
					):
						amount_tmp += purchase_order.grand_total

				if self.filters.presentation_currency != purchase_order.currency:
					amount_tmp = convert(
						amount_tmp,
						self.filters.presentation_currency,
						purchase_order.currency,
						today(),
					)

				amount += amount_tmp
				amount_total += amount_tmp

				self.purchase_orders_scheduled.update({period["key"]: amount})

		self.purchase_orders_scheduled.update({"total": amount_total})

	def calcualte_purchase_invoices(self):
		self.purchase_invoices = {
			"account": _("Purchase Invoices"),
			"indent": 1.0,
			"currency": self.filters.presentation_currency,
		}

		filters = self.company_filter.copy()

		amount_total = 0.0

		for period in self.time_periods:
			amount = 0.0

			filters.update(
				{
					"status": ["not in", "Draft, Cancelled"],
					"due_date": [
						"between",
						[period["from_date"], period["to_date"]],
					],
				}
			)

			purchase_invoices = frappe.get_all(
				"Purchase Invoice",
				filters=filters,
				fields=[
					"name",
					"grand_total",
					"currency",
				],
			)

			for purchase_invoice in purchase_invoices:
				amount_tmp = purchase_invoice["grand_total"]

				if self.filters.presentation_currency != purchase_invoice.currency:
					amount_tmp = convert(
						amount_tmp,
						self.filters.presentation_currency,
						purchase_invoice.currency,
						today(),
					)

				amount += amount_tmp
				amount_total += amount_tmp

				self.purchase_invoices.update({period["key"]: amount})

		self.purchase_invoices.update({"total": amount_total})

	def calcualte_salaries(self):
		self.salaries = {
			"account": _("Salaries"),
			"indent": 1.0,
			"currency": self.filters.presentation_currency,
		}

		filters = self.company_filter.copy()
		filters.update(
			{
				"ctc": ["!=", ""],
			}
		)

		employees = frappe.get_all(
			"Employee",
			filters=filters,
			fields=[
				"name",
				"ctc",
				"salary_currency",
				"date_of_joining",
				"relieving_date",
			],
		)

		amount_total = 0.0

		for period in self.time_periods:
			amount = 0.0

			for employee in employees:
				if employee["date_of_joining"] > period["to_date"]:
					continue
				if employee["relieving_date"] and employee["relieving_date"] < period["from_date"]:
					continue

				start_date = max(employee.date_of_joining, period.from_date)
				end_date = min(employee.relieving_date or period.to_date, period.to_date)
				tmp = ((end_date - start_date).days + 1) / 30.438302988666667 * employee.ctc
				if self.filters.presentation_currency != employee.salary_currency:
					tmp = convert(
						tmp,
						self.filters.presentation_currency,
						employee.salary_currency,
						today(),
					)
				amount += tmp
				amount_total += tmp

			self.salaries.update({period["key"]: amount})

		self.salaries.update({"total": amount_total})

	def calculate_expense_claims(self):
		self.expense_claims = {
			"account": _("Expense Claims"),
			"indent": 1.0,
			"currency": self.filters.presentation_currency,
		}

		filters = self.company_filter.copy()

		amount_total = 0.0

		for period in self.time_periods:
			amount = 0.0

			filters.update(
				{
					"status": ["not in", "Rejected, Cancelled"],
					"posting_date": [
						"between",
						[period["from_date"], period["to_date"]],
					],
				}
			)

			expense_claims = frappe.get_all(
				"Expense Claim",
				filters=filters,
				fields=[
					"name",
					"total_claimed_amount",
					"company",
				],
			)

			for expense_claim in expense_claims:
				amount_tmp = expense_claim["total_claimed_amount"]

				currency = frappe.get_value("Company", expense_claim.company, "default_currency")

				if self.filters.presentation_currency != currency:
					amount_tmp = convert(
						amount_tmp,
						self.filters.presentation_currency,
						currency,
						today(),
					)

				amount += amount_tmp
				amount_total += amount_tmp

				self.expense_claims.update({period["key"]: amount})

		self.expense_claims.update({"total": amount_total})

	def calculate_total_income(self):
		self.total_income = {
			"account": _("Total Income"),
			"indent": 0.0,
			"currency": self.filters.presentation_currency,
			"bold": 1,
		}

		for key in [period["key"] for period in self.time_periods] + ["total"]:
			self.total_income.update({key: self.income.get(key, 0)})

	def calculate_total_expenses(self):
		self.total_expenses = {
			"account": _("Total Expenses"),
			"indent": 0.0,
			"currency": self.filters.presentation_currency,
			"bold": 1,
		}

		for key in [period["key"] for period in self.time_periods] + ["total"]:
			self.total_expenses.update({key: self.expenses.get(key, 0)})

	def calculate_net_cash_flow(self):
		self.net_cash_flow = {
			"account": _("Net Cash Flow"),
			"indent": 0.0,
			"currency": self.filters.presentation_currency,
			"warn_if_negative": 1,
			"bold": 1,
		}

		for key in [period["key"] for period in self.time_periods] + ["total"]:
			self.net_cash_flow.update(
				{key: (self.income.get(key, 0) - self.expenses.get(key, 0))}
			)

	def calculate_totals(self):
		pass

	def get_message(self):
		return None

	def get_chart_data(self):
		labels = [period["label"] for period in self.time_periods]

		if self.filters.periodicity != "Yearly":
			labels += ["Total"]

		income_values = []
		expense_values = []
		net_cash_flow_values = []

		for key in [period["key"] for period in self.time_periods] + ["total"]:
			income_values.append(f"{self.total_income.get(key, 0):.2f}")
			expense_values.append(f"{self.total_expenses.get(key, 0):.2f}")
			net_cash_flow_values.append(f"{self.net_cash_flow.get(key, 0):.2f}")

		datasets = [
			{"name": "Income", "values": income_values},
			{"name": "Expenses", "values": expense_values},
			{"name": "Net Cash Flow", "values": net_cash_flow_values},
		]

		chart = {"data": {"labels": labels, "datasets": datasets}}
		chart["type"] = "bar"

		return chart

	def get_report_summary(self):
		return [
			{
				"value": self.total_income.get("total", 0),
				"label": "Income",
				"datatype": "Currency",
				"currency": self.filters.presentation_currency,
			},
			{
				"value": self.total_expenses.get("total", 0),
				"label": "Expenses",
				"datatype": "Currency",
				"currency": self.filters.presentation_currency,
			},
			{
				"value": self.net_cash_flow.get("total", 0),
				"label": "Net Cash Flow",
				"indicator": "Red" if self.net_cash_flow.get("total", 0) < 0 else "Green",
				"datatype": "Currency",
				"currency": self.filters.presentation_currency,
			},
		]


def execute(filters=None):
	return LiquidityForecast(filters).run()

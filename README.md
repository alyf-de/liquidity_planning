### Liquidity Planning

This app provides a report named "Cash Flow Forecast" that can be used for liquidity planning in ERPNext.

### Installation

You can install this app on you ERPNext instance using the [bench CLI](https://github.com/frappe/bench):

```bash
bench get-app https://github.com/alyf-de/liquidity_planning.git
bench --site $MY_SITE install-app liquidity_planning
```

### Description

The "Cash Flow Forecast" report offers a detailed forecast of an organization's cash flow, providing insights into its financial health. This section explains the data sources and methodology behind the report.

#### Data Sources

The report derives its data from various ERPNext modules, as outlined below:

Income:

1. Outstanding submitted **Sales Orders**, as well as scheduled **Sales Orders** using the "Auto Repeat" feature.
2. Submitted **Sales Invoices**.

Expenses:

4. Outstanding submitted **Purchase Orders**, as well as scheduled **Purchase Orders** using the "Auto Repeat" feature.
5. Submitted **Sales Invoices**.
6. Employee Salaries, calculated based on the _Cost To Company_ (`ctc`) field from the **Employee** DocType, considering joining and relieving dates.
7. Approved **Expense Claims**.

#### Calculation Methods

- The report calculates total income and expenses by aggregating values from sales and purchase orders, invoices, salaries, and expense claims.
- Net cash flow is determined by subtracting total expenses from total income.
- Currency conversions are applied where necessary, based on the presentation currency selected by the user.

#### Report Filters

Users can customize the report using various filters:

- **Company**: To select the specific company for the report.
- **Filter Based On**: Choose between 'Date Range' or 'Fiscal Year'.
- **Periodicity**: Select the frequency of the report (Monthly, Quarterly, Half-Yearly, Yearly).
- **Currency**: Choose the presentation currency (e.g. EUR, USD).

### License

Copyright (C) 2023  ALYF GmbH and contributors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

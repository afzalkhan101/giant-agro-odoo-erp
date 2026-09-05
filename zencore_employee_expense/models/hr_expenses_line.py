from odoo import api, fields, models


class HrExpenseLine(models.Model):
    _name = "hr.expense.line"
    _description = "Monthly Expense Line"
    _order = "expense_date, id"

    expense_id = fields.Many2one(
        "hr.expense",
        string="Monthly Expense",
        required=True,
        ondelete="cascade",
    )

    company_id = fields.Many2one(
        "res.company",
        related="expense_id.company_id",
        store=True,
        readonly=True,
    )

    expense_date = fields.Date(
        string="Date",
        required=True,
    )

    description = fields.Char(
        string="Description",
        required=True,
    )

    category_id = fields.Many2one(
        "product.product",
        string="Expense Category",
        required=True,
        domain="[('can_be_expensed', '=', True)]",
    )

    account_id = fields.Many2one(
        "account.account",
        string="Expense Account",
        compute="_compute_account_id",
        readonly=True,
    )

    amount = fields.Monetary(
        string="Amount",
        required=True,
        currency_field="currency_id",
    )

    currency_id = fields.Many2one(
        "res.currency",
        related="expense_id.currency_id",
        readonly=True,
    )

    @api.depends(
        "category_id",
        "expense_id.company_id",
    )
    def _compute_account_id(self):
        for line in self:
            line.account_id = False

            if not line.category_id:
                continue

            company = (
                line.expense_id.company_id
                or self.env.company
            )

            product = line.category_id.with_company(company)

            accounts = product._get_product_accounts()

            line.account_id = accounts.get("expense")
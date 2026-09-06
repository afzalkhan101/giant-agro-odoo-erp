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


    currency_id = fields.Many2one(
        "res.currency",
        related="expense_id.currency_id",
        store=True,
        readonly=True,
    )


    expense_date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
    )


    description = fields.Char(
        string="Description",
        required=True,
    )


    category_id = fields.Many2one(
        "product.product",
        string="Expense Category",
        required=True,
        domain=[
            ("can_be_expensed", "=", True)
        ],
    )


    account_id = fields.Many2one(
        "account.account",
        string="Expense Account",
        compute="_compute_account_id",
        store=True,
        readonly=True,
    )


    amount = fields.Monetary(
        string="Amount",
        required=True,
        currency_field="currency_id",
    )


    document = fields.Binary(
        string="Document",
        attachment=True,
    )


    document_filename = fields.Char(
        string="Document Filename",
    )



    @api.depends(
        "category_id",
        "company_id",
    )
    def _compute_account_id(self):

        for line in self:

            line.account_id = False


            if not line.category_id:
                continue


            product = line.category_id.with_company(
                line.company_id
            )


            accounts = product._get_product_accounts()


            line.account_id = accounts.get(
                "expense"
            )
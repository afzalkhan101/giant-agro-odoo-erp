from odoo import fields, models


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    monthly_expense_line_ids = fields.One2many(
        'hr.expense.line',
        'expense_id',
        string='Monthly Expense Lines',
        copy=True,
    )

    date = fields.Date(
        string="Expense Date",
        default=False,
    )

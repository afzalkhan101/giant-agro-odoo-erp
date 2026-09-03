
from odoo import api, fields, models

class HrExpenseLine(models.Model):

    _name ="hr.expense.line"
    _description = 'Monthly Expense Line '


    expense_id = fields.Many2one(
        'hr.expense',
        string='Monthly Expense',
        required=True,
        ondelete='cascade',
    )

    expense_date = fields.Date(
        string='Date',
        required=True,
    )

    description = fields.Char(
        string='Description',
        required=True,
    )

    category_id = fields.Many2one(
        'product.product',
        string='Expense Category',
        required=True,
    )


    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id',
    )

    currency_id = fields.Many2one(
        related='expense_id.currency_id',
        store=True,
        readonly=True,
    )
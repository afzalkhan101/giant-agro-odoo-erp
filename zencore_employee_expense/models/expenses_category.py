from odoo import fields, models
from odoo import api
from odoo import models, _
from odoo.exceptions import ValidationError



class HrExpenseCategory(models.Model):
    _inherit = "product.product"

    account_payable_id = fields.Many2one(
        "account.account",
        string="Account Payable",
    )


    
class HrExpense(models.Model):
    _inherit = "hr.expense"

    def action_submit(self):
        for expense in self:
            if expense.monthly_expense_line_ids:

                monthly_total = sum(
                    expense.monthly_expense_line_ids.mapped("amount")
                )
                if expense.currency_id.is_zero(monthly_total):
                    raise ValidationError(
                        _("Monthly Expense Total must be greater than 0.")
                    )
                
                expense.total_amount_currency = monthly_total
                expense._compute_total_amount()

        return super().action_submit()
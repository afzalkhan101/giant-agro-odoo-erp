from odoo import fields, models, Command, _
from odoo.exceptions import UserError
from odoo import models, _
from odoo.exceptions import ValidationError


class HrExpense(models.Model):
    _inherit = "hr.expense"

    monthly_expense_line_ids = fields.One2many(
        "hr.expense.line",
        "expense_id",
        string="Monthly Expense Lines",
    )

    
    def _sync_monthly_expense_total(self):

        for expense in self:

            if not expense.monthly_expense_line_ids:
                continue

            total = sum(
                expense.monthly_expense_line_ids.mapped(
                    "amount"
                )
            )

            if expense.currency_id.is_zero(total):
                raise ValidationError(
                    _(
                        "Monthly Expense Total must be greater than 0."
                    )
                )

            first_line = (
                expense.monthly_expense_line_ids[0]
            )

            vals = {
                "total_amount_currency": total,
                "total_amount": total,
                "quantity": 1.0,
                "price_unit": total,
            }

            if first_line.category_id:
                vals["product_id"] = (
                    first_line.category_id.id
                )

            if first_line.expense_date:
                vals["date"] = (
                    first_line.expense_date
                )

            expense.sudo().write(vals)

        return True

    def action_submit(self):

        for expense in self:

            if expense.monthly_expense_line_ids:
                expense._sync_monthly_expense_total()

        return super().action_submit()


    

    
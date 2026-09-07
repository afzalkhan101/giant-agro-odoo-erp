from odoo import fields, models, Command, _ ,api
from odoo.exceptions import ValidationError


class HrExpense(models.Model):
    _inherit = "hr.expense"

    monthly_expense_line_ids = fields.One2many(
        "hr.expense.line", "expense_id", string="Monthly Expense Lines",
    )


    @api.depends(
        "employee_id",
        "employee_id.department_id",
        "company_id",
        "company_id.expense_admin_id",
    )
    def _compute_from_employee_id(self):
        super()._compute_from_employee_id()

        for expense in self:
            if expense.company_id.expense_admin_id:
                expense.manager_id = expense.company_id.expense_admin_id

    def _sync_monthly_expense_total(self):
        for expense in self:
            if not expense.monthly_expense_line_ids:
                continue
            total = sum(expense.monthly_expense_line_ids.mapped("amount"))
            if expense.currency_id.is_zero(total):
                raise ValidationError(_("Monthly Expense Total must be greater than 0."))
            expense.write({
                "total_amount_currency": total,
                "total_amount": total,
                "quantity": 1,
                "price_unit": total,
            })
        return True

    def action_submit(self):
        self._sync_monthly_expense_total()
        return super().action_submit()

    # =====================================================
    # Category-wise move line split (real hook point in v19)
    # =====================================================

    def _prepare_receipts_vals(self):
        return_vals = super()._prepare_receipts_vals()

        for vals in return_vals:
            new_line_ids = []
            for cmd in vals.get("line_ids", []):
                line_vals = cmd[2]  # Command.create(vals) -> (0, 0, vals)
                expense = self.browse(line_vals.get("expense_id"))

                if expense and expense.monthly_expense_line_ids:
                    for m_line in expense.monthly_expense_line_ids:
                        if not m_line.account_id:
                            raise ValidationError(
                                _("Expense account missing for %s") % m_line.category_id.display_name
                            )
                        split_vals = dict(line_vals)
                        split_vals.update({
                            "name": m_line.description,
                            "account_id": m_line.account_id.id,
                            "price_unit": m_line.amount,
                            "quantity": 1,
                        })
                        new_line_ids.append(Command.create(split_vals))
                else:
                    new_line_ids.append(cmd)

            vals["line_ids"] = new_line_ids

        return return_vals
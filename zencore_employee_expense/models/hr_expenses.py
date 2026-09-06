from odoo import fields, models, _
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
                expense.monthly_expense_line_ids.mapped("amount")
            )


            if expense.currency_id.is_zero(total):
                raise ValidationError(
                    _("Monthly Expense Total must be greater than 0.")
                )


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
    # Custom Journal Entry Creation
    # =====================================================


    def _action_create_account_move(self):

        for expense in self:


            if not expense.monthly_expense_line_ids:

                continue



            move = super()._action_create_account_move()



            if not move:
                continue



            # remove existing expense debit lines

            debit_lines = move.line_ids.filtered(
                lambda l:
                l.debit > 0
            )


            debit_lines.unlink()



            debit_total = 0



            new_lines = []



            # ----------------------------------
            # Category Wise Debit Lines
            # ----------------------------------

            for line in expense.monthly_expense_line_ids:


                if not line.account_id:

                    raise ValidationError(
                        _(
                            "Expense account missing for %s"
                        )
                        %
                        line.category_id.display_name
                    )



                new_lines.append(
                    (
                        0,
                        0,
                        {

                            "name":
                                line.description,


                            "account_id":
                                line.account_id.id,


                            "debit":
                                line.amount,


                            "credit":
                                0,


                        }
                    )
                )


                debit_total += line.amount



            move.write({

                "line_ids":
                    new_lines

            })


        return True
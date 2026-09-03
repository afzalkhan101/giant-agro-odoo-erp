
from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError






class HrExpense(models.Model):
    _inherit = "hr.expense"

    monthly_expense_line_ids = fields.One2many(
        "hr.expense.line",
        "expense_id",
        string="Monthly Expense Lines",
    )

    monthly_journal_id = fields.Many2one(
        "account.journal",
        string="Monthly Expense Journal",
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        default=lambda self: self._default_monthly_journal(),
    )

    @api.model
    def _default_monthly_journal(self):
        return self.env["account.journal"].search(
            [
                ("type", "=", "general"),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )

    def action_post_monthly_expenses(self):
        for expense in self:
            if expense.account_move_id:
                raise UserError(
                    _("Monthly expenses have already been posted.")
                )

            lines = expense.monthly_expense_line_ids

            if not lines:
                raise UserError(
                    _("Please add at least one Monthly Expense Line.")
                )

            if not expense.monthly_journal_id:
                raise UserError(
                    _("Please select a Monthly Expense Journal.")
                )

            # Only employee reimbursement flow
            if expense.payment_mode != "own_account":
                raise UserError(
                    _(
                        "Monthly expense posting currently supports "
                        "'Employee (to reimburse)' only."
                    )
                )

            # ------------------------------------------
            # Validate lines
            # ------------------------------------------
            for line in lines:
                if not line.expense_date:
                    raise UserError(
                        _("Expense Date is required for every line.")
                    )

                if not line.category_id:
                    raise UserError(
                        _("Expense Category is required for every line.")
                    )

                if line.amount <= 0:
                    raise UserError(
                        _(
                            "Amount must be greater than zero for '%s'.",
                            line.description,
                        )
                    )

                if not line.account_id:
                    raise UserError(
                        _(
                            "No Expense Account is configured for category '%s'.",
                            line.category_id.display_name,
                        )
                    )

            # ------------------------------------------
            # All lines must belong to same month
            # ------------------------------------------
            months = {
                (
                    line.expense_date.year,
                    line.expense_date.month,
                )
                for line in lines
            }

            if len(months) > 1:
                raise UserError(
                    _(
                        "All Monthly Expense Lines must belong "
                        "to the same month."
                    )
                )

            # ------------------------------------------
            # Employee Payable Account
            # ------------------------------------------
            employee_partner = (
                expense.employee_id.sudo().work_contact_id
            )

            if not employee_partner:
                raise UserError(
                    _(
                        "No work contact is configured for employee '%s'.",
                        expense.employee_id.name,
                    )
                )

            employee_partner = employee_partner.with_company(
                expense.company_id
            )

            payable_account = (
                employee_partner.property_account_payable_id
                or employee_partner.parent_id.property_account_payable_id
            )

            if not payable_account:
                raise UserError(
                    _(
                        "No Payable Account is configured for employee '%s'.",
                        expense.employee_id.name,
                    )
                )

            company = expense.company_id
            company_currency = company.currency_id
            expense_currency = expense.currency_id

            move_lines = []

            total_currency = 0.0
            total_company = 0.0

            # ------------------------------------------
            # Debit: each Monthly Expense Line
            # ------------------------------------------
            for line in lines:
                company_amount = expense_currency._convert(
                    line.amount,
                    company_currency,
                    company,
                    line.expense_date,
                )

                total_currency += line.amount
                total_company += company_amount

                debit_vals = {
                    "name": line.description,
                    "account_id": line.account_id.id,
                    "debit": company_amount,
                    "credit": 0.0,
                }

                # Multi-currency support
                if expense_currency != company_currency:
                    debit_vals.update({
                        "currency_id": expense_currency.id,
                        "amount_currency": line.amount,
                    })

                move_lines.append(
                    Command.create(debit_vals)
                )

            # ------------------------------------------
            # Credit: Employee Payable
            # ------------------------------------------
            credit_vals = {
                "name": _(
                    "Monthly Expense - %s",
                    expense.employee_id.name,
                ),
                "account_id": payable_account.id,
                "partner_id": employee_partner.id,
                "debit": 0.0,
                "credit": total_company,
            }

            if expense_currency != company_currency:
                credit_vals.update({
                    "currency_id": expense_currency.id,
                    "amount_currency": -total_currency,
                })

            move_lines.append(
                Command.create(credit_vals)
            )

            # Last expense date = journal posting date
            move_date = max(lines.mapped("expense_date"))

            # Hidden standard fields sync রাখা হবে
            expense.write({
                "date": move_date,
                "total_amount_currency": total_currency,
                "total_amount": total_company,
            })

            # ------------------------------------------
            # Create Journal Entry
            # ------------------------------------------
            move = self.env["account.move"].create({
                "move_type": "entry",
                "journal_id": expense.monthly_journal_id.id,
                "date": move_date,
                "ref": _("Monthly Expense - %s", expense.name),
                "company_id": company.id,
                "expense_ids": [Command.set(expense.ids)],
                "line_ids": move_lines,
            })

            # ------------------------------------------
            # Post Journal Entry
            # ------------------------------------------
            move.action_post()

        return True
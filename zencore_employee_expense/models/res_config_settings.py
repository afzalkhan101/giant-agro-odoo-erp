from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    expense_admin_id = fields.Many2one(
        comodel_name="res.users",
        string="Expense Admin",
        related="company_id.expense_admin_id",
        readonly=False,
    )
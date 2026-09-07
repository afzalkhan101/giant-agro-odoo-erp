from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    expense_admin_id = fields.Many2one(
        comodel_name="res.users",
        string="Expense Admin",
        domain=[("share", "=", False)],
        help="User responsible for administering employee expenses.",
    )
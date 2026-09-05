import base64
import mimetypes

from urllib.parse import urlencode

from odoo import Command, fields, http, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request, content_disposition

from odoo.addons.portal.controllers.portal import (
    CustomerPortal,
    pager as portal_pager,
)


class EmployeeExpensePortal(CustomerPortal):

    _items_per_page = 10

    # =========================================================
    # HELPERS
    # =========================================================

    def _get_employee(self):
        return (
            request.env["hr.employee"]
            .sudo()
            .search(
                [
                    (
                        "user_id",
                        "=",
                        request.env.user.id,
                    ),
                ],
                limit=1,
            )
        )

    def _expense_domain(self, employee):

        if not employee:
            return [
                (
                    "id",
                    "=",
                    0,
                ),
            ]

        return [
            (
                "employee_id",
                "=",
                employee.id,
            ),
        ]

    def _get_own_expense(
        self,
        expense_id,
    ):

        employee = self._get_employee()

        if not employee:
            return request.env["hr.expense"]

        return (
            request.env["hr.expense"]
            .sudo()
            .search(
                [
                    (
                        "id",
                        "=",
                        expense_id,
                    ),
                    (
                        "employee_id",
                        "=",
                        employee.id,
                    ),
                ],
                limit=1,
            )
        )

    def _get_categories(
        self,
        employee,
    ):

        if not employee:
            return request.env["product.product"]

        return (
            request.env["product.product"]
            .sudo()
            .search(
                [
                    (
                        "can_be_expensed",
                        "=",
                        True,
                    ),
                    (
                        "active",
                        "=",
                        True,
                    ),
                    "|",
                    (
                        "company_id",
                        "=",
                        False,
                    ),
                    (
                        "company_id",
                        "=",
                        employee.company_id.id,
                    ),
                ],
                order="name",
            )
        )

    def _redirect_message(
        self,
        url,
        message_type,
        message,
    ):

        query = urlencode({
            message_type: str(message),
        })

        return request.redirect(
            "%s?%s" % (
                url,
                query,
            )
        )

    # =========================================================
    # PARSE EXPENSE LINES
    # =========================================================

    def _parse_expense_lines(
        self,
        employee,
    ):

        form = request.httprequest.form

        files = request.httprequest.files

        line_ids = form.getlist(
            "line_id"
        )

        dates = form.getlist(
            "line_expense_date"
        )

        descriptions = form.getlist(
            "line_description"
        )

        categories = form.getlist(
            "line_category_id"
        )

        amounts = form.getlist(
            "line_amount"
        )

        documents = files.getlist(
            "line_document"
        )

        line_count = max(
            len(line_ids),
            len(dates),
            len(descriptions),
            len(categories),
            len(amounts),
            0,
        )

        line_data = []

        total_amount = 0.0

        first_category = False

        first_date = False

        Product = (
            request.env["product.product"]
            .sudo()
        )

        # =====================================================
        # EACH PORTAL ROW
        # =====================================================

        for index in range(
            line_count
        ):

            line_id_value = (
                line_ids[index].strip()
                if index < len(line_ids)
                else ""
            )

            date_value = (
                dates[index].strip()
                if index < len(dates)
                else ""
            )

            description = (
                descriptions[index].strip()
                if index < len(descriptions)
                else ""
            )

            category_value = (
                categories[index].strip()
                if index < len(categories)
                else ""
            )

            amount_value = (
                amounts[index].strip()
                if index < len(amounts)
                else ""
            )

            # -------------------------------------------------
            # Completely blank line
            # -------------------------------------------------

            if not any([
                date_value,
                description,
                category_value,
                amount_value,
            ]):
                continue

            # -------------------------------------------------
            # Date
            # -------------------------------------------------

            if not date_value:
                raise ValidationError(
                    _(
                        "Expense Date is required."
                    )
                )

            try:

                expense_date = (
                    fields.Date.to_date(
                        date_value
                    )
                )

            except Exception:

                raise ValidationError(
                    _(
                        "Invalid Expense Date."
                    )
                )

            # -------------------------------------------------
            # Description
            # -------------------------------------------------

            if not description:
                raise ValidationError(
                    _(
                        "Description is required."
                    )
                )

            # -------------------------------------------------
            # Category
            # -------------------------------------------------

            if not category_value:
                raise ValidationError(
                    _(
                        "Expense Category is required."
                    )
                )

            try:

                category_id = int(
                    category_value
                )

            except (
                TypeError,
                ValueError,
            ):

                raise ValidationError(
                    _(
                        "Invalid Expense Category."
                    )
                )

            category = Product.search(
                [
                    (
                        "id",
                        "=",
                        category_id,
                    ),
                    (
                        "can_be_expensed",
                        "=",
                        True,
                    ),
                    (
                        "active",
                        "=",
                        True,
                    ),
                    "|",
                    (
                        "company_id",
                        "=",
                        False,
                    ),
                    (
                        "company_id",
                        "=",
                        employee.company_id.id,
                    ),
                ],
                limit=1,
            )

            if not category:

                raise ValidationError(
                    _(
                        "Invalid Expense Category."
                    )
                )

            # -------------------------------------------------
            # Amount
            # -------------------------------------------------

            if not amount_value:

                raise ValidationError(
                    _(
                        "Amount is required."
                    )
                )

            try:

                amount = float(
                    amount_value
                )

            except (
                TypeError,
                ValueError,
            ):

                raise ValidationError(
                    _(
                        "Invalid expense amount."
                    )
                )

            if amount <= 0:

                raise ValidationError(
                    _(
                        "Expense amount must "
                        "be greater than 0."
                    )
                )

            # =================================================
            # LINE VALUES
            # =================================================

            vals = {
                "expense_date": (
                    expense_date
                ),

                "description": (
                    description
                ),

                "category_id": (
                    category.id
                ),

                "amount": (
                    amount
                ),
            }

            # =================================================
            # LINE DOCUMENT
            # =================================================

            uploaded_file = False

            if index < len(documents):

                uploaded_file = (
                    documents[index]
                )

            if (
                uploaded_file
                and uploaded_file.filename
            ):

                file_data = (
                    uploaded_file.read()
                )

                if file_data:

                    vals.update({
                        "document": (
                            base64.b64encode(
                                file_data
                            )
                        ),

                        "document_filename": (
                            uploaded_file.filename
                        ),
                    })

            # =================================================
            # EXISTING LINE ID
            # =================================================

            line_id = False

            if line_id_value:

                try:

                    line_id = int(
                        line_id_value
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    raise ValidationError(
                        _(
                            "Invalid expense line."
                        )
                    )

            line_data.append({
                "line_id": line_id,
                "vals": vals,
            })

            total_amount += amount

            if not first_category:
                first_category = category

            if not first_date:
                first_date = expense_date

        # =====================================================
        # REQUIRED LINE
        # =====================================================

        if not line_data:

            raise ValidationError(
                _(
                    "Please add at least "
                    "one expense line."
                )
            )

        return {
            "lines": line_data,
            "total": total_amount,

            "first_category": (
                first_category
            ),

            "first_date": (
                first_date
            ),
        }

    # =========================================================
    # SYNC PARENT EXPENSE
    # =========================================================

    def _sync_expense(
        self,
        expense,
    ):

        lines = (
            expense
            .monthly_expense_line_ids
        )

        if not lines:
            return 0.0

        total = sum(
            lines.mapped(
                "amount"
            )
        )

        first_line = lines[0]

        vals = {
            "total_amount_currency": (
                total
            ),

            "total_amount": (
                total
            ),

            "quantity": 1.0,

            "price_unit": (
                total
            ),
        }

        if first_line.category_id:

            vals["product_id"] = (
                first_line.category_id.id
            )

        if first_line.expense_date:

            vals["date"] = (
                first_line.expense_date
            )

        expense.sudo().write(
            vals
        )

        return total

    # =========================================================
    # DASHBOARD
    # =========================================================

    @http.route(
        ["/my/expenses"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_expense_dashboard(
        self,
        **kwargs
    ):

        employee = (
            self._get_employee()
        )

        domain = (
            self._expense_domain(
                employee
            )
        )

        Expense = (
            request.env["hr.expense"]
            .sudo()
        )

        expenses = Expense.search(
            domain,
            order="date desc, id desc",
            limit=5,
        )

        values = {

            "page_name": (
                "expense_dashboard"
            ),

            "employee": (
                employee
            ),

            "expenses": (
                expenses
            ),

            "total_count": (
                Expense.search_count(
                    domain
                )
            ),

            "draft_count": (
                Expense.search_count(
                    domain + [
                        (
                            "state",
                            "=",
                            "draft",
                        ),
                    ]
                )
            ),

            "pending_count": (
                Expense.search_count(
                    domain + [
                        (
                            "state",
                            "=",
                            "submitted",
                        ),
                    ]
                )
            ),

            "approved_count": (
                Expense.search_count(
                    domain + [
                        (
                            "state",
                            "in",
                            [
                                "approved",
                                "posted",
                                "in_payment",
                            ],
                        ),
                    ]
                )
            ),

            "paid_count": (
                Expense.search_count(
                    domain + [
                        (
                            "state",
                            "=",
                            "paid",
                        ),
                    ]
                )
            ),

            "rejected_count": (
                Expense.search_count(
                    domain + [
                        (
                            "state",
                            "=",
                            "refused",
                        ),
                    ]
                )
            ),

            "error": (
                kwargs.get(
                    "error"
                )
            ),

            "success": (
                kwargs.get(
                    "success"
                )
            ),
        }

        return request.render(
            "zencore_employee_expense."
            "portal_employee_expense_dashboard",
            values,
        )

    # =========================================================
    # EXPENSE LIST
    # =========================================================

    @http.route(
        [
            "/my/expenses/list",

            "/my/expenses/list/"
            "page/<int:page>",
        ],
        type="http",
        auth="user",
        website=True,
    )
    def portal_expense_list(
        self,
        page=1,
        **kwargs
    ):

        employee = (
            self._get_employee()
        )

        domain = (
            self._expense_domain(
                employee
            )
        )

        Expense = (
            request.env["hr.expense"]
            .sudo()
        )

        total = (
            Expense.search_count(
                domain
            )
        )

        pager = portal_pager(
            url="/my/expenses/list",
            total=total,
            page=page,
            step=self._items_per_page,
        )

        expenses = Expense.search(
            domain,
            order="date desc, id desc",
            limit=self._items_per_page,
            offset=pager["offset"],
        )

        values = {
            "page_name": (
                "expense_list"
            ),

            "employee": (
                employee
            ),

            "expenses": (
                expenses
            ),

            "pager": (
                pager
            ),

            "error": (
                kwargs.get(
                    "error"
                )
            ),

            "success": (
                kwargs.get(
                    "success"
                )
            ),
        }

        return request.render(
            "zencore_employee_expense."
            "portal_employee_expense_list",
            values,
        )

    # =========================================================
    # CREATE FORM
    # =========================================================

    @http.route(
        ["/my/expenses/create"],
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_expense_create_form(
        self,
        **kwargs
    ):

        employee = (
            self._get_employee()
        )

        if not employee:

            return request.render(
                "zencore_employee_expense."
                "portal_employee_not_found",
                {},
            )

        values = {
            "page_name": (
                "expense_create"
            ),

            "employee": (
                employee
            ),

            "expense": (
                False
            ),

            "categories": (
                self._get_categories(
                    employee
                )
            ),

            "today": (
                fields.Date.context_today(
                    request.env[
                        "hr.expense"
                    ]
                )
            ),

            "error": (
                kwargs.get(
                    "error"
                )
            ),
        }

        return request.render(
            "zencore_employee_expense."
            "portal_employee_expense_form",
            values,
        )

    # =========================================================
    # CREATE EXPENSE
    # =========================================================

    @http.route(
        ["/my/expenses/save"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_expense_create(
        self,
        **post
    ):

        employee = (
            self._get_employee()
        )

        if not employee:

            return request.redirect(
                "/my/expenses"
            )

        try:

            title = (
                request.httprequest.form
                .get(
                    "name",
                    "",
                )
                .strip()
            )

            if not title:

                raise ValidationError(
                    _(
                        "Expense Title "
                        "is required."
                    )
                )

            parsed = (
                self._parse_expense_lines(
                    employee
                )
            )

            line_commands = [

                Command.create(
                    line_data["vals"]
                )

                for line_data
                in parsed["lines"]
            ]

            expense = (
                request.env["hr.expense"]
                .sudo()
                .create({

                    "name": (
                        title
                    ),

                    "employee_id": (
                        employee.id
                    ),

                    "company_id": (
                        employee.company_id.id
                    ),

                    "currency_id": (
                        employee.company_id
                        .currency_id.id
                    ),

                    "date": (
                        parsed["first_date"]
                    ),

                    "product_id": (
                        parsed[
                            "first_category"
                        ].id
                    ),

                    "payment_mode": (
                        "own_account"
                    ),

                    "monthly_expense_line_ids": (
                        line_commands
                    ),
                })
            )

            self._sync_expense(
                expense
            )

            return (
                self._redirect_message(

                    "/my/expenses/%s"
                    % expense.id,

                    "success",

                    _(
                        "Expense created "
                        "successfully."
                    ),
                )
            )

        except (
            ValidationError,
            UserError,
        ) as error:

            return (
                self._redirect_message(

                    "/my/expenses/create",

                    "error",

                    error,
                )
            )

    # =========================================================
    # EXPENSE DETAIL
    # =========================================================

    @http.route(
        [
            "/my/expenses/"
            "<int:expense_id>"
        ],
        type="http",
        auth="user",
        website=True,
    )
    def portal_expense_detail(
        self,
        expense_id,
        **kwargs
    ):

        expense = (
            self._get_own_expense(
                expense_id
            )
        )

        if not expense:

            return request.redirect(
                "/my/expenses"
            )

        values = {

            "page_name": (
                "expense_detail"
            ),

            "expense": (
                expense
            ),

            "employee": (
                self._get_employee()
            ),

            "success": (
                kwargs.get(
                    "success"
                )
            ),

            "error": (
                kwargs.get(
                    "error"
                )
            ),
        }

        return request.render(
            "zencore_employee_expense."
            "portal_employee_expense_detail",
            values,
        )

    # =========================================================
    # EDIT FORM
    # =========================================================

    @http.route(
        [
            "/my/expenses/"
            "<int:expense_id>/edit"
        ],
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_expense_edit(
        self,
        expense_id,
        **kwargs
    ):

        expense = (
            self._get_own_expense(
                expense_id
            )
        )

        if not expense:

            return request.redirect(
                "/my/expenses"
            )

        if expense.state != "draft":

            return (
                self._redirect_message(

                    "/my/expenses/%s"
                    % expense.id,

                    "error",

                    _(
                        "Only draft expenses "
                        "can be edited."
                    ),
                )
            )

        employee = (
            self._get_employee()
        )

        values = {

            "page_name": (
                "expense_edit"
            ),

            "employee": (
                employee
            ),

            "expense": (
                expense
            ),

            "categories": (
                self._get_categories(
                    employee
                )
            ),

            "today": (
                fields.Date.context_today(
                    request.env[
                        "hr.expense"
                    ]
                )
            ),

            "error": (
                kwargs.get(
                    "error"
                )
            ),
        }

        return request.render(
            "zencore_employee_expense."
            "portal_employee_expense_form",
            values,
        )

    # =========================================================
    # UPDATE EXPENSE
    # =========================================================

    @http.route(
        [
            "/my/expenses/"
            "<int:expense_id>/update"
        ],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_expense_update(
        self,
        expense_id,
        **post
    ):

        expense = (
            self._get_own_expense(
                expense_id
            )
        )

        if not expense:

            return request.redirect(
                "/my/expenses"
            )

        if expense.state != "draft":

            return (
                self._redirect_message(

                    "/my/expenses/%s"
                    % expense.id,

                    "error",

                    _(
                        "Only draft expenses "
                        "can be edited."
                    ),
                )
            )

        employee = (
            self._get_employee()
        )

        try:

            title = (
                request.httprequest.form
                .get(
                    "name",
                    "",
                )
                .strip()
            )

            if not title:

                raise ValidationError(
                    _(
                        "Expense Title "
                        "is required."
                    )
                )

            parsed = (
                self._parse_expense_lines(
                    employee
                )
            )

            existing_lines = (
                expense
                .monthly_expense_line_ids
            )

            existing_line_ids = set(
                existing_lines.ids
            )

            submitted_line_ids = set()

            commands = []

            # =================================================
            # CREATE / UPDATE
            # =================================================

            for line_data in (
                parsed["lines"]
            ):

                line_id = (
                    line_data[
                        "line_id"
                    ]
                )

                vals = (
                    line_data[
                        "vals"
                    ]
                )

                # Existing Line
                if line_id:

                    if (
                        line_id
                        not in existing_line_ids
                    ):

                        raise ValidationError(
                            _(
                                "Invalid "
                                "expense line."
                            )
                        )

                    commands.append(
                        Command.update(
                            line_id,
                            vals,
                        )
                    )

                    submitted_line_ids.add(
                        line_id
                    )

                # New Line
                else:

                    commands.append(
                        Command.create(
                            vals
                        )
                    )

            # =================================================
            # DELETE REMOVED PORTAL ROWS
            # =================================================

            for line in existing_lines:

                if (
                    line.id
                    not in submitted_line_ids
                ):

                    commands.append(
                        Command.delete(
                            line.id
                        )
                    )

            expense.sudo().write({

                "name": (
                    title
                ),

                "date": (
                    parsed["first_date"]
                ),

                "product_id": (
                    parsed[
                        "first_category"
                    ].id
                ),

                "monthly_expense_line_ids": (
                    commands
                ),
            })

            self._sync_expense(
                expense
            )

            return (
                self._redirect_message(

                    "/my/expenses/%s"
                    % expense.id,

                    "success",

                    _(
                        "Expense updated "
                        "successfully."
                    ),
                )
            )

        except (
            ValidationError,
            UserError,
        ) as error:

            return (
                self._redirect_message(

                    "/my/expenses/%s/edit"
                    % expense.id,

                    "error",

                    error,
                )
            )

    # =========================================================
    # DELETE EXPENSE
    # =========================================================

    @http.route(
        [
            "/my/expenses/"
            "<int:expense_id>/delete"
        ],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_expense_delete(
        self,
        expense_id,
        **post
    ):

        expense = (
            self._get_own_expense(
                expense_id
            )
        )

        if not expense:

            return request.redirect(
                "/my/expenses"
            )

        if expense.state != "draft":

            return (
                self._redirect_message(

                    "/my/expenses/%s"
                    % expense.id,

                    "error",

                    _(
                        "Only draft expenses "
                        "can be deleted."
                    ),
                )
            )

        expense.sudo().unlink()

        return (
            self._redirect_message(

                "/my/expenses/list",

                "success",

                _(
                    "Expense deleted "
                    "successfully."
                ),
            )
        )

    # =========================================================
    # SUBMIT EXPENSE
    # =========================================================

    @http.route(
        [
            "/my/expenses/"
            "<int:expense_id>/submit"
        ],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_expense_submit(
        self,
        expense_id,
        **post
    ):

        expense = (
            self._get_own_expense(
                expense_id
            )
        )

        if not expense:

            return request.redirect(
                "/my/expenses"
            )

        if expense.state != "draft":

            return (
                self._redirect_message(

                    "/my/expenses/%s"
                    % expense.id,

                    "error",

                    _(
                        "Only draft expenses "
                        "can be submitted."
                    ),
                )
            )

        try:

            total = (
                self._sync_expense(
                    expense
                )
            )

            if (
                expense
                .currency_id
                .is_zero(
                    total
                )
            ):

                raise ValidationError(
                    _(
                        "Expense total must "
                        "be greater than 0."
                    )
                )

            if not (
                expense
                .monthly_expense_line_ids
            ):

                raise ValidationError(
                    _(
                        "Please add at least "
                        "one expense line."
                    )
                )

            expense.sudo().action_submit()

            return (
                self._redirect_message(

                    "/my/expenses/%s"
                    % expense.id,

                    "success",

                    _(
                        "Expense submitted "
                        "successfully."
                    ),
                )
            )

        except (
            ValidationError,
            UserError,
        ) as error:

            return (
                self._redirect_message(

                    "/my/expenses/%s"
                    % expense.id,

                    "error",

                    error,
                )
            )

    # =========================================================
    # DOWNLOAD LINE DOCUMENT
    # =========================================================

    @http.route(
        [
            "/my/expenses/"
            "<int:expense_id>/"
            "line/<int:line_id>/document"
        ],
        type="http",
        auth="user",
        website=True,
        methods=["GET"],
    )
    def portal_expense_line_document(
        self,
        expense_id,
        line_id,
        **kwargs
    ):

        # Verify parent expense belongs
        # to logged-in employee
        expense = (
            self._get_own_expense(
                expense_id
            )
        )

        if not expense:
            return request.not_found()

        # Find only line belonging
        # to this expense
        line = (
            request.env[
                "hr.expense.line"
            ]
            .sudo()
            .search(
                [
                    (
                        "id",
                        "=",
                        line_id,
                    ),
                    (
                        "expense_id",
                        "=",
                        expense.id,
                    ),
                ],
                limit=1,
            )
        )

        if (
            not line
            or not line.document
        ):

            return request.not_found()

        try:

            content = (
                base64.b64decode(
                    line.document
                )
            )

        except Exception:

            return request.not_found()

        filename = (
            line.document_filename
            or "expense_document"
        )

        mimetype = (
            mimetypes.guess_type(
                filename
            )[0]
            or "application/octet-stream"
        )

        return request.make_response(
            content,
            headers=[
                (
                    "Content-Type",
                    mimetype,
                ),
                (
                    "Content-Disposition",
                    content_disposition(
                        filename
                    ),
                ),
            ],
        )
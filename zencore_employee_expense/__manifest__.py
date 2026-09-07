{
    'name': 'Employee Expense Portal',
    'version': '19.0.1.0.0',
    'summary': 'Monthly Employee Expense Management',
    'description': """
        Monthly Employee Expense Management for Giant Agro.
        Employees can maintain their monthly expenses in a single
        expense form, submit expenses for approval, and generate
        accounting entries after approval.
    """,
    'author': 'Afzal Khan',
    'website': '',
    'category': 'Giant Agro Processing Ltd',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'hr_expense',
        'portal',
        'website',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_expenses_line_views.xml',
        'views/hr_expenses.xml',
        'views/expenses_category_views.xml',
        'views/expense_portal_templates.xml',
        'views/res_config_settings_views.xml',
    ],

    'assets': {
        'web.assets_frontend': [
            'zencore_employee_expense/static/src/scss/expense_portal.scss',
            'zencore_employee_expense/static/src/js/expense_portal.js',
        ],
    },
    'installable': True,
    'application': True,
}
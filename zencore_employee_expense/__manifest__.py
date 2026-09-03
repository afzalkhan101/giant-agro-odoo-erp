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
    'author': 'Afzal khan',
    'website': '',
    'category': 'Giant Agro Processing Ltd',
    'license': 'LGPL-3',

    'depends': [
        'account',
        'hr_expense',
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/hr_expenses_line_views.xml',
        'views/hr_expenses.xml',

    ],

    'demo': [],

    'installable': True,
    'application': True,
}
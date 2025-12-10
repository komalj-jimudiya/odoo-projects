# -*- coding: utf-8 -*-
{
    'name': "project_git_integration",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Project',
    'version': '19.0.0.0',

    # any module necessary for this one to work correctly
    'depends': ['project'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/project_views.xml',
        'views/project_task_views.xml',
        'views/res_config_setting.xml'
    ],
}


# -*- coding: utf-8 -*-

from odoo import models, fields

class GitPullRequest(models.Model):
    _name = 'git.pull.request'
    _description = 'Git Pull Request'
    _order = 'pr_created_on desc'

    pr_number = fields.Integer(string="PR Number", required=True)
    pr_title = fields.Char(string="PR Title")
    pr_url = fields.Char(string="PR URL")
    pr_status = fields.Selection(
        [
            ('open', 'Open'),
            ('closed', 'Closed'),
            ('merged', 'Merged')
        ],
        string="Status"
    )
    pr_source_branch = fields.Char(string="Source Branch")
    pr_target_branch = fields.Char(string="Target Branch")
    pr_created_on = fields.Datetime(string="Created On")
    pr_merged_on = fields.Datetime(string="Merged On")
    pr_created_by = fields.Many2one('res.users', string="Created By")
    task_id = fields.Many2one('project.task', string="Task", ondelete='cascade')

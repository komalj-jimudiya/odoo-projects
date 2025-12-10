# -*- coding: utf-8 -*-

from odoo import models, fields

class GitCommitLog(models.Model):
    _name = 'git.commit.log'
    _description = 'Git Commit Log'
    _order = 'commit_date desc'

    commit_hash = fields.Char(string="Commit ID", required=True)
    commit_message = fields.Text(string="Commit Message")
    commit_author = fields.Char(string="Author")
    commit_date = fields.Datetime(string="Date")
    commit_url = fields.Char(string="Commit URL")
    branch_name = fields.Char(string="Branch")
    name = fields.Char(string="Name")
    task_id = fields.Many2one('project.task', string="Task", ondelete='cascade')

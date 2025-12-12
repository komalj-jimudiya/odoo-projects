# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import requests

class GitMergeWizard(models.TransientModel):
    _name = 'git.merge.wizard'
    _description = 'Git Merge Request Wizard'

    task_id = fields.Many2one('project.task', string="Task", required=True)
    source_branch = fields.Char(string="Source Branch", required=True)
    target_branch = fields.Char(string="Target Branch", required=True)
    title = fields.Char(string="Title", required=True)
    description = fields.Text(string="Description")

    @api.model
    def default_get(self, fields_list):
        res = super(GitMergeWizard, self).default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            task = self.env['project.task'].browse(active_id)
            res['task_id'] = task.id
            res['source_branch'] = task.git_dev_branch
            res['target_branch'] = task.project_id.git_default_branch or 'main'
            res['title'] = f"Merge {task.git_dev_branch or '...'} into {task.project_id.git_default_branch or 'main'}"
            res['description'] = f"Pull Request regarding task: {task.name}"
        return res

    def action_create_merge_request(self):
        self.ensure_one()
        
        task = self.task_id
        if not task.project_id.git_repository_name:
             raise UserError("The project must be linked to a GitHub repository.")

        # Get Token
        github_token = self.env['ir.config_parameter'].sudo().get_param('project_git_integration.github_token')
        if not github_token:
            raise UserError("No GitHub Token found. Please configure it in General Settings.")

        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        owner = task.project_id.git_repository_owner
        repo = task.project_id.git_repository_name
        
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        
        data = {
            'title': self.title,
            'body': self.description or '',
            'head': self.source_branch,
            'base': self.target_branch
        }

        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
        except requests.exceptions.RequestException as e:
             raise UserError(f"Network error creating Pull Request: {str(e)}")

        if response.status_code == 201:
            pr_data = response.json()
            # Optionally fetch PRs on the task immediately
            task.action_fetch_pull_requests()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': f'Pull Request #{pr_data.get("number")} created successfully!',
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        else:
            error_msg = response.text
            try:
                error_json = response.json()
                if 'message' in error_json:
                    error_msg = error_json['message']
                    if 'errors' in error_json: # GitHub validation errors
                         error_msg += f" Details: {error_json['errors']}"
            except ValueError:
                pass
            raise UserError(f"GitHub API Error ({response.status_code}): {error_msg}")

# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import requests

class ProjectTask(models.Model):
    _inherit = 'project.task'

    git_dev_branch = fields.Char(string="Dev Branch Name")
    git_dev_branch_url = fields.Char(string="Dev Branch URL")
    
    git_commit_branch = fields.Char(string="Commit Branch Name")
    git_commit_branch_url = fields.Char(string="Commit Branch URL")
    
    git_branch_status = fields.Selection(
        [
            ('active', "Active"),
            ('merged', "Merged"),
            ('deleted', "Deleted")
        ],
        string="Branch Status",
        default="active"
    )

    git_branch_created_by = fields.Many2one('res.users', string="Branch Created By")
    git_branch_created_on = fields.Datetime(string="Branch Created On")
    git_branch_last_synced = fields.Datetime(string="Last Synced On")
    
    commit_ids = fields.One2many('git.commit.log', 'task_id', string="Commits")

    def action_fetch_commits(self):
        """
        Fetches commits from the linked GitHub branch for this task.
        """
        self.ensure_one()
        
        # Check if project is linked
        if not self.project_id.git_repository_name:
             raise UserError("The project must be linked to a GitHub repository first.")

        # Get Token
        github_token = self.env['ir.config_parameter'].sudo().get_param('project_git_integration.github_token')
        if not github_token:
            raise UserError("No GitHub Token found. Please configure it in General Settings.")

        # Determine Branch
        # Use dev branch if set, otherwise default branch
        branch_name = self.git_dev_branch or self.project_id.git_default_branch
        if not branch_name:
             raise UserError("No branch specified to fetch commits from.")

        # GitHub API Headers
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        owner = self.project_id.git_repository_owner
        repo = self.project_id.git_repository_name
        
        # API URL to list commits
        url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        params = {
            'sha': branch_name,
            'per_page': 100 # Limit to last 100 for now
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
        except requests.exceptions.RequestException as e:
             raise UserError(f"Network error fetching commits: {str(e)}")

        if response.status_code == 200:
            commits_data = response.json()
            
            # Create commit records
            # We want to avoid duplicates. We can check by hash for this task.
            existing_hashes = self.commit_ids.mapped('commit_hash')
            
            new_commits = []
            for commit in commits_data:
                sha = commit.get('sha')
                if sha in existing_hashes:
                    continue
                
                commit_info = commit.get('commit', {})
                author_info = commit_info.get('author', {})
                
                vals = {
                    'commit_hash': sha,
                    'commit_message': commit_info.get('message'),
                    'commit_author': author_info.get('name'),
                    'commit_date': author_info.get('date'), # ISO 8601 format, Odoo handles it
                    'commit_url': commit.get('html_url'),
                    'branch_name': branch_name,
                    'task_id': self.id
                }
                new_commits.append(vals)
            
            if new_commits:
                self.env['git.commit.log'].create(new_commits)
            
            self.git_branch_last_synced = fields.Datetime.now()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': f'{len(new_commits)} new commits fetched successfully!',
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                }
            }
        elif response.status_code == 404:
             raise UserError(f"Branch '{branch_name}' not found on GitHub.")
        else:
            error_msg = response.text
            try:
                error_json = response.json()
                if 'message' in error_json:
                    error_msg = error_json['message']
            except ValueError:
                pass
            raise UserError(f"GitHub API Error ({response.status_code}): {error_msg}")


    def action_create_custom_branch(self):
        """
        Creates a new branch in the linked GitHub repository for this task.
        """
        self.ensure_one()
        
        # Check if project is linked
        if not self.project_id.git_repository_name:
            raise UserError("The project must be linked to a GitHub repository first.")

        # Get Token
        github_token = self.env['ir.config_parameter'].sudo().get_param('project_git_integration.github_token')
        if not github_token:
            raise UserError("No GitHub Token found. Please configure it in General Settings.")

        # Sanitize Task Name for Branch
        # Format: task-{id}-{name}
        task_name_clean = "".join(c if c.isalnum() or c in ('-', '_') else '-' for c in self.name)
        while '--' in task_name_clean:
            task_name_clean = task_name_clean.replace('--', '-')
        task_name_clean = task_name_clean.strip('-').lower()
        
        branch_name = task_name_clean
        # Truncate if too long (optional, but safe)
        if len(branch_name) > 100:
            branch_name = branch_name[:100]

        # GitHub API Headers
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        owner = self.project_id.git_repository_owner
        repo = self.project_id.git_repository_name
        default_branch = self.project_id.git_default_branch or 'main'

        # 1. Get SHA of default branch
        ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{default_branch}"
        
        try:
            ref_response = requests.get(ref_url, headers=headers, timeout=10)
            if ref_response.status_code == 404:
                 raise UserError(f"Default branch '{default_branch}' not found in repository.")
            ref_response.raise_for_status()
            sha = ref_response.json().get('object', {}).get('sha')
        except requests.exceptions.RequestException as e:
            raise UserError(f"Failed to fetch default branch info: {str(e)}")

        # 2. Create New Branch (Reference)
        create_ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
        data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": sha
        }

        try:
            create_response = requests.post(create_ref_url, json=data, headers=headers, timeout=10)
        except requests.exceptions.RequestException as e:
             raise UserError(f"Failed to create branch: {str(e)}")

        if create_response.status_code == 201:
            repo_html_url = self.project_id.git_repository_url
            # Construct branch URL (standard GitHub format)
            branch_url = f"{repo_html_url}/tree/{branch_name}"

            self.write({
                'git_dev_branch': branch_name,
                'git_dev_branch_url': branch_url,
                'git_commit_branch': branch_name, # Assuming same for now as requested
                'git_commit_branch_url': branch_url,
                'git_branch_status': 'active',
                'git_branch_created_by': self.env.user.id,
                'git_branch_created_on': fields.Datetime.now(),
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': f'Branch "{branch_name}" created successfully!',
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                }
            }
        elif create_response.status_code == 422:
             raise UserError(f"Branch '{branch_name}' already exists.")
        else:
            error_msg = create_response.text
            try:
                error_json = create_response.json()
                if 'message' in error_json:
                    error_msg = error_json['message']
            except ValueError:
                pass
            raise UserError(f"GitHub API Error ({create_response.status_code}): {error_msg}")

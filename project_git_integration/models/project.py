# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import requests


class ProjectProject(models.Model):
	_inherit = 'project.project'

	git_repository_name = fields.Char(string="Repository Name")
	git_repository_url = fields.Char(string="Repository URL")
	git_repository_id = fields.Char(string="Repository ID")
	git_repository_owner = fields.Char(string="Repository Owner")
	git_default_branch = fields.Char(string="Default Branch", default="main")

	git_connection_status = fields.Selection(
		[
			('connected', "Connected"),
			('not_connected', "Not Connected")
		],
		string="Connection Status",
		default="not_connected"
	)

	git_connected_on = fields.Datetime(string="Linked On")


	def action_create_repository(self):
		"""
		Creates a GitHub repository for this project using a token from company settings.
		"""
		self.ensure_one()
		
		# 1. Get Token
		github_token = self.env['ir.config_parameter'].sudo().get_param('project_git_integration.github_token')
		if not github_token:
			raise UserError("No GitHub Token found. Please configure it in General Settings.")

		# 2. Sanitize Name (Simple version: Replace spaces with hyphens, remove special chars if needed)
		if not self.name:
			raise UserError("Project name is required to create a repository.")
			
		# Very basic sanitization: alphanumeric and hyphens/underscores only
		repo_name = "".join(c if c.isalnum() or c in ('-', '_') else '-' for c in self.name)
		# Remove duplicate hyphens
		while '--' in repo_name:
			repo_name = repo_name.replace('--', '-')
		repo_name = repo_name.strip('-')

		url = "https://api.github.com/user/repos"
		headers = {
			"Authorization": f"Bearer {github_token}",
			"Accept": "application/vnd.github+json",
			"X-GitHub-Api-Version": "2022-11-28"
		}
		data = {
			"name": repo_name,
			"private": False, # Or make this configurable
			"description": f"Repository for Odoo Project: {self.name}",
			"auto_init": True
		}

		try:
			response = requests.post(url, json=data, headers=headers, timeout=10)
		except requests.exceptions.RequestException as e:
			raise UserError(f"Network error connecting to GitHub: {str(e)}")

		if response.status_code == 201:
			repo_data = response.json()
			self.write({
				'git_repository_name': repo_data.get('name'),
				'git_repository_url': repo_data.get('html_url'),
				'git_repository_id': str(repo_data.get('id')),
				'git_repository_owner': repo_data.get('owner', {}).get('login'),
				'git_default_branch': repo_data.get('default_branch', 'main'),
				'git_connection_status': 'connected',
				'git_connected_on': fields.Datetime.now(),
			})
			return {
				'type': 'ir.actions.client',
				'tag': 'display_notification',
				'params': {
					'title': 'Success',
					'message': 'GitHub repository created successfully!',
					'type': 'success',
					'sticky': False,
					'next': {'type': 'ir.actions.client', 'tag': 'reload'},
				}
			}
		else:
			error_msg = response.text
			try:
				error_json = response.json()
				if 'message' in error_json:
					error_msg = error_json['message']
			except ValueError:
				pass
			raise UserError(f"GitHub API Error ({response.status_code}): {error_msg}")

	def action_git_assign_repo(self):
		"""
		Searches for an existing GitHub repository with the same name as the project
		and links it if found.
		"""
		print("action_git_assign_repo---------------------")
		self.ensure_one()

		# 1. Get Token
		github_token = self.env['ir.config_parameter'].sudo().get_param('project_git_integration.github_token')
		if not github_token:
			raise UserError("No GitHub Token found. Please configure it in General Settings.")

		# 2. Sanitize Name
		if not self.name:
			raise UserError("Project name is required to search for a repository.")
		repo_name = "".join(c if c.isalnum() or c in ('-', '_') else '-' for c in self.name)
		while '--' in repo_name:
			repo_name = repo_name.replace('--', '-')
		repo_name = repo_name.strip('-')

		# 3. Get Current User (Owner)
		user_url = "https://api.github.com/user"
		headers = {
			"Authorization": f"Bearer {github_token}",
			"Accept": "application/vnd.github+json",
			"X-GitHub-Api-Version": "2022-11-28"
		}
		
		try:
			user_response = requests.get(user_url, headers=headers, timeout=10)
			user_response.raise_for_status()
			username = user_response.json().get('login')
		except requests.exceptions.RequestException as e:
			raise UserError(f"Failed to fetch GitHub user info: {str(e)}")

		# 4. Check if Repo Exists
		repo_url = f"https://api.github.com/repos/{username}/{repo_name}"
		try:
			response = requests.get(repo_url, headers=headers, timeout=10)
		except requests.exceptions.RequestException as e:
			raise UserError(f"Network error searching for repository: {str(e)}")

		if response.status_code == 200:
			repo_data = response.json()
			self.write({
				'git_repository_name': repo_data.get('name'),
				'git_repository_url': repo_data.get('html_url'),
				'git_repository_id': str(repo_data.get('id')),
				'git_repository_owner': repo_data.get('owner', {}).get('login'),
				'git_default_branch': repo_data.get('default_branch', 'main'),
				'git_connection_status': 'connected',
				'git_connected_on': fields.Datetime.now(),
			})
			return {
				'type': 'ir.actions.client',
				'tag': 'display_notification',
				'params': {
					'title': 'Success',
					'message': f'Existing repository "{repo_name}" linked successfully!',
					'type': 'success',
					'sticky': False,
					'next': {'type': 'ir.actions.client', 'tag': 'reload'},
				}
			}
		elif response.status_code == 404:
			raise UserError(f"No existing repository found with name '{repo_name}' for user '{username}'.")
		else:
			error_msg = response.text
			try:
				error_json = response.json()
				if 'message' in error_json:
					error_msg = error_json['message']
			except ValueError:
				pass
			raise UserError(f"GitHub API Error ({response.status_code}): {error_msg}")

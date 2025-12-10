# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from unittest.mock import patch, MagicMock
import logging

_logger = logging.getLogger(__name__)

class TestProjectGit(TransactionCase):

	def setUp(self):
		super(TestProjectGit, self).setUp()
		self.project = self.env['project.project'].create({
			'name': 'Test Project',
		})
		self.env['ir.config_parameter'].sudo().set_param('project_git_integration.github_token', 'test_token')

	def test_create_repository_success(self):
		""" Test successful repository creation """
		with patch('requests.post') as mock_post:
			mock_response = MagicMock()
			mock_response.status_code = 201
			mock_response.json.return_value = {
				'name': 'Test-Project',
				'html_url': 'https://github.com/user/Test-Project',
				'id': 123456,
				'owner': {'login': 'testuser'},
				'default_branch': 'main',
			}
			mock_post.return_value = mock_response

			self.project.action_create_repository()

			self.assertEqual(self.project.git_repository_name, 'Test-Project')
			self.assertEqual(self.project.git_repository_url, 'https://github.com/user/Test-Project')
			self.assertEqual(self.project.git_repository_id, '123456')
			self.assertEqual(self.project.git_connection_status, 'connected')

	def test_create_repository_no_token(self):
		""" Test failure when no token is configured """
		self.env['ir.config_parameter'].sudo().set_param('project_git_integration.github_token', False)
		with self.assertRaises(UserError):
			self.project.action_create_repository()

	def test_assign_repo_success(self):
		""" Test successful linking of existing repository """
		with patch('requests.get') as mock_get:
			# Mock User Info Response
			mock_user_response = MagicMock()
			mock_user_response.status_code = 200
			mock_user_response.json.return_value = {'login': 'testuser'}
			
			# Mock Repo Existence Response
			mock_repo_response = MagicMock()
			mock_repo_response.status_code = 200
			mock_repo_response.json.return_value = {
				'name': 'Test-Project',
				'html_url': 'https://github.com/testuser/Test-Project',
				'id': 987654,
				'owner': {'login': 'testuser'},
				'default_branch': 'master',
			}

			mock_get.side_effect = [mock_user_response, mock_repo_response]

			self.project.action_git_assign_repo()

			self.assertEqual(self.project.git_repository_name, 'Test-Project')
			self.assertEqual(self.project.git_repository_id, '987654')
			self.assertEqual(self.project.git_connection_status, 'connected')

	def test_assign_repo_not_found(self):
		""" Test failure when repo does not exist """
		with patch('requests.get') as mock_get:
			# Mock User Info Response
			mock_user_response = MagicMock()
			mock_user_response.status_code = 200
			mock_user_response.json.return_value = {'login': 'testuser'}

			# Mock Repo Not Found
			mock_repo_response = MagicMock()
			mock_repo_response.status_code = 404

			mock_get.side_effect = [mock_user_response, mock_repo_response]

			with self.assertRaises(UserError):
				self.project.action_git_assign_repo()

	def test_create_repository_api_error(self):
		""" Test handling of API errors """
		with patch('requests.post') as mock_post:
			mock_response = MagicMock()
			mock_response.status_code = 401
			mock_response.text = 'Bad credentials'
			mock_response.json.side_effect = ValueError # Simulate non-JSON response sometimes
			mock_post.return_value = mock_response

			with self.assertRaises(UserError):
				self.project.action_create_repository()

class TestProjectTaskGit(TransactionCase):

	def setUp(self):
		super(TestProjectTaskGit, self).setUp()
		self.project = self.env['project.project'].create({
			'name': 'Test Project',
			'git_repository_name': 'Test-Project',
			'git_repository_owner': 'testuser',
			'git_default_branch': 'main',
			'git_repository_url': 'https://github.com/testuser/Test-Project'
		})
		self.task = self.env['project.task'].create({
			'name': 'Test Task 1',
			'project_id': self.project.id,
		})
		self.env['ir.config_parameter'].sudo().set_param('project_git_integration.github_token', 'test_token')

	def test_create_branch_success(self):
		""" Test successful branch creation """
		with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
			# Mock Default Branch SHA
			mock_ref_response = MagicMock()
			mock_ref_response.status_code = 200
			mock_ref_response.json.return_value = {'object': {'sha': 'abcdef123456'}}
			
			mock_get.return_value = mock_ref_response

			# Mock Create Branch
			mock_create_response = MagicMock()
			mock_create_response.status_code = 201
			
			mock_post.return_value = mock_create_response

			self.task.action_create_custom_branch()

			expected_branch = f"task-{self.task.id}-test-task-1"
			self.assertEqual(self.task.git_dev_branch, expected_branch)
			self.assertEqual(self.task.git_branch_status, 'active')
			self.assertTrue(self.task.git_dev_branch_url.endswith(expected_branch))

	def test_create_branch_no_token(self):
		""" Test error when token is missing """
		self.env['ir.config_parameter'].sudo().set_param('project_git_integration.github_token', False)
		with self.assertRaises(UserError):
			self.task.action_create_custom_branch()

	def test_create_branch_no_repo_link(self):
		""" Test error when project not linked """
		self.project.git_repository_name = False
		with self.assertRaises(UserError):
			self.task.action_create_custom_branch()

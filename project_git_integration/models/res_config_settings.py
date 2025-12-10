from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    github_token = fields.Char(string="GitHub Token")

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('project_git_integration.github_token', self.github_token)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res['github_token'] = self.env['ir.config_parameter'].sudo().get_param('project_git_integration.github_token')
        return res




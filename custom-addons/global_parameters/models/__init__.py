from odoo import models,fields

class Parameters(models.Model):
    _name='global.parameters'
    _description='Modelo para gestionar parámetros globales en la base de datos'

    parameterId=fields.Char(string='Parameter ID')
    name=fields.Char(string='Name',required=True)
    groupId=fields.Char(string='Group')
    value=fields.Char(string='Value',required=True)
    description=fields.Text(string='Description')

# Otros campos que desees para tus parámetros globales
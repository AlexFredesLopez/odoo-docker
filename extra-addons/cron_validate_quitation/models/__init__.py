
import logging
import base64
import requests
from odoo import models, api, fields

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    iterated = fields.Boolean(string='Iterated', store=True , default=False)

    def check_partner_sap_registration(self):
        orders_to_check = self.search([('iterated', '=', False)])

        # iniciamos la búsqueda

        self.__checkPartnerSapRegistration('C154134174')

        # for order in orders_to_check:
        #     if order.partner_id:

        #         _logger.info('------------------> Verificando registro SAP para el partner IDsssssss: %s', order.partner_id.name)
        #         _logger.info('------------------> Verificando registro SAP para el partner ID: %s', order.partner_id.id)




    def __openConnection(self):

        sap_endpoint_url = 'https://cl-cloud-su4.sapparapymes.cloud:50000/b1s/v1/Login'

        # Datos que deseas enviar en el cuerpo de la solicitud POST, puede ser un diccionario de Python
        post_data = {
            "CompanyDB": "SBODEMOCL3",
            "Password": "fBAGohonYpBBc11i",
            "UserName": "demosap1"
        }

        # Realiza la solicitud POST con las credenciales y los datos
        headers = {
            'Content-Type': 'application/json'  # Ajusta el tipo de contenido según lo que espera el servicio SAP
        }

        _logger.info('------------------> Datos a enviar: %s', post_data)

        response = requests.post(sap_endpoint_url, json=post_data, headers=headers)

        _logger.info('------------------> Status Code, %s', response.status_code)

        if response.status_code == 200:
            # Procesa la respuesta del servicio SAP según tu lógica
            # Por ejemplo, si la respuesta es JSON, puedes usar response.json() para analizarla.
            # Luego, actualiza el campo "Iterated" en función de la respuesta.

            # order.iterated = True  # Actualiza según la lógica
            _logger.info('------------------> Llegamos OK al endpoint, %s', response.json())

            return response.json()
        else:
            # Maneja el caso en el que la solicitud no sea exitosa, por ejemplo, registrando un error.
            # _logger.error('------------------> Error al verificar registro SAP para el partner ID: %s', order.partner_id.name)
            _logger.error('------------------> Error al verificar registro SAP para el partner ID: %s', response.json())


    def __closeConnection(self):

        sap_endpoint_url = 'https://cl-cloud-su4.sapparapymes.cloud:50000/b1s/v1/Logout' 

        headers = {
            'Content-Type': 'application/json'  # Ajusta el tipo de contenido según lo que espera el servicio SAP
        }

        _logger.info('------------------> Datos a enviar: %s', post_data)

        response = requests.post(sap_endpoint_url, headers=headers)

        _logger.info('------------------> Status Code, %s', response.status_code)     



    def __checkPartnerSapRegistration(self, partner_id):
        # Iniciamos la conexión con SAP
        conn = self.__openConnection()


        # iniciamos la búsqueda 

        url = f'https://cl-cloud-su4.sapparapymes.cloud:50000/b1s/v1/BusinessPartners(\'{partner_id}\')?$select=CardCode,CardName,CardType'


        # Es de tipo GET

        headers = {
            'Content-Type': 'application/json',  # Ajusta el tipo de contenido según lo que espera el servicio SAP
            'Cookie': 'B1SESSION=' + conn['SessionId'] + '; ROUTEID=.node2'
        }

        response = requests.get(url, headers=headers)

        data = response.json()

        _logger.info('------------------> Status Code, %s', response.status_code)
        _logger.info('------------------> Respuesta, %s', data['CardName'])



        # Cerramos la conecxión
        self.__closeConnection()



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

        self.__checkPartnerSapRegistration('C182508500')

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

        response = requests.post(sap_endpoint_url, headers=headers)

        _logger.info('------------------> Status Code, %s', response.status_code)     


    def __checkPartnerSapRegistration(self, partner_id):
        # Iniciamos la conexión con SAP
        conn = self.__openConnection()


        _logger.info('------------------> Consultado Rut SAP, %s', partner_id)

        # iniciamos la búsqueda 

        url = f'https://cl-cloud-su4.sapparapymes.cloud:50000/b1s/v1/BusinessPartners(\'{partner_id}\')?$select=CardCode,CardName,CardType'


        # Es de tipo GET

        headers = {
            'Content-Type': 'application/json',  # Ajusta el tipo de contenido según lo que espera el servicio SAP
            'Cookie': 'B1SESSION=' + conn['SessionId'] + '; ROUTEID=.node2'
        }

        response = requests.get(url, headers=headers)

        
        # Debemos validar el status code y si es 200, entonces procesamos la respuesta y retornamos el valor
        # Si no es 200, entonces debemos crear el socio de negocio en SAP y retornar el valor
        
        if(response.status_code == 200):
            data = response.json()
            _logger.info('------------------> Status Code, %s', response.status_code)
            _logger.info('------------------> Respuesta, %s', data['CardName'])

            self._createOrderSap(data)

        else:
            _logger.info('------------------> Status Code, %s', response.status_code)
            _logger.info('------------------> Respuesta Trabajador SAP  no se encuentra, se debe crear con el Rut: %s', partner_id)

            data = self._createSocioNegocioSap(partner_id)

            if(data.status_code == 201):
                _logger.info('------------------> Usuario Creadoooooooo')
                _logger.info('------------------> Status Code, %s', data.status_code)
                _logger.info('------------------> Respuesta, %s', data['CardName'])

                self._createOrderSap(data)


        # Cerramos la conecxión
        self.__closeConnection()




    def _createSocioNegocioSap(self, partner_id):

        # Iniciamos la conexión con SAP
        conn = self.__openConnection()

        # iniciamos la búsqueda 

        url = f'https://cl-cloud-su4.sapparapymes.cloud:50000/b1s/v1/BusinessPartners'

        # Es de tipo POST

        headers = {
            'Content-Type': 'application/json',  # Ajusta el tipo de contenido según lo que espera el servicio SAP
            'Cookie': 'B1SESSION=' + conn['SessionId'] + '; ROUTEID=.node2'
        }

        post_data = {
            "CardCode": "C182508500",
            "CardName": "ALEX FREDES",
            "CardType": "cCustomer",
            "Phone1": "+56 2 26641300",
            "Cellular": "+56 9 67896947",
            "EmailAddress": "alex.fredes.l@gmail.com",
            "FederalTaxID": "15413417-4",
            "Notes": "Particular"
        }

        response = requests.post(url, json=post_data, headers=headers)

        data = response.json()

        if(response.status_code == 201):
            _logger.info('------------------> Usuario Creadoooooooo')
            _logger.info('------------------> Status Code, %s', response.status_code)
            _logger.info('------------------> Respuesta, %s', data['CardName'])

            return data

        else:
            _logger.info('------------------> Status Code, %s', response.status_code)
            _logger.info('------------------> Error al crear partnet_id: %s', partner_id)

            return data



        # Cerramos la conecxión
        self.__closeConnection()


    def _createOrderSap(data) :
        _logger.info('------------------> Creando orden SAP')

        _logger.info(' -----------> Creando la orden de venta SAP', data) 



import logging
import base64
import requests
import datetime
from odoo import models, api, fields

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    iterated = fields.Boolean(string='Iterated', store=True, default=False)
    sap_doc_entry = fields.Char(string='Doc entry Sap', store=True , default=None)
    sap_card_code = fields.Char(string='Card Code SAP', store=True , default=None)

    def check_partner_sap_registration(self):
        
        order_id = self.id

        order = self.env['sale.order'].search([('id', '=', order_id), ('iterated', '=', False)])

        
        if not order:
            _logger.info(' ******  La órden ya fue enviada a SAP ******')
            return True
    
    
        try:
            _logger.info(' ******  Se intenta crear el usuario en SAP ******')
            checkSocioNegocio = self.__checkPartnerSapRegistration(order)

            if checkSocioNegocio['status_code'] in (201, 200):
                _logger.info(' ******  USUARIO CREADO EN SAP ******')

                order.write({
                    'iterated': True,
                    'sap_doc_entry': checkSocioNegocio['data']['DocEntry'],
                    'sap_card_code': checkSocioNegocio['data']['CardCode'],
                })


                message = ('Orden Sap Creada exitosamente, DocEntry: %s, CardCode: %s') % (checkSocioNegocio['data']['DocEntry'], checkSocioNegocio['data']['CardCode'])
                return self._display_notification(message)
            else:
                raise Exception(checkSocioNegocio['message'])

            
            
        except Exception as e:
            _logger.info(' ******  ERROR AL CREAR USUARIO EN SAP ******')
            _logger.info(' ******  ERROR ****** , %s', e)
            return False



    def __checkPartnerSapRegistration(self, order):
        # Iniciamos la conexión con SAP
        conn = self.__openConnection()
        
        cardCode = 'C' + order.partner_id.vat.replace('-', '').replace('.', '')
        _logger.info(' ******  CONSULTADO RUT < %s > A SAP', cardCode)

        # iniciamos la búsqueda 
        url = f'https://cl-cloud-su4.sapparapymes.cloud:50000/b1s/v1/BusinessPartners(\'{cardCode}\')?$select=CardCode,CardName,CardType'

        # Es de tipo GET
        headers = {
            'Content-Type': 'application/json',  # Ajusta el tipo de contenido según lo que espera el servicio SAP
            'Cookie': 'B1SESSION=' + conn['SessionId'] + '; ROUTEID=.node2'
        }

        response = requests.get(url, headers=headers)
        
        socioNegocio = None

        if response.status_code == 200:
            socioNegocio = {
                
                'status_code': response.status_code,
                'message': 'Creado exitosamente',
                'data' : response.json()
            }
            
            _logger.info(' ******  USUARIO EXISTE EN SAP, OCUPAMOS EL MISMO USUARIO ******')
            _logger.info(' ******  RESPONSE ****** , %s', response)
        else:
            _logger.info(' ******  USUARIO NO EXISTE EN SAP COMO SOCIO NEGOCIO, SE DEBE CREAR ******')
            socioNegocio = self._createSocioNegocioSap(order)
            
            
        _logger.info(' ******  SOCIO NEGOCIO ****** , %s', socioNegocio)
        
        
        
        
        if(socioNegocio['status_code'] == 201 or socioNegocio['status_code'] == 200):
            
            _logger.info(' ******  USUARIO CREADO EN SAP ******')
            
            responseOrderSap = self._createOrderSap(socioNegocio['data'], order)
            
            
            self.__closeConnection()
            return {
                'status_code': responseOrderSap['status_code'],
                'message': responseOrderSap['message'],
                'data' : responseOrderSap['data']
            }

        else:
            
            _logger.info(' ******  ERROR AL CREAR USUARIO EN SAP ******')
            
            self.__closeConnection()
            return {
                'status_code': socioNegocio['status_code'],
                'message': socioNegocio['message'],
                'data' : ""
            }

        


    def _createSocioNegocioSap(self, order):


        _logger.info(' ******  CREANDO SOCIO NEGOCIO SAP ******')
        # Iniciamos la conexión con SAP
        conn = self.__openConnection()
        url = f'https://cl-cloud-su4.sapparapymes.cloud:50000/b1s/v1/BusinessPartners'

        headers = {
            'Content-Type': 'application/json',  # Ajusta el tipo de contenido según lo que espera el servicio SAP
            'Cookie': 'B1SESSION=' + conn['SessionId'] + '; ROUTEID=.node2'
        }
        
        cardCode = 'C' + order.partner_id.vat.replace('-', '').replace('.', '')

        post_data = {
            "CardCode": cardCode, # VAT + C
            "CardName": order.res_partner.name, # name
            "CardType": "cCustomer", # todo serán cCustomer
            "Phone1": order.res_partner.phone, # phone
            "Cellular": order.res_partner.mobile, # mobile
            "EmailAddress": order.res_partner.email, # email
            "FederalTaxID": order.res_partner.vat, # vat
            "Notes": order.res_company.name, # company_id.name
        }

        _logger.info(' ******  DATOS A INSERTAR : %s', post_data)

        response = requests.post(url, json=post_data, headers=headers)

        if(response.status_code == 201):
            _logger.info(' ******  USUARIO SOCIO NEGOCIO INGRESADO ******')

            return {
                'status_code': response.status_code,
                'message': 'Creado exitosamente',
                'data' : response.json()
            }

        else:
            
            _logger.info(' ******  ERROR AL CREAR SOCIO NEGOCIO SAP ******')
            return {
                'status_code': response.status_code,
                'message': 'Error al crear partnet_id: ' + order.partner_id.id,
                'data' : ""
            }

        


    def _createOrderSap(self, data, order) :
        _logger.info(' ******  Creando orden SAP ******')
        _logger.info(' ******  DATA ****** , %s', data)
        # fecha del dia
        fecha = datetime.datetime.now()
        
        
        # Debemos sumar el price_subtotal de todas las líneas de la orden
        price_subtotal = 0
        for line in order.order_line:
            price_subtotal += line.price_subtotal
            

        payload = {
            "CardCode": data['CardCode'],
            "DocDueDate": fecha.strftime("%Y-%m-%d"), # fecha de hoy 
            "Comments": "Venta realizada por integración Starkcloud", # 
            "DocumentLines":[
                {
                    "ItemCode":"I00003",
                    "Quantity":1.0, # Por ahora será solo 1 
                    "UnitPrice":price_subtotal, #select sum(price_subtotal) from sale_order_line where order_id  = 25;
                    "Dscription": "Compra realizada con Nota de venta %s" % order.id
                     # order.id # La descripción de la línea -> compra realizada según nota de venta 25
                } 
            ]
        }    


        _logger.info(' ******  PAYLOAD *******, %s', payload)


        url = f'https://cl-cloud-su4.sapparapymes.cloud:50000/b1s/v1/Orders'

        conn = self.__openConnection()
        # Es de tipo POST

        headers = {
            'Content-Type': 'application/json',  # Ajusta el tipo de contenido según lo que espera el servicio SAP
            'Cookie': 'B1SESSION=' + conn['SessionId'] + '; ROUTEID=.node2'
        }

        response = requests.post(url, json=payload, headers=headers)

        if(response.status_code == 201):
            _logger.info(' ******  ORDEN SAP CREADA ******')
            _logger.info(' ******  RESPONSE ****** , %s', response.json())


            return {
                'status_code': response.status_code,
                'message': 'Creada exitosamente',
                'data' : response.json()
            }

        else:
            _logger.info(' ******  ERROR AL CREAR ORDEN SAP ******')
            _logger.info(' ******  RESPONSE ****** , %s', response.json())

            return {
                'status_code': response.status_code,
                'message': 'Error al crear orden SAP',
                'data' : ""
            }


    def __openConnection(self):


        _logger.info(' ******  conexión con SAP ******')
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

        _logger.info(' ******   Datos a enviar: %s', post_data)

        response = requests.post(sap_endpoint_url, json=post_data, headers=headers)

        _logger.info(' ******  Status Code, %s', response.status_code)

        if response.status_code == 200:
            _logger.info(' ******  Llegamos OK al endpoint, %s', response.json())
            return response.json()
        else:
            _logger.error(' ******* Error al verificar registro SAP para el partner ID: %s', response.json())


    def __closeConnection(self):

        _logger.info(' ******  conexión con SAP ******')
        sap_endpoint_url = 'https://cl-cloud-su4.sapparapymes.cloud:50000/b1s/v1/Logout' 

        headers = { 'Content-Type': 'application/json'  }   

        response = requests.post(sap_endpoint_url, headers=headers)

        if(response.status_code == 204):
            _logger.info(' ******  Cerramos conexión con SAP, %s', response.status_code)

    @api.model
    def _display_notification(self, message, title='Operación Exitosa', type='success'):
        """Muestra una notificación en la interfaz de usuario."""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'sticky': False,
                'type': type,  # 'success', 'danger', 'warning', 'info'
            },
        }
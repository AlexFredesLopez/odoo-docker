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
    

    # Constantes con los nombres de los campos
    URL_SAP = 'SAP_URL'
    COMPANY_DB = 'SAP_COMPANY_DB'
    USER_NAME = 'SAP_USERNAME'
    PASSWORD = 'SAP_PASSWORD'
    

    def check_partner_sap_registration(self):
        
        order_id = self.id

        order = self.env['sale.order'].search([('id', '=', order_id), ('iterated', '=', False)])

        urlSap = self.env['global.parameters'].search([('parameterId', '=', self.URL_SAP)], limit=1).value
        companyDb = self.env['global.parameters'].search([('parameterId', '=', self.COMPANY_DB)], limit=1).value
        UserName = self.env['global.parameters'].search([('parameterId', '=', self.USER_NAME)], limit=1).value
        Password = self.env['global.parameters'].search([('parameterId', '=', self.PASSWORD)], limit=1).value

        if(urlSap == "" or urlSap == None or urlSap == False or urlSap == " "):
            order.message_post(body='Error al crear orden SAP: No se ha configurado la URL de SAP')
            return False

        if(companyDb == "" or companyDb == None or companyDb == False or companyDb == " "):
            order.message_post(body='Error al crear orden SAP: No se ha configurado la empresa de SAP')
            return False
        
        if(UserName == "" or UserName == None or UserName == False or UserName == " "):
            order.message_post(body='Error al crear orden SAP: No se ha configurado el usuario de SAP')
            return False

        if(Password == "" or Password == None or Password == False or Password == " "):
            order.message_post(body='Error al crear orden SAP: No se ha configurado la contraseña de SAP')
            return False

    
        
        if not order:
            _logger.info(' ******  La órden ya fue enviada a SAP ******')
            return True
    
    
        try:
            _logger.info(' ******  Se intenta crear el usuario en SAP ******')
            
            if(order.partner_id.vat == "" or order.partner_id.vat == None or order.partner_id.vat == False or order.partner_id.vat == " "):
                message = ('Error al crear orden SAP: %s') % ('El cliente no tiene RUT')
                order.message_post(body=message)
                return self._display_notification(message, title='Error al crear orden SAP', type='danger')
            
            
            
            _logger.info(' ******  RUT DEL CLIENTE ****** , %s', order.partner_id.vat)
            checkSocioNegocio = self.__checkPartnerSapRegistration(order)

            if checkSocioNegocio['status_code'] in (201, 200):

                order.write({
                    'iterated': True,
                    'sap_doc_entry': checkSocioNegocio['data']['DocEntry'],
                    'sap_card_code': checkSocioNegocio['data']['CardCode'],
                })


                message = ('Cotización Creada exitosamente. DocEntry: %s, CardCode: %s') % (checkSocioNegocio['data']['DocEntry'], checkSocioNegocio['data']['CardCode'])
                
                # agregarlo al log de la orden
            
                order.message_post(body=message)
                
                # refresh the order
                
                self._display_notification(message, title='Orden creada correctamente', type='success')
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
                
                
            else:
                
                message = ('Error al crear orden SAP: %s') % (checkSocioNegocio['message'])
                return self._display_notification(message, title='Error al crear orden SAP', type='danger')
            
        except Exception as e:

            error = ('Error al crear orden SAP: %s') % (e)
            _logger.info(' ******  ERROR AL CREAR ORDEN SAP ****** , %s', error)
            order.message_post(body=error)
            return self._display_notification("Error el crear la orden en SAP ", title='Error al crear orden SAP', type='danger')



    def __checkPartnerSapRegistration(self, order):
        # Iniciamos la conexión con SAP
        conn = self.__openConnection()
        
        cardCode = 'C' + order.partner_id.vat.replace('-', '').replace('.', '')
        _logger.info(' ******  CONSULTADO RUT < %s > A SAP', cardCode)


        urlSap = self.env['global.parameters'].search([('parameterId', '=', self.URL_SAP)], limit=1).value
        # iniciamos la búsqueda 
        url = urlSap + "BusinessPartners('" + cardCode + "')"
    
        # Es de tipo GET
        headers = {
            'Content-Type': 'application/json',  # Ajusta el tipo de contenido según lo que espera el servicio SAP
            'Cookie': 'B1SESSION=' + conn['SessionId'] + '; ROUTEID=.node2'
        }

        response = requests.get(url, headers=headers)
        
        socioNegocio = None
        
        
        _logger.info(' ******  RESPONSE SOCIO NEGOCIO ****** , %s', response.status_code)

        if response.status_code == 200 or response.status_code == 201:
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

        urlSap = self.env['global.parameters'].search([('parameterId', '=', self.URL_SAP)], limit=1).value
        url = urlSap + 'BusinessPartners'

        headers = {
            'Content-Type': 'application/json',  # Ajusta el tipo de contenido según lo que espera el servicio SAP
            'Cookie': 'B1SESSION=' + conn['SessionId'] + '; ROUTEID=.node2'
        }
        
        cardCode = 'C' + order.partner_id.vat.replace('-', '').replace('.', '')

        post_data = {
            "CardCode": cardCode, # VAT + C
            "CardName": order.partner_id.name, # name
            "CardType": "cCustomer", # todo serán cCustomer
            "Phone1": order.partner_id.phone, # phone
            "Cellular": order.partner_id.mobile, # mobile
            "EmailAddress": order.partner_id.email, # email
            "FederalTaxID": order.partner_id.vat, # vat
            "Notes": order.company_id.name, # company_id.name,
            "ProjectCode" : 9999,
            "U_NX_INDUSTRIA" : "A",
            "U_NX_SEGMENTO" : "A"
        }

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
                'message': 'Error al crear partner_id: ' + order.partner_id.id,
                'data' : response.json()
            }

        


    def _createOrderSap(self, data, order) :
        _logger.info(' ******  Creando orden SAP ******')
        # fecha del dia
        fecha = datetime.datetime.now()
        
        # Debemos sumar el price_subtotal de todas las líneas de la orden
        price_subtotal = 0
        for line in order.order_line:
            price_subtotal += line.price_subtotal
            

        payload = {
            "CardCode": data['CardCode'],
            "DocDueDate": fecha.strftime("%Y-%m-%d"), # fecha de hoy 
            "Comments": "Venta realizada por integración Starkcloud N° Cuotas %s, Cantidad Usuario %s" % (order.x_studio_meses, order.x_studio_cant_usuarios), #
            "U_NX_Origen": "StarkCloud",
            "U_NX_Partner": "H&CO Chile",
            "U_NX_ANegocios" : "Clientes",
            "DocumentLines":[
                {
                    "ItemCode": "PAAS-ATV",
                    "Quantity":1.0, # Por ahora será solo 1 
                    "UnitPrice":price_subtotal, #select sum(price_subtotal) from sale_order_line where order_id  = 25;
                    "Dscription": "Compra realizada con Nota de venta %s" % order.id,
                    "Currency": order.currency_id.name,
                    "ProjectCode" : "9999",
                    "CostingCode" : "B001",
                    "CostingCode2" : "D002",
                    "CostingCode3" : "A003",
                } 
            ]
        }    
        
        
        if(order.x_studio_pedido_ == "" or order.x_studio_pedido_ == None or order.x_studio_pedido_ == False or order.x_studio_pedido_ == " "):        
            order.write({
                'x_studio_pedido_': order.id
            })


        _logger.info(' ******  PAYLOAD  NOTA DE VENTA *******, %s', payload)

        urlSap = self.env['global.parameters'].search([('parameterId', '=', self.URL_SAP)], limit=1).value

        url = urlSap + 'Quotations'

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
        _logger.info(' ******  CREANDO CONEXIÓN A SAP ******')

        urlSap = self.env['global.parameters'].search([('parameterId', '=', self.URL_SAP)], limit=1).value
        companyDb = self.env['global.parameters'].search([('parameterId', '=', self.COMPANY_DB)], limit=1).value
        UserName = self.env['global.parameters'].search([('parameterId', '=', self.USER_NAME)], limit=1).value
        Password = self.env['global.parameters'].search([('parameterId', '=', self.PASSWORD)], limit=1).value

        sap_endpoint_url = urlSap + 'Login'

        _logger.info(' ******  URL SAP ****** , %s', sap_endpoint_url)

        # Datos que deseas enviar en el cuerpo de la solicitud POST, puede ser un diccionario de Python
        post_data = {
            "CompanyDB": companyDb,
            "Password": Password,
            "UserName": UserName
        }

        # Realiza la solicitud POST con las credenciales y los datos
        headers = {
            'Content-Type': 'application/json'  # Ajusta el tipo de contenido según lo que espera el servicio SAP
        }

        response = requests.post(sap_endpoint_url, json=post_data, headers=headers)


        _logger.info(' ******  RESPONSE CONN ****** , %s', response.json())
        if response.status_code == 200:
            return response.json()
        else:
            return self._display_notification('Error al conectar a SAP', title='Error al crear orden SAP', type='danger')


    def __closeConnection(self):
        
        sap_endpoint_url = self.urlSap + 'Logout' 

        headers = { 'Content-Type': 'application/json'  }   

        response = requests.post(sap_endpoint_url, headers=headers)

        if(response.status_code == 204):
            return False
            

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
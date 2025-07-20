# Programa para lanzar comprobantes a bizlink
# Pasos:
1.- Crear campos en maeope
    XMLToSend       varchar(MAX)
    XMLResponse     varchar(MAX)
    SignedStatus    varchar(50)
 2.- Actualizar el archivo w_atila.dll de power builder
 3.- 

 hola mundo!

# Estando en D:\Scripts\sendXML o en la raiz del proyecto se corre lo siguiente en consola para instalar el servicio
python send_xml_service.py install
# Para iniciar el servicio
python send_xml_service.py start
# Otra forma de iniciar el servicio
net start ServicioEnvioXML
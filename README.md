# Programa para lanzar comprobantes a bizlink
# Pasos:
1.  Descargar e instalar git desde: https://git-scm.com/downloads/win
2.  Descargar e instalar visual studio code desde: https://code.visualstudio.com/
3.  Descargar e instalar y configurar python desde: https://www.python.org/downloads/
    # Desactivar los alias de ejecucion
    Presionar Windows + i
    > Aplicaciones - Del lado izquierdo
        > Configuracion avanzada de aplicaciones
            > Alias de ejecucuón de aplicaciones
                - Desactivar "Instalador de aplicaciones - Python.exe" Apagar
                - Desactivar "Instalador de aplicaciones - Python3.exe" Apagar
    # Agregar al Path de windows
    > buscar la siguiete direccion: C:\Users\SERVIDOR\AppData\Local\Programs\Python\
        Copiar:
        C:\Users\SERVIDOR\AppData\Local\Programs\Python\Python313
        C:\Users\SERVIDOR\AppData\Local\Programs\Python\Python313\Scripts
    > Presionar windows y buscar "variables de entorno" -> Editar las variables de entorno del sistema
        Se abrirà un fomrulario en la parte inferior ingresar a donde dice "Variables de entorno"
        Se abrirà otro formulario, seleccionamos el que dice Path, le damos editar
        Clic en nuevo y pegamos: C:\Users\SERVIDOR\AppData\Local\Programs\Python\Python313
        Clic en nuevo y pegamos: C:\Users\SERVIDOR\AppData\Local\Programs\Python\Python313\Scripts
4.  Verificar instalación desde consola: python --version
    >> Python 3.13.5
5.  Ingresar al SQL y Crear campos corriendo en un nuevo query:
    En maeope si no es restaurante: 
    >>
    use DbLaBaseDeDatos    
    ALTER TABLE MAEOPE
    ADD
        XMLToSend    VARCHAR(MAX),
        XMLResponse  VARCHAR(MAX),
        SignedStatus VARCHAR(50);

    Para validar si ya esta creado se corre lo siguiente en SQL:
    >> select top 1 XMLToSend, XMLResponse, SignedStatus from MAEOPE

    En MAEFAC si es restaurante
    >>
    use DbLaBaseDeDatos    
    ALTER TABLE MAEFAC
    ADD
        XMLToSend    VARCHAR(MAX),
        XMLResponse  VARCHAR(MAX),
        SignedStatus VARCHAR(50);
    
    Para validar si ya este creado se corre lo siguiente en SQL:
    >> select top 1 XMLToSend, XMLResponse, SignedStatus from MAEFAC

6.  Actualizar el archivo w_atila.dll de power builder

7.  Se ingresa a la unidad base según sea el caso desde consola
    >>C:
    >>D:
8.  Se crea la carpeta Scripts:
    >> mkdir Scripts
    se ingresa a la carpeta
    >> cd Scripts
9.  Clonamos el repositorio
    >> git clone https://github.com/yuripc2023/sendXML.git
    >> cd sendXML
    Para actualizar los cambios
    >> git pull
10.  isntalamos los requerimientos
    >> pip install -r .\requirements.txt
    >> code .
11. Copiamos o creamos el archivo .env con los siguientes parametros:

    # SQL Server
    SQL_SERVER=XXX
    SQL_DATABASE=XX
    SQL_USER=XX
    SQL_PASSWORD=XX
    # Tec - Res
    Rubro=RES

    # SOAP
    SOAP_WSDL=http://ec2-52-26-118-179.us-west-2.compute.amazonaws.com/invoker21?wsdl
    SOAP_USER=XX
    SOAP_PASS=XX

12. Para probar el servicio:
    >> python .\send_xml.py
13. Tener cuidado con la version del driver de Microsoft SQL Server
    De preferencia usar:
    f"DRIVER={{ODBC Driver 11 for SQL Server}};"
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"

    Ver la relacion de drivers
    Win + R: odbcad32.exe  
14. Estando en D:\Scripts\sendXML o en la raiz del proyecto se corre lo siguiente en consola para instalar el servicio
    python send_xml_service.py install
    # Para iniciar el servicio
15. Iniciamos el servio  
    python send_xml_service.py start
16. Ver el estado del servicio desde consola
    >> Get-Service -Name "ServicioEnvioXML"
17. Matar el servicio, PID se extrae desde administrador de tareas/Servicios = ServicioEnvioXML
    taskkill /PID 15036 /F
18. Para eliminar el servicio
    >> python send_xml_service.py remove

19. Como revisar si esta funcionando bien?
    revisar el archivo: envio_xml.log, debe salir algo asì:
    
        2025-07-20 12:46:05,487 - INFO - \u23f8\ufe0f No hay comprobantes por enviar. Esperando 10 segundos...
        2025-07-20 12:46:15,487 - INFO - \U0001f50d Buscando XMLs pendientes...
        2025-07-20 12:46:15,502 - INFO - \u23f8\ufe0f No hay comprobantes por enviar. Esperando 10 segundos...
        2025-07-20 12:46:25,503 - INFO - \U0001f50d Buscando XMLs pendientes...

20. Para que el servicio se inicie en automàtico desde power shell
    >> cmd /c sc config ServicioEnvioXML start= auto
21. Ingresar el SQL server y correr el archivo alter_view_vw_comprobante.sql (TEC) o 
    Simplemente agregar el campo en la vista Operacion.SignedStatus (recomendado)
    


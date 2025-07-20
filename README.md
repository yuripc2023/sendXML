# Programa para lanzar comprobantes a bizlink
# Pasos:
1.  Instalar python, descargar e instalar desde: https://www.python.org/downloads/
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
2.  Verificar instalación desde consola: python --version
    >> Python 3.13.5
3.  Ingresar al SQL y Crear campos corriendo en un nuevo query:
    En maeope si no es restaurante: 
    >>
    use DbLaBaseDeDatos    
    ALTER TABLE MAEOPE
    ADD
        XMLToSend    VARCHAR(MAX),
        XMLResponse  VARCHAR(MAX),
        SignedStatus VARCHAR(50);
    
    En MAEFAC si es restaurante
    >>
    use DbLaBaseDeDatos    
    ALTER TABLE MAEFAC
    ADD
        XMLToSend    VARCHAR(MAX),
        XMLResponse  VARCHAR(MAX),
        SignedStatus VARCHAR(50);

 4. Actualizar el archivo w_atila.dll de power builder
 5. descargar git desde: https://git-scm.com/downloads/win
 6. Se ingresa a la unidad base según sea el caso desde consola
    >>C:
    >>D:
7.  Se crea la carpeta Scripts:
    >> mkdir Scripts
    se ingresa a la carpeta
    >> cd Scripts
8.  Clonamos el repositorio
    >> git clone https://github.com/yuripc2023/sendXML.git
9.  Instalar visual studio code desde: https://code.visualstudio.com/


# Estando en D:\Scripts\sendXML o en la raiz del proyecto se corre lo siguiente en consola para instalar el servicio
python send_xml_service.py install
# Para iniciar el servicio
python send_xml_service.py start
# Otra forma de iniciar el servicio
net start ServicioEnvioXML
# Matar el servicio, PID se extrae desde administrador de tareas/Servicios = ServicioEnvioXML
taskkill /PID 15036 /F

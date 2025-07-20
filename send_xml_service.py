# send_xml_service.py

import win32serviceutil
import win32service
import win32event
import servicemanager
import time
import logging
from logging.handlers import RotatingFileHandler
import os

# --- INICIO DE CAMBIOS PARA SOPORTE DE SERVICIO ---

# Obtener la ruta del directorio del script actual
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Asegurarse de que el log del servicio va al mismo archivo que el script principal
log_file_path = os.path.join(BASE_DIR, "envio_xml.log")

# Configuración del log para el servicio. Esto asegura que los eventos del servicio
# (inicio, parada, errores críticos de SvcDoRun) también se registren.
# Usamos el mismo archivo y formato para coherencia.
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
# --- FIN DE CAMBIOS PARA SOPORTE DE SERVICIO ---

# Importar la función principal del otro script
# Esta importación debe ser después de que el logging básico esté configurado,
# aunque en este caso, ambos scripts configuran el mismo archivo de log, así que es más flexible.
try:
    from send_xml import main
except ImportError as e:
    # Esto capturaría si send_xml.py no se puede importar al iniciar el servicio
    logging.error(f"❌ Error al importar send_xml.main: {e}", exc_info=True)
    # Considera salir aquí si la importación es fatal para el servicio.
    # Esto puede ocurrir si hay un error de sintaxis en send_xml.py, por ejemplo.
    main = None # Para evitar NameError si el servicio intenta ejecutar main()

class PythonWindowsService(win32serviceutil.ServiceFramework):
    _svc_name_ = "ServicioEnvioXML"
    _svc_display_name_ = "Servicio de Envío XML por SOAP"
    _svc_description_ = "Este servicio envía XMLs automáticamente vía SOAP desde Python."

    def __init__(self, args):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True
        # Puedes añadir un logger específico para el servicio si lo deseas,
        # pero para simplicidad, estamos usando el logger raíz que apunta a envio_xml.log

    def SvcStop(self):
        # Reporta el estado de detención pendiente al Service Control Manager
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        logging.info("🛑 Solicitud de detención del servicio recibida. Señalizando para detener el bucle principal.")
        self.running = False # Aunque main() no usa esta bandera directamente, es buena práctica
        win32event.SetEvent(self.hWaitStop) # Señaliza el evento para detener si SvcDoRun lo espera

    def SvcDoRun(self):
        # Registra el inicio del servicio en el Visor de Eventos de Windows
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '') # Nombre del servicio para el log de eventos
        )
        logging.info("🟢 Servicio iniciado correctamente por el Service Control Manager.")
        
        if main is None:
            logging.error("❌ No se pudo ejecutar la lógica principal (send_xml.main) debido a un error de importación.")
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_ERROR_TYPE,
                servicemanager.PYS_SERVICE_ERROR,
                ("Error de importación de la lógica principal.", '')
            )
            return # El servicio no puede continuar sin la función principal

        try:
            # Ejecuta la función principal de tu script.
            # Esta función DEBE contener un bucle infinito (o un loop de tiempo)
            # para que el servicio no se detenga inmediatamente.
            main()
        except Exception as e:
            # Captura cualquier excepción no manejada que escape de main()
            logging.error(f"❌ Error CRÍTICO no manejado en la función principal (main()): {e}", exc_info=True)
            # También loguea al Visor de Eventos de Windows para una visibilidad más alta
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_ERROR_TYPE,
                servicemanager.PYS_SERVICE_ERROR,
                (f"Error fatal en {self._svc_name_}: {str(e)}", '')
            )
        finally:
            logging.info("🛑 La función principal (main) ha finalizado. El servicio se detendrá.")
            # Reporta el estado de detención al Service Control Manager
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)

if __name__ == '__main__':
    # Esto permite manejar comandos como 'install', 'uninstall', 'start', 'stop', 'debug'
    # desde la línea de comandos.
    # Ejemplo: python send_xml_service.py install
    # Ejemplo: python send_xml_service.py start
    win32serviceutil.HandleCommandLine(PythonWindowsService)
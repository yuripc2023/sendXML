# send_xml_service.py

import win32serviceutil
import win32service
import win32event
import servicemanager
import time
import logging
from logging.handlers import RotatingFileHandler
from send_xml import main  # ⬅️ Aquí importamos la función principal

logging.basicConfig(
    filename='envio_xml.log',
    level=logging.INFO,
    format='[%(asctime)s] %(message)s'
)

class PythonWindowsService(win32serviceutil.ServiceFramework):
    _svc_name_ = "ServicioEnvioXML"
    _svc_display_name_ = "Servicio de Envío XML por SOAP"
    _svc_description_ = "Este servicio envía XMLs automáticamente vía SOAP desde Python."

    def __init__(self, args):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.running = False
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        logging.info("🟢 Servicio iniciado correctamente")
        try:
            main()  # 👈 Aquí ejecutamos la lógica del envío
        except Exception as e:
            logging.error(f"❌ Error al ejecutar main(): {e}")
        logging.info("🛑 Servicio detenido")

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(PythonWindowsService)

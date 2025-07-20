import win32serviceutil
import win32service
import win32event
import servicemanager
import time

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
        servicemanager.LogInfoMsg("Servicio Python Iniciado.")
        while self.running:
            try:
                # Aquí llamas a tu función principal (ej: enviar_xml())
                print("Ejecutando tarea de envío XML...")
                time.sleep(10)  # Cambia por la frecuencia deseada
            except Exception as e:
                servicemanager.LogErrorMsg(f"Error: {str(e)}")
            time.sleep(60)  # tiempo entre ejecuciones

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(PythonWindowsService)

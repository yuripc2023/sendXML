# send_xml.py

import pyodbc
from zeep import Client
from zeep.transports import Transport
from requests import Session
from requests.auth import HTTPBasicAuth
import logging
from dotenv import load_dotenv
import os
import requests
import time
import datetime # Importar datetime para manejar fechas
import win32event # Importar para el manejo del evento de detención del servicio
import xml.etree.ElementTree as ET # Importar la librería para parsear XML
import html # Importar para decodificar entidades HTML
from lxml import etree

# Obtener la ruta del directorio del script actual
# Esto es crucial para que el .env y el log se encuentren sin importar dónde se ejecute el servicio
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cargar variables desde .env usando la ruta absoluta
dotenv_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    # Si el .env no se encuentra, logueamos un error crítico y (opcionalmente) salimos.
    # Usamos print aquí temporalmente porque el logger aún no está configurado al 100%.
    # Una vez que el logger esté activo, los mensajes irán allí.
    print(f"ERROR CRÍTICO: Archivo .env no encontrado en: {dotenv_path}")
    # Para un servicio, si las variables son críticas, se recomienda salir o lanzar una excepción.
    # raise FileNotFoundError(f".env file not found at {dotenv_path}")

# --- CONFIGURACIÓN DE LOGGING MÁS ROBUSTA ---
log_file_path = os.path.join(BASE_DIR, "envio_xml.log")
file_handler = None # Variable global para almacenar el handler del archivo de log
_service_stop_event = None # Variable global para el evento de detención del servicio

def setup_logging():
    """Configura o reconfigura el logger principal para el servicio."""
    global file_handler
    # Cerrar y remover handlers existentes para evitar duplicados al reconfigurar
    if logging.root.handlers:
        for handler in list(logging.root.handlers):
            logging.root.removeHandler(handler)
            handler.close()

    file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    
    logging.root.addHandler(file_handler)
    logging.root.setLevel(logging.INFO)
    # Silenciar logs ruidosos de librerías para mantener el log limpio
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

setup_logging() # Llama a la configuración inicial de logging al inicio del script

# --- FUNCIONES PARA LA LIMPIEZA DEL LOG ---
LOG_CLEANUP_INTERVAL_DAYS = 5 # Intervalo de limpieza en días
LAST_CLEANUP_FILE = os.path.join(BASE_DIR, "last_log_cleanup.txt") # Archivo para guardar la fecha de la última limpieza

def get_last_cleanup_date():
    """Lee la fecha de la última limpieza del archivo."""
    if os.path.exists(LAST_CLEANUP_FILE):
        with open(LAST_CLEANUP_FILE, 'r') as f:
            try:
                return datetime.datetime.strptime(f.read().strip(), '%Y-%m-%d').date()
            except ValueError:
                logging.warning(f"Formato de fecha inválido en {LAST_CLEANUP_FILE}. Asumiendo limpieza anterior.")
                return datetime.date.min # Una fecha muy antigua para forzar la limpieza
    return datetime.date.min # Si el archivo no existe, limpiar la primera vez

def update_last_cleanup_date():
    """Actualiza la fecha de la última limpieza en el archivo."""
    with open(LAST_CLEANUP_FILE, 'w') as f:
        f.write(datetime.date.today().strftime('%Y-%m-%d'))

def clean_log_file():
    """Verifica si es necesario limpiar el archivo de log y lo hace."""
    last_cleanup = get_last_cleanup_date()
    today = datetime.date.today()

    if (today - last_cleanup).days >= LOG_CLEANUP_INTERVAL_DAYS:
        logging.info(f"📆 Han pasado {LOG_CLEANUP_INTERVAL_DAYS} días desde la última limpieza del log. Procediendo a limpiar...")
        
        try:
            # Importante: Detener el logger para liberar el archivo antes de intentar eliminarlo
            global file_handler
            if file_handler:
                logging.root.removeHandler(file_handler)
                file_handler.close()
                file_handler = None # Resetear el handler
                
            # Eliminar el archivo de log
            if os.path.exists(log_file_path):
                os.remove(log_file_path)
                logging.info(f"🗑️ Archivo de log '{log_file_path}' eliminado.")
            else:
                logging.info(f"Archivo de log '{log_file_path}' no encontrado para eliminar. Creando uno nuevo.")
            
            # Reconfigurar el logging para que el servicio siga escribiendo en un nuevo archivo
            setup_logging()
            logging.info("📝 Se ha reconfigurado el logging para escribir en un nuevo archivo de log.")
            
            update_last_cleanup_date()
            logging.info(f"✅ Fecha de la última limpieza actualizada a: {today.strftime('%Y-%m-%d')}.")

        except Exception as e:
            logging.error(f"❌ Error al intentar limpiar el archivo de log: {e}", exc_info=True)
            # Intentar reconfigurar el logger incluso si falla la eliminación (para que siga logueando)
            setup_logging()
            
    else:
        logging.info(f"🗓️ No es necesario limpiar el log todavía. Próxima limpieza en {LOG_CLEANUP_INTERVAL_DAYS - (today - last_cleanup).days} día(s).")

# --- FUNCIÓN PARA INICIALIZAR EL EVENTO DE DETENCIÓN DESDE EL SERVICIO ---
def init_service_stop_event(event):
    """Inicializa el objeto de evento para la detención del servicio."""
    global _service_stop_event
    _service_stop_event = event
    logging.info("Evento de detención del servicio inicializado.")


# Leer variables del entorno
SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")
SQL_USER = os.getenv("SQL_USER")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")

SOAP_WSDL = os.getenv("SOAP_WSDL")
SOAP_USER = os.getenv("SOAP_USER")
SOAP_PASS = os.getenv("SOAP_PASS")

# Validación básica de que las variables de entorno se cargaron
if not all([SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASSWORD, SOAP_WSDL, SOAP_USER, SOAP_PASS]):
    logging.error("❌ ERROR: Una o más variables de entorno (SQL o SOAP) no están definidas. Revisa tu archivo .env.")
    # import sys
    # sys.exit(1) # Si es crítico, descomentar esto para que el script falle temprano

# Obtener XML y datos clave de la BD
def get_pending_xmls_from_db():
    try:
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};" # Usando el Driver 11 como indicaste
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USER};"
            f"PWD={SQL_PASSWORD}"
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT OPECOD, EJECOD, MAE_ASOCOD, XMLToSend
            FROM MAEOPE
            WHERE XMLToSend IS NOT NULL AND XMLResponse IS NULL
        """)
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        logging.error(f"❌ Error al obtener XMLs de la base de datos: {e}", exc_info=True)
        return []

# Enviar XML por SOAP
def send_xml_to_soap(xml_str):
    try:
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "" # Coloca aquí el SOAPAction si tu endpoint lo requiere, ej. "http://tempuri.org/MyMethod"
        }
        response = requests.post(
            SOAP_WSDL,
            data=xml_str.encode("utf-8"),
            headers=headers,
            auth=HTTPBasicAuth(SOAP_USER, SOAP_PASS)
        )
        response.raise_for_status() # Lanza excepción si status != 200 (error HTTP)
        logging.info(f"✅ Respuesta recibida del SOAP (Estado: {response.status_code}): {response.text}")
        return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Error al enviar XML vía SOAP: {e}", exc_info=True)
        return f"ERROR: {e}"
    except Exception as e:
        logging.error(f"❌ Error inesperado en send_xml_to_soap: {e}", exc_info=True)
        return f"ERROR_INESPERADO: {e}"

# --- NUEVA FUNCIÓN PARA EXTRAER EL ESTADO DE LA FIRMA DEL XML DE RESPUESTA ---

def extract_signed_status(soap_response):
    try:
        soap_root = etree.fromstring(soap_response.encode("utf-8"))

        # Buscar nodo <return> sin importar namespace
        return_node = soap_root.find('.//{*}return')
        if return_node is None or not return_node.text:
            logger.warning("⚠️ No se encontró el nodo <return> o está vacío en la respuesta SOAP.")
            return "UNKNOWN_STATUS"

        inner_xml = html.unescape(return_node.text)
        inner_root = etree.fromstring(inner_xml.encode("utf-8"))

        status_node = inner_root.find('.//{*}status')
        return status_node.text if status_node is not None else "UNKNOWN_STATUS"

    except Exception as e:
        logger.error(f"❌ Error inesperado al extraer el estado firmado: {e}", exc_info=True)
        return "UNKNOWN_STATUS"

# Actualizar XMLResponse y SignedStatus en la BD
def update_response_in_db(ope_cod, eje_cod, mae_aso_cod, response_text):
    # Extraemos el estado de la firma primero
    signed_status = extract_signed_status(response_text)
    
    # Mapear el estado a lo que quieres guardar en la DB
    # Por ejemplo, si el status del XML interno es 'OK', lo guardamos como 'SIGNED'
    # Si es 'ERROR', lo guardamos como 'ERROR_SOAP', etc.
    db_signed_status = "UNKNOWN_STATUS" # Valor por defecto si no se puede determinar
    if signed_status == "OK":
        db_signed_status = "SIGNED"
    elif signed_status == "ERROR":
        db_signed_status = "ERROR_SOAP"
    elif signed_status: # Si se encontró un valor pero no es OK ni ERROR
        db_signed_status = signed_status # Guardar el valor tal cual si no es mapeado

    try:
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};" # Usando el Driver 11 como indicaste
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USER};"
            f"PWD={SQL_PASSWORD}"
        )
        cursor = conn.cursor()
        
        # Asegúrate de que tu tabla MAEOPE tenga una columna llamada SignedStatus (ej. VARCHAR(50))
        # Y que el tipo de dato sea adecuado para almacenar cadenas como 'SIGNED', 'ERROR_SOAP', 'UNKNOWN_STATUS'.
        cursor.execute("""
            UPDATE MAEOPE
            SET XMLResponse = ?, SignedStatus = ?
            WHERE OPECOD = ? AND EJECOD = ? AND MAE_ASOCOD = ?
        """, (response_text, db_signed_status, ope_cod, eje_cod, mae_aso_cod))
        
        conn.commit()
        conn.close()
        logging.info(f"✅ XMLResponse y SignedStatus='{db_signed_status}' actualizado para OPECOD={ope_cod}, EJECOD={eje_cod}, MAE_ASOCOD={mae_aso_cod}.")
    except Exception as e:
        logging.error(f"❌ Error al actualizar XMLResponse y SignedStatus para OPECOD={ope_cod}: {e}", exc_info=True)

# Validar conexión inicial a SQL
def test_conexion_sql():
    try:
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};" # Usando el Driver 11 como indicaste
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USER};"
            f"PWD={SQL_PASSWORD}"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT GETDATE()")
        result = cursor.fetchone()
        conn.close()
        logging.info(f"✅ Conexión SQL Server exitosa. Fecha actual: {result[0]}")
    except Exception as e:
        logging.error(f"❌ Error de conexión inicial a SQL Server: {e}", exc_info=True)

# Función principal
def main():
    # Es crucial que test_conexion_sql() y cualquier otra función al inicio
    # utilice logging en lugar de print, ya que el servicio no tendrá una consola.
    test_conexion_sql()
    
    logging.info("🟢 Servicio iniciando el bucle de búsqueda y envío de XMLs.")
    
    # Definir el timeout para WaitForSingleObject
    # Cada 10 segundos, comprobamos si hay XMLs pendientes.
    # Pero cada 1 segundo (o cada X segundos más pequeños que 10), comprobamos si el servicio debe detenerse.
    check_interval_seconds = 10 # Tiempo que se espera para buscar nuevos XMLs

    while True:
        # Llama a la función de limpieza del log al inicio de cada ciclo principal
        # Esto asegura que se verifique la limpieza periódicamente
        clean_log_file()

        # Aquí usamos WaitForSingleObject con un timeout.
        # Esto permite que el bucle "despierte" ya sea porque el tiempo de espera ha terminado
        # O porque se ha seteado el evento de detención.
        # Un timeout más pequeño (ej. 1 segundo) hace que el servicio responda más rápido a la detención.
        # Si el evento _service_stop_event no está configurado (ej. ejecutando directamente el script),
        # esto simplemente actuará como un time.sleep().
        if _service_stop_event:
            wait_result = win32event.WaitForSingleObject(_service_stop_event, check_interval_seconds * 1000) # Tiempo en milisegundos
            if wait_result == win32event.WAIT_OBJECT_0:
                # El evento se ha seteado, lo que significa que se ha solicitado detener el servicio.
                logging.info("🛑 Señal de detención de servicio recibida. Finalizando bucle principal.")
                break # Salir del bucle while True
        else:
            # Si se ejecuta el script directamente (no como servicio), simplemente espera.
            time.sleep(check_interval_seconds)

        logging.info("🔍 Buscando XMLs pendientes...")
        xml_rows = get_pending_xmls_from_db()

        if not xml_rows:
            logging.info("⏸️ No hay comprobantes por enviar. Esperando el siguiente ciclo.")
            continue # Vuelve al inicio del bucle para la siguiente búsqueda (y chequeo de detención/limpieza)

        logging.info(f"📚 {len(xml_rows)} comprobante(s) pendiente(s) encontrado(s). Procesando...")
        for row in xml_rows:
            ope_cod, eje_cod, mae_aso_cod, xml_str = row
            logging.info(f"📦 Procesando XML para OPECOD={ope_cod}, EJECOD={eje_cod}, MAE_ASOCOD={mae_aso_cod}")
            
            try:
                response = send_xml_to_soap(xml_str)
                if response.startswith("ERROR:"):
                    logging.warning(f"⚠️ El envío SOAP para OPECOD={ope_cod} falló, la respuesta es un mensaje de error. No se actualizará la tabla como exitoso.")
                else:
                    update_response_in_db(ope_cod, eje_cod, mae_aso_cod, response)
            except Exception as e:
                logging.error(f"❌ Fallo inesperado al procesar OPECOD={ope_cod}: {e}", exc_info=True)
                continue # Sigue con el siguiente comprobante para no detener el servicio

        logging.info("✅ Lote de comprobantes procesado. Preparando para el siguiente ciclo.")
        # La espera se maneja ahora con WaitForSingleObject al inicio del bucle.


# Ejecutar script directamente (para pruebas fuera del servicio)
if __name__ == "__main__":
    # Puedes ejecutar este script directamente desde la terminal para probar la lógica.
    # Los mensajes irán al archivo de log configurado.
    logging.info("🚀 send_xml.py ejecutado directamente (no como servicio).")
    main()
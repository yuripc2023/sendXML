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
import html # Importar para decodificar entidades HTML
from lxml import etree # Importar lxml para parsear XML

SCRIPT_VERSION = "1.0.0" 

# Obtener la ruta del directorio del script actual
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cargar variables desde .env usando la ruta absoluta
dotenv_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print(f"ERROR CRÍTICO: Archivo .env no encontrado en: {dotenv_path}")
    # Considera una excepción crítica si el .env es indispensable para el inicio
    # raise FileNotFoundError(f".env file not found at {dotenv_path}")

# --- CONFIGURACIÓN DE LOGGING MÁS ROBUSTA ---
log_file_path = os.path.join(BASE_DIR, "envio_xml.log")
file_handler = None # Variable global para almacenar el handler del archivo de log
_service_stop_event = None # Variable global para el evento de detención del servicio

def setup_logging():
    """Configura o reconfigura el logger principal para el servicio."""
    global file_handler
    if logging.root.handlers:
        for handler in list(logging.root.handlers):
            logging.root.removeHandler(handler)
            handler.close()

    file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    
    logging.root.addHandler(file_handler)
    logging.root.setLevel(logging.INFO)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

setup_logging()

# --- FUNCIONES PARA LA LIMPIEZA DEL LOG ---
LOG_CLEANUP_INTERVAL_DAYS = 2 # Intervalo de limpieza en días
LAST_CLEANUP_FILE = os.path.join(BASE_DIR, "last_log_cleanup.txt") # Archivo para guardar la fecha de la última limpieza

def get_last_cleanup_date():
    """Lee la fecha de la última limpieza del archivo."""
    if os.path.exists(LAST_CLEANUP_FILE):
        with open(LAST_CLEANUP_FILE, 'r') as f:
            try:
                return datetime.datetime.strptime(f.read().strip(), '%Y-%m-%d').date()
            except ValueError:
                logging.warning(f"Formato de fecha inválido en {LAST_CLEANUP_FILE}. Asumiendo limpieza anterior.")
                return datetime.date.min
    return datetime.date.min

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
            global file_handler
            if file_handler:
                logging.root.removeHandler(file_handler)
                file_handler.close()
                file_handler = None
                
            if os.path.exists(log_file_path):
                os.remove(log_file_path)
                logging.info(f"🗑️ Archivo de log '{log_file_path}' eliminado.")
            else:
                logging.info(f"Archivo de log '{log_file_path}' no encontrado para eliminar. Creando uno nuevo.")
            
            setup_logging()
            logging.info("📝 Se ha reconfigurado el logging para escribir en un nuevo archivo de log.")
            
            update_last_cleanup_date()
            logging.info(f"✅ Fecha de la última limpieza actualizada a: {today.strftime('%Y-%m-%d')}.")

        except Exception as e:
            logging.error(f"❌ Error al intentar limpiar el archivo de log: {e}", exc_info=True)
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

# NUEVA VARIABLE DE ENTORNO: Rubro
RUBRO = os.getenv("Rubro")

# Validación básica de que las variables de entorno se cargaron
if not all([SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASSWORD, SOAP_WSDL, SOAP_USER, SOAP_PASS, RUBRO]):
    logging.error("❌ ERROR: Una o más variables de entorno (SQL, SOAP o Rubro) no están definidas. Revisa tu archivo .env.")
    # import sys
    # sys.exit(1)

# --- Funciones auxiliares para determinar la tabla ---
def get_table_names(rubro):
    """Retorna los nombres de las tablas de consulta y actualización según el rubro."""
    if rubro and rubro.upper() == "TEC":
        return "MAEOPE", "MAEOPE"
    elif rubro and rubro.upper() == "RES":
        return "MAEFAC", "MAEFAC"
    else:
        logging.error(f"❌ ERROR: Rubro '{rubro}' no reconocido. Se espera 'Tec' o 'Res'.")
        # Por seguridad, podrías decidir lanzar una excepción o usar una tabla por defecto
        # En este caso, devolveremos None para que las funciones lo manejen.
        return None, None

# Obtener XML y datos clave de la BD
def get_pending_xmls_from_db():
    table_name, _ = get_table_names(RUBRO)
    if not table_name:
        return []

    try:
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 11 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USER};"
            f"PWD={SQL_PASSWORD}"
        )
        cursor = conn.cursor()
        query = f"""
            SELECT OPECOD, EJECOD, MAE_ASOCOD, XMLToSend
            FROM {table_name}
            WHERE XMLToSend IS NOT NULL AND XMLResponse IS NULL
        """
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        logging.info(f"🔍 Consulta de XMLs pendientes en tabla '{table_name}' completada.")
        return results
    except Exception as e:
        logging.error(f"❌ Error al obtener XMLs de la tabla '{table_name}': {e}", exc_info=True)
        return []

# Enviar XML por SOAP
def send_xml_to_soap(xml_str):
    try:
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "" # Coloca aquí el SOAPAction si tu endpoint lo requiere
        }
        response = requests.post(
            SOAP_WSDL,
            data=xml_str.encode("utf-8"),
            headers=headers,
            auth=HTTPBasicAuth(SOAP_USER, SOAP_PASS)
        )
        response.raise_for_status()
        logging.info(f"✅ Respuesta recibida del SOAP (Estado: {response.status_code}): {response.text}")
        return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Error al enviar XML vía SOAP: {e}", exc_info=True)
        return f"ERROR: {e}"
    except Exception as e:
        logging.error(f"❌ Error inesperado en send_xml_to_soap: {e}", exc_info=True)
        return f"ERROR_INESPERADO: {e}"

# --- FUNCIÓN PARA EXTRAER EL ESTADO DE LA FIRMA DEL XML DE RESPUESTA ---
def extract_signed_status(soap_response):
    try:
        soap_root = etree.fromstring(soap_response.encode("utf-8"))

        return_node = None
        for elem in soap_root.iter():
            local_tag = etree.QName(elem.tag).localname
            
            if local_tag == 'return' and elem.text is not None and elem.text.strip() != "":
                return_node = elem
                break

        if return_node is None:
            logging.warning("⚠️ No se encontró el nodo <return> (con contenido) en la respuesta SOAP externa.")
            # logging.debug(f"Respuesta SOAP completa recibida para extract_signed_status: {soap_response}") # Descomentar para depuración
            return "UNKNOWN_STATUS"

        nested_xml_string = html.unescape(return_node.text)
        inner_root = etree.fromstring(nested_xml_string.encode("utf-8"))

        status_node = inner_root.find('.//{*}status')

        if status_node is not None and status_node.text is not None and status_node.text.strip() != "":
            return status_node.text.strip()
        else:
            logging.warning("No se encontró el nodo <status> dentro de <document> o está vacío en el XML de respuesta anidado.")
            return "UNKNOWN_STATUS"

    except etree.XMLSyntaxError as e:
        logging.error(f"❌ Error de sintaxis XML al parsear respuesta SOAP o XML interno: {e}", exc_info=True)
        return "UNKNOWN_STATUS"
    except Exception as e:
        logging.error(f"❌ Error inesperado al extraer el estado firmado: {e}", exc_info=True)
        return "UNKNOWN_STATUS"

# Actualizar XMLResponse y SignedStatus en la BD
def update_response_in_db(ope_cod, eje_cod, mae_aso_cod, response_text):
    _, table_name = get_table_names(RUBRO) # Obtener el nombre de la tabla para actualizar
    if not table_name:
        logging.error(f"❌ No se pudo determinar la tabla para actualizar para Rubro='{RUBRO}'.")
        return

    signed_status = extract_signed_status(response_text)
    
    db_signed_status = "UNKNOWN_STATUS"
    if signed_status == "SIGNED": # Usamos directamente "SIGNED" que viene del XML
        db_signed_status = "SIGNED"
    elif signed_status == "OK": # Si en algún caso el XML interno devuelve "OK" y no "SIGNED"
        db_signed_status = "OK_PROCESSED" # Podrías poner otro estado para diferenciar
    elif "ERROR" in signed_status.upper(): # Si la respuesta contiene ERROR
        db_signed_status = "ERROR_SOAP"
    else: # Cualquier otro valor o si no se encontró
        db_signed_status = signed_status # Guardar el valor tal cual si no es mapeado

    try:
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 11 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USER};"
            f"PWD={SQL_PASSWORD}"
        )
        cursor = conn.cursor()
        
        # Consulta de actualización dinámica según la tabla
        update_query = f"""
            UPDATE {table_name}
            SET XMLResponse = ?, SignedStatus = ?
            WHERE OPECOD = ? AND EJECOD = ? AND MAE_ASOCOD = ?
        """
        cursor.execute(update_query, (response_text, db_signed_status, ope_cod, eje_cod, mae_aso_cod))
        
        conn.commit()
        conn.close()
        logging.info(f"✅ XMLResponse y SignedStatus='{db_signed_status}' actualizado en tabla '{table_name}' para OPECOD={ope_cod}, EJECOD={eje_cod}, MAE_ASOCOD={mae_aso_cod}.")
    except Exception as e:
        logging.error(f"❌ Error al actualizar XMLResponse y SignedStatus en tabla '{table_name}' para OPECOD={ope_cod}: {e}", exc_info=True)

# Validar conexión inicial a SQL
def test_conexion_sql():
    try:
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 11 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USER};"
            f"PWD={SQL_PASSWORD}"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT GETDATE()")
        result = cursor.fetchone()
        conn.close()
        logging.info(f"✅ Conexión SQL Server exitosa a SERVER='{SQL_SERVER}', DATABASE='{SQL_DATABASE}'. Fecha actual: {result[0]}")
    except Exception as e:
        logging.error(f"❌ Error de conexión inicial a SQL Server: {e}", exc_info=True)

# Función principal
def main():
    logging.info(f"ATIC Perú")
    logging.info(f"✨ Iniciando servicio send_xml.py - Versión: {SCRIPT_VERSION} ✨")
    test_conexion_sql()
    logging.info(f"🟢 Servicio iniciando el bucle de búsqueda y envío de XMLs para Rubro: '{RUBRO}'.")
    
    check_interval_seconds = 10 

    while True:
        clean_log_file()

        if _service_stop_event:
            wait_result = win32event.WaitForSingleObject(_service_stop_event, check_interval_seconds * 1000)
            if wait_result == win32event.WAIT_OBJECT_0:
                logging.info("🛑 Señal de detención de servicio recibida. Finalizando bucle principal.")
                break
        else:
            time.sleep(check_interval_seconds)

        logging.info("🔍 Buscando XMLs pendientes...")
        xml_rows = get_pending_xmls_from_db()

        if not xml_rows:
            logging.info("⏸️ No hay comprobantes por enviar. Esperando el siguiente ciclo.")
            continue

        logging.info(f"📚 {len(xml_rows)} comprobante(s) pendiente(s) encontrado(s). Procesando...")
        for row in xml_rows:
            ope_cod, eje_cod, mae_aso_cod, xml_str = row
            logging.info(f"📦 Procesando XML para OPECOD={ope_cod}, EJECOD={eje_cod}, MAE_ASOCOD={mae_aso_cod}")
            
            try:
                response = send_xml_to_soap(xml_str)
                if response and response.startswith("ERROR:"): # Asegurarse de que la respuesta no sea None
                    logging.warning(f"⚠️ El envío SOAP para OPECOD={ope_cod} falló, la respuesta es un mensaje de error. No se actualizará la tabla como exitoso.")
                else:
                    update_response_in_db(ope_cod, eje_cod, mae_aso_cod, response)
            except Exception as e:
                logging.error(f"❌ Fallo inesperado al procesar OPECOD={ope_cod}: {e}", exc_info=True)
                continue

        logging.info("✅ Lote de comprobantes procesado. Preparando para el siguiente ciclo.")

if __name__ == "__main__":
    logging.info("🚀 send_xml.py ejecutado directamente (no como servicio).")
    main()
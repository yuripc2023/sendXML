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

# Configuración del log: Usamos una ruta absoluta para el archivo de log.
# El nivel INFO es bueno para ver la actividad normal y los errores.
log_file_path = os.path.join(BASE_DIR, "envio_xml.log")
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
# --- FIN DE CAMBIOS PARA SOPORTE DE SERVICIO ---

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
    # Si estas variables son absolutamente críticas, puedes optar por salir aquí.
    # Por ejemplo: sys.exit(1) o raise ValueError("Variables de entorno incompletas")

# Obtener XML y datos clave de la BD
def get_pending_xmls_from_db():
    try:
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
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
        conn.close() # Importante cerrar la conexión
        return results
    except Exception as e:
        logging.error(f"❌ Error al obtener XMLs de la base de datos: {e}", exc_info=True) # exc_info=True para stack trace
        return []

# Enviar XML por SOAP
def send_xml_to_soap(xml_str):
    try:
        # Nota: La librería zeep no se está usando actualmente en send_xml_to_soap.
        # Si tienes una necesidad de WSDL complejo o manejo de schemas, zeep es más robusto.
        # Aquí estás usando requests directamente, lo cual es válido para un POST simple.

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": ""  # Coloca aquí el SOAPAction si tu endpoint lo requiere, ej. "http://tempuri.org/MyMethod"
        }

        # logging.info(f"Enviando a SOAP_WSDL: {SOAP_WSDL}") # Solo para depuración
        # logging.info(f"XML a enviar: {xml_str[:200]}...") # Loguea solo el inicio del XML

        response = requests.post(
            SOAP_WSDL,  # Aunque sea .wsdl, aquí es el endpoint real al que enviarás el XML
            data=xml_str.encode("utf-8"),
            headers=headers,
            auth=HTTPBasicAuth(SOAP_USER, SOAP_PASS) # Usar HTTPBasicAuth directamente es más limpio
        )

        response.raise_for_status()  # Lanza excepción si status != 200 (error HTTP)
        logging.info(f"✅ Respuesta recibida del SOAP (Estado: {response.status_code}): {response.text}")
        # print("📨 Respuesta del servidor:", response.text) # REMOVIDO: Los prints no funcionan en servicios
        return response.text

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Error al enviar XML vía SOAP: {e}", exc_info=True)
        return f"ERROR: {e}"
    except Exception as e:
        logging.error(f"❌ Error inesperado en send_xml_to_soap: {e}", exc_info=True)
        return f"ERROR_INESPERADO: {e}"

# Actualizar XMLResponse en la BD
def update_response_in_db(ope_cod, eje_cod, mae_aso_cod, response_text): # Cambié 'response' a 'response_text' para claridad
    try:
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USER};"
            f"PWD={SQL_PASSWORD}"
        )
        cursor = conn.cursor()
        # Asegúrate de que el campo XMLResponse en tu DB soporte el tamaño de la respuesta.
        # Usar NVARCHAR(MAX) o XML TYPE en SQL Server es recomendable.
        cursor.execute("""
            UPDATE MAEOPE
            SET XMLResponse = ?
            WHERE OPECOD = ? AND EJECOD = ? AND MAE_ASOCOD = ?
        """, (response_text, ope_cod, eje_cod, mae_aso_cod)) # Usar response_text
        conn.commit()
        conn.close() # Importante cerrar la conexión
        logging.info(f"✅ XMLResponse actualizado para OPECOD={ope_cod}, EJECOD={eje_cod}, MAE_ASOCOD={mae_aso_cod}.")
    except Exception as e:
        logging.error(f"❌ Error al actualizar XMLResponse para OPECOD={ope_cod}: {e}", exc_info=True)

# Validar conexión inicial a SQL
def test_conexion_sql():
    try:
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USER};"
            f"PWD={SQL_PASSWORD}"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT GETDATE()")
        result = cursor.fetchone()
        conn.close() # Importante cerrar la conexión
        # print("✅ Conexión exitosa. Fecha actual en SQL Server:", result[0]) # REMOVIDO
        logging.info(f"✅ Conexión SQL Server exitosa. Fecha actual: {result[0]}")
    except Exception as e:
        # print("❌ Error de conexión:", e) # REMOVIDO
        logging.error(f"❌ Error de conexión inicial a SQL Server: {e}", exc_info=True)

# Función principal
def main():
    # Es crucial que test_conexion_sql() y cualquier otra función al inicio
    # utilice logging en lugar de print, ya que el servicio no tendrá una consola.
    test_conexion_sql()
    
    logging.info("🟢 Servicio iniciando el bucle de búsqueda y envío de XMLs.")
    
    # Este bucle simula la ejecución continua del servicio.
    # Para detener el servicio, win32service detendrá este proceso.
    while True:
        logging.info("🔍 Buscando XMLs pendientes...")
        xml_rows = get_pending_xmls_from_db()

        if not xml_rows:
            logging.info("⏸️ No hay comprobantes por enviar. Esperando 10 segundos...")
            time.sleep(10)
            continue # Vuelve al inicio del bucle para la siguiente búsqueda

        logging.info(f"📚 {len(xml_rows)} comprobante(s) pendiente(s) encontrado(s). Procesando...")
        for row in xml_rows:
            ope_cod, eje_cod, mae_aso_cod, xml_str = row
            logging.info(f"📦 Procesando XML para OPECOD={ope_cod}, EJECOD={eje_cod}, MAE_ASOCOD={mae_aso_cod}")
            
            try:
                response = send_xml_to_soap(xml_str)
                # Aquí, debes decidir qué hacer si send_xml_to_soap devuelve un ERROR
                # Si devuelve "ERROR:...", no quieres guardarlo directamente como respuesta exitosa.
                if response.startswith("ERROR:"):
                    logging.warning(f"⚠️ El envío SOAP para OPECOD={ope_cod} falló, la respuesta es un mensaje de error. No se actualizará la tabla como exitoso.")
                    # O podrías guardar el error en una columna específica de errores si la tienes.
                    # Por ahora, si hay un error, no actualizamos XMLResponse, solo lo logueamos.
                    # Considera marcar el registro de otra forma si no se procesó correctamente.
                else:
                    update_response_in_db(ope_cod, eje_cod, mae_aso_cod, response)
            except Exception as e:
                # Este bloque capturará errores que ocurran *fuera* de send_xml_to_soap y update_response_in_db
                logging.error(f"❌ Fallo inesperado al procesar OPECOD={ope_cod}: {e}", exc_info=True)
                continue  # Sigue con el siguiente comprobante para no detener el servicio

        logging.info("✅ Lote de comprobantes procesado. Esperando 10 segundos antes del siguiente ciclo.")
        time.sleep(10)

# Ejecutar script directamente (para pruebas fuera del servicio)
if __name__ == "__main__":
    # Puedes ejecutar este script directamente desde la terminal para probar la lógica.
    # Los mensajes irán al archivo de log configurado.
    logging.info("🚀 send_xml.py ejecutado directamente (no como servicio).")
    main()
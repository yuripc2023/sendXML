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

# Cargar variables desde .env
load_dotenv()

# Leer variables del entorno
SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")
SQL_USER = os.getenv("SQL_USER")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")

SOAP_WSDL = os.getenv("SOAP_WSDL")
SOAP_USER = os.getenv("SOAP_USER")
SOAP_PASS = os.getenv("SOAP_PASS")

# Configuración del log
logging.basicConfig(
    filename="envio_xml.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

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
        return cursor.fetchall()
    except Exception as e:
        logging.error(f"❌ Error al obtener XMLs de la base de datos: {e}")
        return []

# Enviar XML por SOAP
def send_xml_to_soap(xml_str):
    try:
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": ""  # Coloca aquí el SOAPAction si tu endpoint lo requiere
        }

        response = requests.post(
            SOAP_WSDL,  # Aunque sea .wsdl, aquí es el endpoint real al que enviarás el XML
            data=xml_str.encode("utf-8"),
            headers=headers,
            auth=(SOAP_USER, SOAP_PASS)
        )

        response.raise_for_status()  # Lanza excepción si status != 200
        logging.info(f"✅ Respuesta recibida del SOAP: {response.text}")
        print("📨 Respuesta del servidor:", response.text)
        return response.text

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Error al enviar XML vía SOAP: {e}")
        return f"ERROR: {e}"

# Actualizar XMLResponse en la BD
def update_response_in_db(ope_cod, eje_cod, mae_aso_cod, response):
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
            UPDATE MAEOPE
            SET XMLResponse = ?
            WHERE OPECOD = ? AND EJECOD = ? AND MAE_ASOCOD = ?
        """, (response, ope_cod, eje_cod, mae_aso_cod))
        conn.commit()
        logging.info("✅ XMLResponse actualizado correctamente en la base de datos.")
    except Exception as e:
        logging.error(f"❌ Error al actualizar XMLResponse: {e}")

# Validar conexión inicial
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
        print("✅ Conexión exitosa. Fecha actual en SQL Server:", result[0])
    except Exception as e:
        print("❌ Error de conexión:", e)

# Función principal
def main():
    test_conexion_sql()
    
    while True:
        print("🔍 Buscando XMLs pendientes...")
        xml_rows = get_pending_xmls_from_db()

        if not xml_rows:
            print("⏸️ No hay comprobantes por enviar. Esperando 10 segundos...")
            time.sleep(10)
            continue

        for row in xml_rows:
            ope_cod, eje_cod, mae_aso_cod, xml_str = row
            print(f"📦 Enviando XML para OPECOD={ope_cod}, EJECOD={eje_cod}, MAE_ASOCOD={mae_aso_cod}")
            try:
                response = send_xml_to_soap(xml_str)
                update_response_in_db(ope_cod, eje_cod, mae_aso_cod, response)
            except Exception as e:
                logging.error(f"❌ Fallo al procesar OPECOD={ope_cod}: {e}")
                continue  # Sigue con el siguiente comprobante

        print("✅ Lote procesado. Esperando 10 segundos antes del siguiente...")
        time.sleep(10)

# Ejecutar script
if __name__ == "__main__":
    main()

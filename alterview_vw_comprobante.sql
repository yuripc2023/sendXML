USE database
GO

/****** Object:  View [dbo].[vw_comprobante]    Script Date: 20/07/2025 02:21:16 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


ALTER view [dbo].[vw_comprobante]
as

SELECT        tienda.ASODIR AS Direccion_empresa, tienda.asoobs AS Direccion_empresa2, tienda.asoimg as Direccion_empresa3,  tienda.ASONRZ AS Razon_Social, tienda.ASOAPE as NComercial, tienda.ASONDO AS RUC_Empresa, tienda.ASOCOD AS Tienda, Cliente.ASONRZ + ' ' + Cliente.ASOAPE AS Cliente, Cliente.ASONCO AS ClienteNComercial, 
                         Cliente.ASODIR
						 --  + ' | ' + dis.UBIDSC + ' - ' + prov.UBIDSC + ' - ' + dep.UBIDSC 
						 AS Direccion, Cliente.ASOCOD AS Codigo_cliente, Cliente.ASONDO AS RUC, Cliente.ASOTE1 AS Teléfono, Operacion.CTACOD AS Cuenta, 
                         Operacion.OPEEST AS Estado, Operacion.OPENDO AS n_Documento, Operacion.OPECOD AS Codigo, Cliente.ASOTDO AS Documento, Cliente.ASONDO AS N_, Operacion.EJECOD AS Ejercicio, Operacion.OPEFEM AS Fecha, 
                         Operacion.OPEFRE AS FechaRegistro, Operacion.OPEFCP AS FechPago, Operacion.OPEDPZ AS DiasPlazo, Operacion.OPESDO AS Serie, Operacion.DOCCOD AS Tipo, Detalle.PROCOD AS CodigoProducto, 
                         Detalle.DETLOT AS Lote, Detalle.DETFVE AS Vencimiento, Detalle.DETCAN AS Cantidad, Producto.PROMED AS Presentacion, 0.00 AS Dcto1, 0.00 AS Dcto2, 0.00 AS Dcto3, 
                         Detalle.DETPRF * Detalle.DETCAN AS Total, Detalle.DETPREC AS Precio, Detalle.DETPRF AS PrecioFinal, Detalle.DETDSC AS Producto, Operacion.OPEIBT AS ImporteBruto, Operacion.OPEDCT AS TotalDcto, Operacion.OPEVVE AS ValorVenta, Operacion.OPEFLE AS Flete, 
                         Operacion.OPEDCT as Descuento,
						 Operacion.OPEDEB - Operacion.OPEDCT AS SubTotal, Vendedor.ASOCOD AS Vendedor, Operacion.OPEIGV AS IGV, Operacion.OPEANU AS Anulado, tienda_producto.PROCOD AS cod_Producto, Detalle.DETFAC AS Factor, 
                         Cliente.ASOZON AS ZonaCliente, Vendedor.ASOZON AS ZonaVendedor, Operacion.ASOCAJ AS CodigoRegistra, tienda.ASOTE1 AS TelefonoEmpresa1, tienda.ASOMOV AS TelefonoEmpresa2, tienda.ASOCLA AS TelefonoEmpresa3, 
                         Operacion.OPELAN AS Numeros_Letras, Cliente.ASODIR AS direccion_c, dis.UBIDSC AS distrito, prov.UBIDSC AS provincia, dep.UBIDSC AS departamento, Detalle.BUSOPE, Detalle.BUSDET, 
                         Vendedor.ASONRZ + ' ' + Vendedor.ASOAPE AS NombreVendedor, Operacion.OPEOBS AS Observaciones, Cliente.UBICOD AS Ubigeo, Operacion.OPELAN AS NumerosEnletras, Operacion.OPENDG AS NumeroDeGuia, 
                         Operacion.OPENDP AS NumerodePedido, Operacion.OPEODC as OrdenDeCompra, 
						 Operacion.OPETIP AS ContadoCredito, Operacion.OPEMOT AS MotivoNC, Operacion.OPESDR as SerieDocRef, Operacion.OPENDR as NumDocRef, Operacion.opefedr as FechaDocuRef,
						 Operacion.opetddr as TipoDocReferencia, Operacion.opecdm as CodigoTipoNotadeCreditoDebito,
						 Documento.DOCDSC as Comprobante, Operacion.OPEEDD as EstadoCancelacion, Operacion.OPEFDC as FechaCancelación, Operacion.OPECOM as PorComision,
						 Detalle.DETPRF * Detalle.DETCAN AS Importe, Detalle.DETDSC AS DescripcionSerie, Detalle.DETCAN * (Detalle.DETPRF - Detalle.DETCOS) as Utilidad, '' as Mesa, '' as qr,
						 Operacion.OPEEFE as Efectivo, Operacion.OPECAJ as Cajero, Operacion.OPECICBP as CantidadICBPER, Operacion.OPEVICBP as ValorICBPER, Operacion.OPEMPA as MedioDePago,
						 Tienda.ubicod as ubigeoEmisor, disEmisor.UBIDSC as distritoEmisor, provEmisor.UBIDSC as provinciaEmisor, depEmisor.UBIDSC as departamentoEmisor,
						 Operacion.opefdpn as formaPagoNegociable, Operacion.opefpc as fechaPagoCuota, Operacion.OPEVRE as ValorReferencial, Operacion.OPEVNP as ValorNetoPagar,
						 Operacion.SignedStatus

FROM            MAEASO AS tienda INNER JOIN
                         MAEOPE AS Operacion ON tienda.ASOCOD = Operacion.MAE_ASOCOD INNER JOIN
                         MAEASO AS Cliente ON Operacion.OPEASO = Cliente.ASOCOD INNER JOIN
                         MAEASO AS Vendedor ON Vendedor.ASOCOD = Operacion.ASOCOD INNER JOIN
                         DETOPE AS Detalle ON Operacion.OPECOD = Detalle.OPECOD AND Operacion.EJECOD = Detalle.EJECOD AND Operacion.MAE_ASOCOD = Detalle.MAE_ASOCOD AND Operacion.DOCCOD = Detalle.DOCCOD AND 
                         Operacion.CTACOD = Detalle.CTACOD INNER JOIN
                         VINTXP AS tienda_producto ON tienda_producto.PROCOD = Detalle.PROCOD AND tienda_producto.ASOCOD = Detalle.ASOCOD INNER JOIN
                         MAEPRO AS Producto ON tienda_producto.PROCOD = Producto.PROCOD LEFT OUTER JOIN
                         MAEUBI AS dis ON Cliente.UBICOD = dis.UBICOD LEFT OUTER JOIN
                         MAEUBI AS prov ON dis.UBIDEP = prov.UBICOD LEFT OUTER JOIN
                         MAEUBI AS dep ON prov.UBIDEP = dep.UBICOD inner join
						 VINDXT on Operacion.DOCCOD = VINDXT.DOCCOD and Operacion.MAE_ASOCOD = VINDXT.ASOCOD inner join
						 MAEDOC as Documento on Documento.DOCCOD = VINDXT.DOCCOD
						 LEFT OUTER JOIN
                         MAEUBI AS disEmisor ON tienda.UBICOD = disEmisor.UBICOD LEFT OUTER JOIN
                         MAEUBI AS provEmisor ON disEmisor.UBIDEP = provEmisor.UBICOD LEFT OUTER JOIN
                         MAEUBI AS depEmisor ON provEmisor.UBIDEP = depEmisor.UBICOD

						 -- where Operacion.OPECOD = 4

						 --select CAJCOD from MAEOPE
















GO



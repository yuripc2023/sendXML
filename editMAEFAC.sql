use DbGrupoTerracafe
select DOCCOD, OPEFEM, OPEEST, XMLToSend from MAEFAC where DOCCOD <> 'NV' and year(OPEFEM) = 2025 and MONTH(opefem) = 9 and DAY(opefem) = 16

-- Limpiar XML generados
update MAEFAC set XMLToSend = null, XMLResponse = null, OPEEST  = '', SignedStatus = '' from MAEFAC 
where DOCCOD <> 'NV' and year(OPEFEM) = 2025 and MONTH(opefem) = 9 and DAY(opefem) = 19


order by XMLToSend

update MAEOPE set XMLResponse = null, OPEEST  = '', SignedStatus = '' where opecod = :g_st_parametros.codigo and ejecod = :g_st_parametros.ejercicio and MAE_ASOCOD = :g_st_parametros.tienda;


SELECT OPECOD, EJECOD, MAE_ASOCOD, XMLToSend, OPEFEM, XMLResponse
            FROM MAEFAC
WHERE XMLToSend IS NOT NULL AND XMLResponse IS NULL

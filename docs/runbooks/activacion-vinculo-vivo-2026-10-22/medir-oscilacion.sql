-- Solo lectura. Cambios de administrativeStatus en PROYECCIONES por dia/tarea/recurso (ultimos 4 dias).
-- Medido 19-22 oct: recon Trabajadores -> LDAP DIS ~1.484/dia; Egresados+Estudiantes+Koha -> LDAP ENA ~1.484/dia.
-- Esperado tras el paso 2: la fila Trabajadores/LDAP/DIS cae a ~0 (solo bajas reales del dia).
\pset pager off
\pset format unaligned
with ev as (select e.id, e.timestamp, e.targetoid, e.taskoid from ma_audit_event e where e.timestamp >= now()-interval '4 days' and e.eventstage='EXECUTION' and e.targettype='USER'),
d as (select ev.*, d.resourcenameorig r, case when convert_from(d.delta,'UTF8') ~ 'administrativeStatus","value":\[\{"@type":"c:ActivationStatusType","@value":"disabled"' then 'DIS' when convert_from(d.delta,'UTF8') ~ 'administrativeStatus","value":\[\{"@type":"c:ActivationStatusType","@value":"enabled"' then 'ENA' end v
      from ev join ma_audit_delta d on d.recordid=ev.id and d.timestamp=ev.timestamp and convert_from(d.delta,'UTF8') like '%administrativeStatus%')
select to_char(timestamp,'MM-DD') dia, coalesce((select nameorig from m_task t where t.oid=d.taskoid),'-') task, coalesce(r,'(foco)') r, v, count(distinct targetoid) from d where v is not null group by 1,2,3,4 order by 1,2,3,4;

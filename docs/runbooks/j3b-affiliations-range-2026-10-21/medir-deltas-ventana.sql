-- Solo lectura. Deltas ejecutados por recurso desde :'desde' (timestamptz). Esperado: solo LDAP default
-- (eduPersonAffiliation/ScopedAffiliation) y foco; Koha/Entra/Zammad = 0 salvo ruido conocido.
select coalesce(d.resourcenameorig,'(foco)') recurso, d.shadowintent, d.deltatype, d.status, count(*)
from ma_audit_delta d join ma_audit_event e on e.id=d.recordid and e.timestamp=d.timestamp
where d.timestamp >= :'desde' and e.eventstage='EXECUTION'
group by 1,2,3,4 order by 5 desc;

-- Solo lectura. Correr con PGOPTIONS='-c default_transaction_read_only=on'.
-- affiliations (ext 100) actual vs lo que J3b debe producir desde 216/217/215. Medido 21-oct: 7.678 differ, 0 gain.
with x as (
  select u.oid, u.lifecyclestate::text ls,
    coalesce((select array_agg(distinct v order by v) from jsonb_array_elements_text(u.ext->'100') v), '{}') cur,
    coalesce((select array_agg(distinct v order by v) from unnest(array[lower(trim(u.ext->>'216')), lower(trim(u.ext->>'217')), lower(trim(u.ext->>'215'))]) v
              where v in ('faculty','staff','student','alum','affiliate')), '{}') exp
  from m_user u)
select case when grouping(ls)=1 then 'TOTAL' else coalesce(ls,'(null)') end ls, count(*) filter (where cur<>exp) differ, count(*) filter (where not cur @> exp) gain_some,
       count(*) filter (where cur<>'{}' and exp='{}') lose_all, count(*) total
from x group by rollup(ls) order by 1;

-- Solo lectura. v2: foto por usuario de lo que tocan R/ACT/L para comparar antes/despues del encendido
-- acotado. uso: psql ... -f snapshot-estado.sql > snap-<momento>.tsv ; diff snap-pre.tsv snap-post.tsv
-- Fuera del canario SOLO pueden aparecer cambios explicables por las IIA (altas/bajas del dia); el
-- encendido acotado no puede producir ninguno: el filtro esta en el rango (CANARIO).
\pset pager off
\pset format unaligned
\pset tuples_only on
\pset fieldsep '\t'
select u.oid, u.nameorig, coalesce(u.lifecyclestate,'-'), coalesce(u.administrativestatus::text,'-'),
       coalesce(u.effectivestatus::text,'-'), coalesce(u.ext->>'216','-'), coalesce(u.ext->>'217','-'), coalesce(u.ext->>'215','-')
from m_user u order by u.oid;

-- Solo lectura (PGOPTIONS default_transaction_read_only=on). Foto por usuario: lifecycle/admin/effective,
-- items vivos 216/217/215, terminationDate (99), cuentas Oracle vivas/muertas con ESTADO/FEC_TERMINO,
-- DATE_EXPIRY, AFILIACION, LDAP/Koha/Zammad (estado cacheado), evidencia laboral, arquetipos. ~9 s en PROD.
\pset pager off
\pset format unaligned
\pset footer off
\pset fieldsep '\t'
with lk as materialized (
 select p.owneroid o, s.resourcereftargetoid r, s.intent, coalesce(s.dead,false) dead,
   s.attributes a, convert_from(s.fullobject,'UTF8')::jsonb->'shadow'->'activation'->>'administrativeStatus' sadm
 from m_ref_projection p join m_shadow s on s.oid=p.targetoid
 where s.resourcereftargetoid in ('6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21','6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22','6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e23','7b4e1c2d-3f8a-4d6b-9e5c-0a1b2c3d4e5f','e10a539a-cb7f-4c72-a19f-60f7f62e4b96','7a11d0d0-0000-4000-a000-7a11d0d00001')),
ag as (select o,
 count(*) filter (where r='6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21' and not dead) w_live,
 count(*) filter (where r='6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21' and dead) w_dead,
 string_agg(coalesce(a->>'29','')||'/'||coalesce(a->>'35','')||'/'||coalesce(a->>'32',''),'|') filter (where r='6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21' and not dead) w_attr,
 count(*) filter (where r='6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22' and not dead) s_live,
 count(*) filter (where r='6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22' and dead) s_dead,
 string_agg(coalesce(a->>'158',''),'|') filter (where r='6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22' and not dead) s_attr,
 count(*) filter (where r='6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e23' and not dead) a_live,
 string_agg(coalesce(a->>'77',''),'|') filter (where r='6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e23' and not dead) a_attr,
 string_agg(intent||':'||coalesce(sadm,'-')||(case when dead then ':dead' else '' end),'|') filter (where r='7b4e1c2d-3f8a-4d6b-9e5c-0a1b2c3d4e5f') ldap,
 string_agg(coalesce(sadm,'-')||(case when dead then ':dead' else '' end),'|') filter (where r='e10a539a-cb7f-4c72-a19f-60f7f62e4b96') koha,
 string_agg(coalesce(sadm,'-')||(case when dead then ':dead' else '' end),'|') filter (where r='7a11d0d0-0000-4000-a000-7a11d0d00001') zam
 from lk group by o),
emp as (select distinct a.owneroid o from m_assignment a where a.targetreftargetoid in ('6460facf-3abf-4851-966e-0c95aa1a6c46','c93083ca-f4c5-4704-acf4-d53b97c9556e')),
arc as (select r.owneroid o, string_agg(a.nameorig,',') n from m_ref_archetype r join m_archetype a on a.oid=r.targetoid group by 1)
select u.oid, u.nameorig, coalesce(u.lifecyclestate::text,''), coalesce(u.administrativestatus::text,''), coalesce(u.effectivestatus::text,''),
 coalesce(u.ext->>'216',''), coalesce(u.ext->>'217',''), coalesce(u.ext->>'215',''), coalesce(u.ext->>'99',''), coalesce(u.ext->>'218',''), coalesce(u.ext->>'171',''), coalesce(u.ext->>'179',''),
 coalesce(ag.w_live,0), coalesce(ag.w_dead,0), coalesce(ag.w_attr,''), coalesce(ag.s_live,0), coalesce(ag.s_dead,0), coalesce(ag.s_attr,''), coalesce(ag.a_live,0), coalesce(ag.a_attr,''),
 coalesce(ag.ldap,''), coalesce(ag.koha,''), coalesce(ag.zam,''), (emp.o is not null)::int, coalesce(arc.n,''), coalesce(u.ext->>'78',''), coalesce(u.ext->>'100','')
from m_user u left join ag on ag.o=u.oid left join emp on emp.o=u.oid left join arc on arc.o=u.oid;

-- Solo lectura. Residuo del diseno activacion-vinculo-vivo. Medido 22-oct ANTES: ver README §3.
\pset pager off
\pset format unaligned
with lk as materialized (select p.owneroid o, s.resourcereftargetoid r from m_ref_projection p join m_shadow s on s.oid=p.targetoid
   where coalesce(s.dead,false)=false and s.resourcereftargetoid in ('6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21','6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22','6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e23'))
select 'R1 217 sin cuenta e22 viva' m, count(*) from m_user u where u.ext ? '217' and not exists (select 1 from lk where lk.o=u.oid and lk.r='6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e22')
union all select 'R2 215 sin cuenta e23 viva', count(*) from m_user u where u.ext ? '215' and not exists (select 1 from lk where lk.o=u.oid and lk.r='6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e23')
union all select 'R3 216 sin cuenta e21 viva', count(*) from m_user u where u.ext ? '216' and not exists (select 1 from lk where lk.o=u.oid and lk.r='6a91f7e1-1b50-4dcf-9c4b-7c0c0e0e0e21')
union all select 'ACT active+DISABLED con item vivo', count(*) from m_user u where u.lifecyclestate='active' and u.administrativestatus='DISABLED' and (u.ext ? '216' or u.ext ? '217' or u.ext ? '215')
union all select 'L active sin item vivo', count(*) from m_user u where u.lifecyclestate='active' and not (u.ext ? '216' or u.ext ? '217' or u.ext ? '215');
-- Esperado tras el despliegue: R1 <= 1 (Hulda hasta la fusion), R2 0, R3 0 (201811693 lo aplica la recon de Egresados),
-- ACT 0, L active sin item vivo = 3 (administrator no cuenta: lifecycle null; svc-ai-identity, 202512729 congelado).
select lifecyclestate, administrativestatus, effectivestatus, count(*) from m_user group by 1,2,3 order by 1,2,3;

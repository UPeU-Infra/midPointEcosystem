-- Solo lectura. Lee un SimulationResult: uso psql -v sim="'<oid del SimulationResult>'" -f medir-sim.sql
-- (m_simulation_result_processed_object se une por owneroid; fullobject es JSON en claro; NO hacer JOIN con m_shadow
--  para contar ADDED: los ADDED no existen en m_shadow y el join los descarta en silencio).
\pset pager off
\pset format unaligned
select objecttype, state, count(*) from m_simulation_result_processed_object where owneroid=:sim group by 1,2 order by 1,2;
select p.objecttype, p.state, p.nameorig,
  substring(convert_from(p.fullobject,'UTF8') from '"resourceRef":\{"oid":"([0-9a-f-]{36})') res,
  (convert_from(p.fullobject,'UTF8') ~ 'lifecycleState') lc, (convert_from(p.fullobject,'UTF8') ~ 'administrativeStatus') adm,
  (convert_from(p.fullobject,'UTF8') ~ 'liveAffiliationStudent') s217, (convert_from(p.fullobject,'UTF8') ~ 'liveAffiliationAlum') a215,
  (convert_from(p.fullobject,'UTF8') ~ 'liveAffiliationWorker') w216, (convert_from(p.fullobject,'UTF8') ~ 'archetypeRef') arch
from m_simulation_result_processed_object p where p.owneroid=:sim and p.state<>'UNMODIFIED' order by 1,3;

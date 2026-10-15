#!/bin/bash
# uso: verif_ventana.sh "<desde ISO con offset, p.ej. 2026-10-15 11:05:00-05>"
D="$1"
cat <<SQL | ./psql.sh
SELECT 'audit-deltas-Entra' k, d.objectnameorig, d.status, d.deltatype, count(*) FROM ma_audit_delta d WHERE d.timestamp >= '$D' AND d.resourceoid='2f11c057-7b15-4641-a0eb-00c98a6fa4cb' GROUP BY 2,3,4 ORDER BY 2;
SELECT 'eventos-Entra' k, e.eventtype, e.eventstage, e.targetname, e.outcome, count(*) FROM ma_audit_event e WHERE e.timestamp >= '$D' AND e.resourceoids @> ARRAY['2f11c057-7b15-4641-a0eb-00c98a6fa4cb'] GROUP BY 2,3,4,5 ORDER BY 4;
SELECT 'pendientes-Entra' k, count(*) FROM m_shadow WHERE resourcereftargetoid='2f11c057-7b15-4641-a0eb-00c98a6fa4cb' AND pendingoperationcount>0;
SELECT 'tareas-running' k, nameorig FROM m_task WHERE executionstate::text='RUNNING';
SQL

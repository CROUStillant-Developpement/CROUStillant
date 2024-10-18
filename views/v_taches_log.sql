CREATE OR REPLACE VIEW {SCHEMA}.TACHES_LOGS AS (
    SELECT
        RID,
        IDTACHE
    FROM PUBLIC.TACHE_LOG
    LEFT JOIN PUBLIC.EMPTY ON 1 = 1
);

-- ***************************************************************/
COMMENT ON VIEW {SCHEMA}.TACHES_LOGS IS 'Liste des tâches log';
-- ***************************************************************/
COMMENT ON COLUMN {SCHEMA}.TACHES_LOGS.RID IS 'Identifiant du restaurant concerné';
COMMENT ON COLUMN {SCHEMA}.TACHES_LOGS.IDTACHE IS 'Identifiant de la tâche';
-- ***************************************************************/
GRANT SELECT ON {SCHEMA}.TACHES_LOGS TO {USER};
REVOKE INSERT, UPDATE, DELETE ON {SCHEMA}.TACHES_LOGS FROM {USER};
-- ***************************************************************/

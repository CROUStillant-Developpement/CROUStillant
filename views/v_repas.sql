CREATE OR REPLACE VIEW {SCHEMA}.REPAS AS (
    SELECT
        TPR,
        MID,
        RPID
    FROM PUBLIC.REPAS R
    LEFT JOIN PUBLIC.EMPTY ON 1 = 1
);

-- ***************************************************************/
COMMENT ON VIEW {SCHEMA}.REPAS IS 'Liste des repas';
-- ***************************************************************/
COMMENT ON COLUMN {SCHEMA}.REPAS.TPR IS 'Type de repas';
COMMENT ON COLUMN {SCHEMA}.REPAS.MID IS 'Identifiant du menu';
COMMENT ON COLUMN {SCHEMA}.REPAS.RPID IS 'Identifiant du repas';
-- ***************************************************************/
GRANT SELECT ON {SCHEMA}.REPAS TO {USER};
REVOKE INSERT, UPDATE, DELETE ON {SCHEMA}.REPAS FROM {USER};
-- ***************************************************************/

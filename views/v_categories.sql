CREATE OR REPLACE VIEW {SCHEMA}.CATEGORIES AS (
    SELECT
        CATID,
        TPCAT,
        ORDRE,
        RPID
    FROM PUBLIC.CATEGORIE
    LEFT JOIN PUBLIC.EMPTY ON 1 = 1
);

-- ***************************************************************/
COMMENT ON VIEW {SCHEMA}.CATEGORIES IS 'Liste des catégories';
-- ***************************************************************/
COMMENT ON COLUMN {SCHEMA}.CATEGORIES.CATID IS 'Identifiant de la catégorie';
COMMENT ON COLUMN {SCHEMA}.CATEGORIES.TPCAT IS 'Type de catégorie';
COMMENT ON COLUMN {SCHEMA}.CATEGORIES.ORDRE IS 'Ordre de la catégorie';
COMMENT ON COLUMN {SCHEMA}.CATEGORIES.RPID IS 'Identifiant du repas';
-- ***************************************************************/
GRANT SELECT ON {SCHEMA}.CATEGORIES TO {USER};
REVOKE INSERT, UPDATE, DELETE ON {SCHEMA}.CATEGORIES FROM {USER};
-- ***************************************************************/

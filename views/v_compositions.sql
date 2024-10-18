CREATE OR REPLACE VIEW {SCHEMA}.COMPOSITIONS AS (
    SELECT
        CATID,
        ORDRE,
        PLATID
    FROM PUBLIC.COMPOSITION
    LEFT JOIN PUBLIC.EMPTY ON 1 = 1
);

-- ***************************************************************/
COMMENT ON VIEW {SCHEMA}.COMPOSITIONS IS 'Liste des compositions';
-- ***************************************************************/
COMMENT ON COLUMN {SCHEMA}.COMPOSITIONS.CATID IS 'Identifiant de la catégorie';
COMMENT ON COLUMN {SCHEMA}.COMPOSITIONS.ORDRE IS 'Ordre de la composition';
COMMENT ON COLUMN {SCHEMA}.COMPOSITIONS.PLATID IS 'Identifiant du plat';
-- ***************************************************************/
GRANT SELECT ON {SCHEMA}.COMPOSITIONS TO {USER};
REVOKE INSERT, UPDATE, DELETE ON {SCHEMA}.COMPOSITIONS FROM {USER};
-- ***************************************************************/

CREATE OR REPLACE VIEW {SCHEMA}.REGIONS AS (
    SELECT
        IDREG,
        LIBELLE
    FROM PUBLIC.REGION
    LEFT JOIN PUBLIC.EMPTY E ON 1 = 1
);

-- ***************************************************************/
COMMENT ON VIEW {SCHEMA}.REGIONS IS 'Liste des régions';
-- ***************************************************************/
COMMENT ON COLUMN {SCHEMA}.REGIONS.IDREG IS 'Identifiant de la région';
COMMENT ON COLUMN {SCHEMA}.REGIONS.LIBELLE IS 'Libellé de la région';
-- ***************************************************************/
GRANT SELECT ON {SCHEMA}.REGIONS TO {USER};
REVOKE INSERT, UPDATE, DELETE ON {SCHEMA}.REGIONS FROM {USER};
-- ***************************************************************/

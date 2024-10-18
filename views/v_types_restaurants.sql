CREATE OR REPLACE VIEW {SCHEMA}.TYPES_RESTAURANTS AS (
    SELECT
        IDTPR,
        LIBELLE
    FROM PUBLIC.TYPE_RESTAURANT
    LEFT JOIN PUBLIC.EMPTY E ON 1 = 1
);

-- ***************************************************************/
COMMENT ON VIEW {SCHEMA}.TYPES_RESTAURANTS IS 'Liste des types de restaurant';
-- ***************************************************************/
COMMENT ON COLUMN {SCHEMA}.TYPES_RESTAURANTS.IDTPR IS 'Identifiant du type de restaurant';
COMMENT ON COLUMN {SCHEMA}.TYPES_RESTAURANTS.LIBELLE IS 'Libellé du type de restaurant';
-- ***************************************************************/
GRANT SELECT ON {SCHEMA}.TYPES_RESTAURANTS TO {USER};
REVOKE INSERT, UPDATE, DELETE ON {SCHEMA}.TYPES_RESTAURANTS FROM {USER};
-- ***************************************************************/

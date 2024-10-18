CREATE OR REPLACE VIEW {SCHEMA}.PLATS AS (
    SELECT
        PLATID,
        LIBELLE
    FROM PUBLIC.PLAT
    LEFT JOIN PUBLIC.EMPTY ON 1 = 1
);

-- ***************************************************************/
COMMENT ON VIEW {SCHEMA}.PLATS IS 'Liste des plats';
-- ***************************************************************/
COMMENT ON COLUMN {SCHEMA}.PLATS.PLATID IS 'Identifiant du plat';
COMMENT ON COLUMN {SCHEMA}.PLATS.LIBELLE IS 'Libellé du plat';
-- ***************************************************************/
GRANT SELECT ON {SCHEMA}.PLATS TO {USER};
REVOKE INSERT, UPDATE, DELETE ON {SCHEMA}.PLATS FROM {USER};
-- ***************************************************************/

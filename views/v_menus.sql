CREATE OR REPLACE VIEW {SCHEMA}.MENUS AS (
    SELECT
        MID,
        DATE,
        RID
    FROM PUBLIC.MENU
    LEFT JOIN PUBLIC.EMPTY ON 1 = 1
);

-- ***************************************************************/
COMMENT ON VIEW {SCHEMA}.MENUS IS 'Liste des menus';
-- ***************************************************************/
COMMENT ON COLUMN {SCHEMA}.MENUS.MID IS 'Identifiant du menu';
COMMENT ON COLUMN {SCHEMA}.MENUS.DATE IS 'Date du menu';
COMMENT ON COLUMN {SCHEMA}.MENUS.RID IS 'Identifiant du restaurant';
-- ***************************************************************/
GRANT SELECT ON {SCHEMA}.MENUS TO {USER};
REVOKE INSERT, UPDATE, DELETE ON {SCHEMA}.MENUS FROM {USER};
-- ***************************************************************/

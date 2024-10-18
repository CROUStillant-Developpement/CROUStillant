CREATE OR REPLACE VIEW {SCHEMA}.STATS AS (
    SELECT
        (SELECT COUNT(*) FROM PUBLIC.REGION) AS regions,
        (SELECT COUNT(*) FROM PUBLIC.RESTAURANT) AS restaurants,
        (SELECT COUNT(*) FROM PUBLIC.TYPE_RESTAURANT) AS types_restaurants,
        (SELECT COUNT(*) FROM PUBLIC.MENU) AS menus,
        (SELECT COUNT(*) FROM PUBLIC.REPAS) AS repas,
        (SELECT COUNT(*) FROM PUBLIC.CATEGORIE) AS categories,
        (SELECT COUNT(*) FROM PUBLIC.PLAT) AS plats,
        (SELECT COUNT(*) FROM PUBLIC.COMPOSITION) AS compositions
);

-- ***************************************************************/
COMMENT ON VIEW {SCHEMA}.STATS IS 'Statistiques sur les données';
-- ***************************************************************/
COMMENT ON COLUMN {SCHEMA}.STATS.regions IS 'Nombre de régions';
COMMENT ON COLUMN {SCHEMA}.STATS.restaurants IS 'Nombre de restaurants';
COMMENT ON COLUMN {SCHEMA}.STATS.types_restaurants IS 'Nombre de types de restaurants';
COMMENT ON COLUMN {SCHEMA}.STATS.menus IS 'Nombre de menus';
COMMENT ON COLUMN {SCHEMA}.STATS.repas IS 'Nombre de repas';
COMMENT ON COLUMN {SCHEMA}.STATS.categories IS 'Nombre de catégories';
COMMENT ON COLUMN {SCHEMA}.STATS.plats IS 'Nombre de plats';
COMMENT ON COLUMN {SCHEMA}.STATS.compositions IS 'Nombre de compositions';
-- ***************************************************************/
GRANT SELECT ON {SCHEMA}.STATS TO {USER};
REVOKE INSERT, UPDATE, DELETE ON {SCHEMA}.STATS FROM {USER};
-- ***************************************************************/

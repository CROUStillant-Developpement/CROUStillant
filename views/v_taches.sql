CREATE OR REPLACE VIEW {SCHEMA}.TACHES AS (
    SELECT
        ID,
        DEBUT,
        DEBUT_REGIONS,
        DEBUT_RESTAURANTS,
        DEBUT_TYPES_RESTAURANTS,
        DEBUT_MENUS,
        DEBUT_REPAS,
        DEBUT_CATEGORIES,
        DEBUT_PLATS,
        DEBUT_COMPOSITIONS,
        FIN,
        FIN_REGIONS,
        FIN_RESTAURANTS,
        FIN_TYPES_RESTAURANTS,
        FIN_MENUS,
        FIN_REPAS,
        FIN_CATEGORIES,
        FIN_PLATS,
        FIN_COMPOSITIONS,
        REQUETES
    FROM PUBLIC.TACHE
    LEFT JOIN PUBLIC.EMPTY ON 1 = 1
);

-- ***************************************************************/
COMMENT ON VIEW {SCHEMA}.TACHES IS 'Liste des tâches';
-- ***************************************************************/
COMMENT ON COLUMN {SCHEMA}.TACHES.ID IS 'Identifiant de la tâche';
COMMENT ON COLUMN {SCHEMA}.TACHES.DEBUT IS 'Date de début';
COMMENT ON COLUMN {SCHEMA}.TACHES.DEBUT_REGIONS IS 'Nombre de régions au début';
COMMENT ON COLUMN {SCHEMA}.TACHES.DEBUT_RESTAURANTS IS 'Nombre de restaurants au début';
COMMENT ON COLUMN {SCHEMA}.TACHES.DEBUT_TYPES_RESTAURANTS IS 'Nombre de types de restaurants au début';
COMMENT ON COLUMN {SCHEMA}.TACHES.DEBUT_MENUS IS 'Nombre de menus au début';
COMMENT ON COLUMN {SCHEMA}.TACHES.DEBUT_REPAS IS 'Nombre de repas au début';
COMMENT ON COLUMN {SCHEMA}.TACHES.DEBUT_CATEGORIES IS 'Nombre de catégories au début';
COMMENT ON COLUMN {SCHEMA}.TACHES.DEBUT_PLATS IS 'Nombre de plats au début';
COMMENT ON COLUMN {SCHEMA}.TACHES.DEBUT_COMPOSITIONS IS 'Nombre de compositions au début';
COMMENT ON COLUMN {SCHEMA}.TACHES.FIN IS 'Date de fin';
COMMENT ON COLUMN {SCHEMA}.TACHES.FIN_REGIONS IS 'Nombre de régions à la fin';
COMMENT ON COLUMN {SCHEMA}.TACHES.FIN_RESTAURANTS IS 'Nombre de restaurants à la fin';
COMMENT ON COLUMN {SCHEMA}.TACHES.FIN_TYPES_RESTAURANTS IS 'Nombre de types de restaurants à la fin';
COMMENT ON COLUMN {SCHEMA}.TACHES.FIN_MENUS IS 'Nombre de menus à la fin';
COMMENT ON COLUMN {SCHEMA}.TACHES.FIN_REPAS IS 'Nombre de repas à la fin';
COMMENT ON COLUMN {SCHEMA}.TACHES.FIN_CATEGORIES IS 'Nombre de catégories à la fin';
COMMENT ON COLUMN {SCHEMA}.TACHES.FIN_PLATS IS 'Nombre de plats à la fin';
COMMENT ON COLUMN {SCHEMA}.TACHES.FIN_COMPOSITIONS IS 'Nombre de compositions à la fin';
COMMENT ON COLUMN {SCHEMA}.TACHES.REQUETES IS 'Nombre de requêtes effectuées';
-- ***************************************************************/
GRANT SELECT ON {SCHEMA}.TACHES TO {USER};
REVOKE INSERT, UPDATE, DELETE ON {SCHEMA}.TACHES FROM {USER};
-- ***************************************************************/

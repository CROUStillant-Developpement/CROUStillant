CREATE OR REPLACE VIEW {SCHEMA}.RESTAURANTS AS (
    SELECT
        RID,
        NOM,
        ADRESSE,
        LATITUDE,
        LONGITUDE,
        HORAIRES,
        JOURS_OUVERT,
        IMAGE_URL,
        EMAIL,
        TELEPHONE,
        ISPMR,
        ZONE,
        PAIEMENT,
        ACCES
    FROM PUBLIC.RESTAURANT
);

-- ***************************************************************/
COMMENT ON VIEW {SCHEMA}.RESTAURANTS IS 'Liste des restaurants';
-- ***************************************************************/
COMMENT ON COLUMN {SCHEMA}.RESTAURANTS.RID IS 'Identifiant du restaurant';
COMMENT ON COLUMN {SCHEMA}.RESTAURANTS.NOM IS 'Nom du restaurant';
COMMENT ON COLUMN {SCHEMA}.RESTAURANTS.ADRESSE IS 'Adresse du restaurant';
COMMENT ON COLUMN {SCHEMA}.RESTAURANTS.LATITUDE IS 'Latitude du restaurant';
COMMENT ON COLUMN {SCHEMA}.RESTAURANTS.LONGITUDE IS 'Longitude du restaurant';
COMMENT ON COLUMN {SCHEMA}.RESTAURANTS.HORAIRES IS 'Horaires du restaurant';
COMMENT ON COLUMN {SCHEMA}.RESTAURANTS.JOURS_OUVERT IS 'Jours d''ouverture du restaurant';
COMMENT ON COLUMN {SCHEMA}.RESTAURANTS.IMAGE_URL IS 'URL de l''image du restaurant';
COMMENT ON COLUMN {SCHEMA}.RESTAURANTS.EMAIL IS 'Email du restaurant';
COMMENT ON COLUMN {SCHEMA}.RESTAURANTS.TELEPHONE IS 'Téléphone du restaurant';
COMMENT ON COLUMN {SCHEMA}.RESTAURANTS.ISPMR IS 'Restaurant PMR';
COMMENT ON COLUMN {SCHEMA}.RESTAURANTS.ZONE IS 'Zone du restaurant';
COMMENT ON COLUMN {SCHEMA}.RESTAURANTS.PAIEMENT IS 'Moyens de paiement du restaurant';
COMMENT ON COLUMN {SCHEMA}.RESTAURANTS.ACCES IS 'Accès du restaurant';
-- ***************************************************************/
GRANT SELECT ON {SCHEMA}.RESTAURANTS TO {USER};
REVOKE INSERT, UPDATE, DELETE ON {SCHEMA}.RESTAURANTS FROM {USER};
-- ***************************************************************/

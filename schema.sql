/***************************************************************
    *  CROUStillant - schema.sql
    *  Created by: CROUStillant Développement
    *  Created on: 13/11/2023
    *  Updated on: 18/10/2024
    *  Description: SQL database scheme for the CROUStillant project
***************************************************************/

-- Région
CREATE TABLE REGION(
    IDREG INT PRIMARY KEY,
    LIBELLE VARCHAR(255)
);


-- Type de restaurant
CREATE TABLE TYPE_RESTAURANT(
    IDTPR SERIAL PRIMARY KEY,
    LIBELLE VARCHAR(255)
);


-- Restaurant
CREATE TABLE RESTAURANT(
    RID INT PRIMARY KEY,
    IDREG INT,
    IDTPR INT,
    NOM VARCHAR(255),
    ADRESSE VARCHAR(255),
    LATITUDE FLOAT,
    LONGITUDE FLOAT,
    HORAIRES VARCHAR(1000),
    JOURS_OUVERT CHAR(27),
    IMAGE_URL VARCHAR(255),
    EMAIL VARCHAR(255),
    TELEPHONE VARCHAR(14),
    ISPMR BOOLEAN,
    ZONE VARCHAR(255),
    PAIEMENT VARCHAR(1000),
    ACCES VARCHAR(500),
    OPENED BOOLEAN,
    CONSTRAINT FK_RESTAURANT_REGION FOREIGN KEY (IDREG) REFERENCES REGION(IDREG),
    CONSTRAINT FK_RESTAURANT_TYPE_RESTAURANT FOREIGN KEY (IDTPR) REFERENCES TYPE_RESTAURANT(IDTPR)
);


-- Paramètres (pour le BOT Discord)
CREATE TABLE PARAMETRES(
    GUILD_ID BIGINT,
    CHANNEL_ID BIGINT,
    MESSAGE_ID BIGINT,
    RID INT,
    THEME VARCHAR(100),
    CONSTRAINT PK_PARAMETRES PRIMARY KEY (GUILD_ID, RID),
    CONSTRAINT FK_PARAMETRES_RESTAURANT FOREIGN KEY (RID) REFERENCES RESTAURANT(RID),
    CONSTRAINT CK_PARAMETRES_THEME CHECK (THEME IN ('light', 'dark'))
);


-- Menu
CREATE TABLE MENU
(
    MID  INT PRIMARY KEY,
    DATE DATE,
    RID  INT,
    CONSTRAINT FK_MENU_RESTAURANT FOREIGN KEY (RID) REFERENCES RESTAURANT (RID)
) PARTITION BY HASH(MID);

CREATE INDEX menu_date ON MENU USING BTREE(DATE);

-- Création des partitions pour la table MENU
DO
$$
BEGIN
    FOR i IN 0..29 LOOP
        EXECUTE format('CREATE TABLE menu_partition_%s PARTITION OF MENU FOR VALUES WITH (modulus 30, remainder %s)', i, i);
    END LOOP;
END;
$$;


-- Repas
CREATE TABLE REPAS(
    RPID SERIAL PRIMARY KEY,
    TPR VARCHAR(10),
    MID INT,
    CONSTRAINT FK_REPAS_MENU FOREIGN KEY (MID) REFERENCES MENU(MID),
    CONSTRAINT CK_REPAS_TPR CHECK (TPR IN ('matin', 'midi', 'soir'))
) PARTITION BY HASH(RPID);

-- Création des partitions pour la table REPAS
DO
$$
BEGIN
    FOR i IN 0..29 LOOP
        EXECUTE format('CREATE TABLE repas_partition_%s PARTITION OF REPAS FOR VALUES WITH (modulus 30, remainder %s)', i, i);
    END LOOP;
END;
$$;


-- Catégorie
CREATE TABLE CATEGORIE(
    CATID SERIAL PRIMARY KEY,
    TPCAT VARCHAR(500),
    ORDRE INT,
    RPID INT,
    CONSTRAINT FK_CATEGORIE_REPAS FOREIGN KEY (RPID) REFERENCES REPAS(RPID)
) PARTITION BY HASH(CATID);

-- Création des partitions pour la table CATEGORIE
DO
$$
BEGIN
    FOR i IN 0..29 LOOP
        EXECUTE format('CREATE TABLE categorie_partition_%s PARTITION OF CATEGORIE FOR VALUES WITH (modulus 30, remainder %s)', i, i);
    END LOOP;
END;
$$;


-- Plat
CREATE TABLE PLAT(
    PLATID SERIAL PRIMARY KEY,
    LIBELLE VARCHAR(500)
) PARTITION BY HASH(PLATID);

-- Création des partitions pour la table PLAT
DO
$$
BEGIN
    FOR i IN 0..29 LOOP
        EXECUTE format('CREATE TABLE plat_partition_%s PARTITION OF PLAT FOR VALUES WITH (modulus 30, remainder %s)', i, i);
    END LOOP;
END;
$$;


-- Composition
CREATE TABLE COMPOSITION(
    CATID INT,
    ORDRE INT,
    PLATID INT,
    CONSTRAINT PK_COMPOSITION PRIMARY KEY (CATID, PLATID),
    CONSTRAINT FK_COMPOSITION_CATEGORIE FOREIGN KEY (CATID) REFERENCES CATEGORIE(CATID),
    CONSTRAINT FK_COMPOSITION_PLAT FOREIGN KEY (PLATID) REFERENCES PLAT(PLATID)
) PARTITION BY HASH(CATID, PLATID);

-- Création des partitions pour la table COMPOSITION
DO
$$
BEGIN
    FOR i IN 0..29 LOOP
        EXECUTE format('CREATE TABLE composition_partition_%s PARTITION OF COMPOSITION FOR VALUES WITH (modulus 30, remainder %s)', i, i);
    END LOOP;
END;
$$;


-- Tâche
CREATE TABLE TACHE(
    ID SERIAL PRIMARY KEY,
    DEBUT TIMESTAMP,
    DEBUT_REGIONS INT,
    DEBUT_RESTAURANTS INT,
    DEBUT_TYPES_RESTAURANTS INT,
    DEBUT_MENUS INT,
    DEBUT_REPAS INT,
    DEBUT_CATEGORIES INT,
    DEBUT_PLATS INT,
    DEBUT_COMPOSITIONS INT,
    FIN TIMESTAMP,
    FIN_REGIONS INT,
    FIN_RESTAURANTS INT,
    FIN_TYPES_RESTAURANTS INT,
    FIN_MENUS INT,
    FIN_REPAS INT,
    FIN_CATEGORIES INT,
    FIN_PLATS INT,
    FIN_COMPOSITIONS INT,
    REQUETES INT,
    CONSTRAINT CK_STATISTIQUES CHECK (
        DEBUT_REGIONS <= FIN_REGIONS AND 
        DEBUT_RESTAURANTS <= FIN_RESTAURANTS AND 
        DEBUT_TYPES_RESTAURANTS <= FIN_TYPES_RESTAURANTS AND
        DEBUT_MENUS <= FIN_MENUS AND
        DEBUT_REPAS <= FIN_REPAS AND
        DEBUT_CATEGORIES <= FIN_CATEGORIES AND
        DEBUT_PLATS <= FIN_PLATS AND
        DEBUT_COMPOSITIONS <= FIN_COMPOSITIONS AND
        DEBUT <= FIN
    ),
    CONSTRAINT CK_STATISTIQUES_REQUETES CHECK (REQUETES >= 0)
) PARTITION BY HASH(ID);

-- Création des partitions pour la table TACHE
DO
$$
BEGIN
    FOR i IN 0..29 LOOP
        EXECUTE format('CREATE TABLE tache_partition_%s PARTITION OF TACHE FOR VALUES WITH (modulus 30, remainder %s)', i, i);
    END LOOP;
END;
$$;


-- Tâche log
CREATE TABLE TACHE_LOG(
    RID INT,
    IDTACHE INT,
    CONSTRAINT PK_TACHE_LOG PRIMARY KEY (RID, IDTACHE),
    CONSTRAINT FK_TACHE_LOG_RESTAURANT FOREIGN KEY (RID) REFERENCES RESTAURANT(RID),
    CONSTRAINT FK_TACHE_LOG_TACHE FOREIGN KEY (IDTACHE) REFERENCES TACHE(ID)
) PARTITION BY HASH(RID, IDTACHE);

-- Création des partitions pour la table TACHE_LOG
DO
$$
BEGIN
    FOR i IN 0..29 LOOP
        EXECUTE format('CREATE TABLE tache_log_partition_%s PARTITION OF TACHE_LOG FOR VALUES WITH (modulus 30, remainder %s)', i, i);
    END LOOP;
END;
$$;

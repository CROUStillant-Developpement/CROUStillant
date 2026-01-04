/***************************************************************
    *  CROUStillant - migration_add_menu_hash.sql
    *  Created on: 04/01/2026
    *  Description: Migration script to add MENU_HASH field to MENU table
    *  This optimizes the refresh task by avoiding unnecessary deletions
    *  and re-insertions when menu content hasn't changed.
***************************************************************/

-- Add MENU_HASH column to MENU table
ALTER TABLE MENU ADD COLUMN IF NOT EXISTS MENU_HASH VARCHAR(64);

-- Update the schema.sql updated date comment
COMMENT ON TABLE MENU IS 'Updated on: 04/01/2026 - Added MENU_HASH field for refresh optimization';

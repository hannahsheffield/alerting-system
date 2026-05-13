SELECT
  CONCAT("DROP VIEW ", "`", table_catalog, ".", table_schema, ".", table_name, "`", ";") AS sql_statements
FROM PARAM-BQ-PROJECT.PARAM-BQ-DATASET.INFORMATION_SCHEMA.VIEWS

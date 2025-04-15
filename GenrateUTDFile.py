import re
import pyodbc

def export_sp_definitions_no_block_comments(server, database, main_sp_name, output_file):
    """
    Connects to a SQL Server instance, creates & populates a temp table with the
    tables referenced by the specified main_sp_name, then retrieves stored procedure
    definitions (without the SP names, removing block comments), and writes them to a file.
    
    Parameters:
        server (str): The SQL Server name or address.
        database (str): The database name to connect to.
        main_sp_name (str): The name of the stored procedure whose table references 
                            will be used to find other SPs.
        output_file (str): The path to the output file where definitions will be saved.
    """
    connection_string = (
        "Driver={SQL Server};"
        f"Server={server};"
        f"Database={database};"
        "Trusted_Connection=yes;"
    )

    # Prep statements to build the temp table (#UsedTables) with references from the main_sp_name
    prep_sql = f"""
    SET TEXTSIZE 2147483647;
    SET NOCOUNT ON;

    IF OBJECT_ID('tempdb..#UsedTables') IS NOT NULL
        DROP TABLE #UsedTables;

    CREATE TABLE #UsedTables
    (
        TableSchema SYSNAME,
        TableName   SYSNAME
    );

    INSERT INTO #UsedTables (TableSchema, TableName)
    SELECT 
        SCHEMA_NAME(o.schema_id) AS TableSchema,
        o.name AS TableName
    FROM sys.sql_expression_dependencies sed
    INNER JOIN sys.objects procObj
        ON sed.referencing_id = procObj.object_id
    INNER JOIN sys.objects o
        ON sed.referenced_id = o.object_id
    WHERE procObj.type = 'P'
      AND procObj.name = '{main_sp_name}'  -- Using the parameter
      AND o.type = 'U'
      AND sed.referenced_id IS NOT NULL
    GROUP BY SCHEMA_NAME(o.schema_id), o.name;
    """

    # The final SELECT to get definitions from any SP that references the same tables.
    query_sql = """
    SELECT DISTINCT
        sm.[definition] AS ProcedureDefinition
    FROM #UsedTables t
    INNER JOIN sys.objects sp
        ON sp.type = 'P'
       AND sp.name LIKE 'UTD%'   -- Adjust if needed
    INNER JOIN sys.sql_expression_dependencies sed
        ON sed.referencing_id = sp.object_id
    INNER JOIN sys.objects ot
        ON sed.referenced_id = ot.object_id
    INNER JOIN sys.sql_modules sm
        ON sp.object_id = sm.object_id
    WHERE ot.type = 'U'
      AND SCHEMA_NAME(ot.schema_id) = t.TableSchema
      AND ot.name = t.TableName;
    """

    # Connect to SQL Server
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()

    # Execute preparation statements
    cursor.execute(prep_sql)
    conn.commit()

    # Execute the final SELECT
    cursor.execute(query_sql)
    rows = cursor.fetchall()

    # Regex to remove block comments of the form /* ... */
    block_comment_pattern = re.compile(r'/\*.*?\*/', flags=re.DOTALL)

    # Write the definitions to a file
    with open(output_file, "w", encoding="utf-8") as f:
        for row in rows:
            proc_def = row.ProcedureDefinition if row.ProcedureDefinition else ""
            # Remove all block comments
            proc_def_no_comments = re.sub(block_comment_pattern, '', proc_def)
            # Optionally strip extra whitespace
            proc_def_no_comments = proc_def_no_comments.strip()
            f.write(proc_def_no_comments)
            f.write("\n" + "-"*80 + "\n")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    # Example usage
    export_sp_definitions_no_block_comments(
        server=".",
        database="LoyaltyDB",
        main_sp_name="usp_RPT_BucketLiabilitySummary_sel",   # Pass the name of the SP whose table refs you want to use
        output_file="UTDs.txt"
    )

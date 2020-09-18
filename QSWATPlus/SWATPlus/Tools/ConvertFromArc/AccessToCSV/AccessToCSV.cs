// <copyright file="AccessToCSV.cs">
//     Copyright (c) Chris George. All rights reserved.
// </copyright>
// ********************************************************************************************************
// The contents of this file are subject to the Mozilla Public License Version 1.1 (the "License"); 
// you may not use this file except in compliance with the License. You may obtain a copy of the License at 
// http:// www.mozilla.org/MPL/ 
// Software distributed under the License is distributed on an "AS IS" basis, WITHOUT WARRANTY OF 
// ANY KIND, either express or implied. See the License for the specificlanguage governing rights and 
// limitations under the License. 
// 
// The Initial Developer of this version of the Original Code is Chris George.
// 
// Contributor(s): (Open source contributors should list themselves and their modifications here). 
// Change Log: 
// Date           Changed By      Notes
// ********************************************************************************************************


using System;
using System.Collections;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Data;
using System.Data.OleDb;
using System.IO;

namespace AccessToCSV
{
    class Program
    {
        public static void Main(string[] args)
        {
            if (args.Length == 0)
            {
                Console.WriteLine("You must provide at least mdb file as parameter");
                System.Environment.Exit(-1);
            }
            string db = args[0];
            if (!File.Exists(db))
            {
                Console.WriteLine("mdb file " + db + " does not exist");
                System.Environment.Exit(-1);
            }
            string connectionString = "Provider=Microsoft.Jet.OLEDB.4.0; Data Source=" + db;
            OleDbConnection dbConnection = new OleDbConnection(connectionString);
			dbConnection.Open();
			// make list of all tables
			// We only want user tables, not system tables
			string[] restrictions = new string[4];
			restrictions[3] = "Table";
			// Get list of user tables
			DataTable tables = dbConnection.GetSchema("Tables", restrictions);
			if (args.Length > 1)
			{
			    // following arguments are table names or table name prefixes (ending in '*')
			    for (int i = 1; i < args.Length; i++)
			    {
			    	string arg = args[i];
			    	//Console.WriteLine("Next arg is " + arg);
			    	if (arg[arg.Length - 1] == '*') 
			    	{
			    		string prefix = arg.Substring(0, arg.Length - 1);
			    		//Console.WriteLine("Asterisk found: prefix is " + prefix);
			    		string table = FindPrefixTable(prefix, tables);
			    		//Console.WriteLine("Prefix table is " + table);
			    		if (table != "") 
			    		{
			    			WriteCSV(table, prefix + ".csv", dbConnection);
			    		}
			    	}
			    	else if (TableInTables(arg, tables))
			    	{
			        	WriteCSV(arg, arg + ".csv", dbConnection);
			    	}
			    }
			}
			else // generate csv files for all tables
			{
			    for (int i = 0; i < tables.Rows.Count; i++)
			    {
			    	string table = tables.Rows[i][2].ToString();
			        WriteCSV(table, table + ".csv", dbConnection);
			    }
			}
			dbConnection.Close();
        }
        
        private static bool TableInTables(string table, DataTable tables)
        {
        	for (int i = 0; i < tables.Rows.Count; i++)
        	{
        		if (table == tables.Rows[i][2].ToString())
        		{
        			return true;
        		}
        	}
        	return false;
        }
        
        private static string FindPrefixTable(string prefix, DataTable tables)
        {
        	for (int i = 0; i < tables.Rows.Count; i++)
        	{
        		string table = tables.Rows[i][2].ToString();
        		if (table.StartsWith(prefix))
        		{
        		    return table;
        		}
        	}
        	return "";
        }
        
        private static void WriteCSV(string table, string fileName, OleDbConnection dbConnection)
        {
            try
            {
                string sql = "SELECT * FROM " + table;
                OleDbCommand command = new OleDbCommand(sql, dbConnection);
                OleDbDataReader reader = command.ExecuteReader();
                bool firstLine = true;
                using (StreamWriter sw = new StreamWriter(fileName))
                {
                    int num = reader.FieldCount;
                    if (firstLine)
                    {
                        firstLine = false;
                        // write column names in first line
                        if (num > 0)
                        {
                            sw.Write(reader.GetName(0));
                            for (int i = 1; i < num; i++)
                            {
                                sw.Write(",");
                                sw.Write(reader.GetName(i));
                            }
                            sw.WriteLine("");
                        }
                    }
                    while (reader.Read())
                    {
                        if (num > 0)
                        {
                            sw.Write(reader.GetValue(0).ToString());
                            for (int i = 1; i < num; i++)
                            {
                                sw.Write(",");
                                sw.Write(reader.GetValue(i).ToString());
                            }
                            sw.WriteLine("");
                        }
                    }
                }
            // Console.WriteLine(fileName + " written");
            }
            catch (Exception)
            {
                Console.WriteLine("Cannot export table " + table + " to csv");
            }
        }
    }
}
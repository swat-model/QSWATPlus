AccessToCSV takes an Access .mdb file name as an argument, and should
be run in the same directory as the Access file. 

Optionally, more arguments may be provided, which must be the names of tables in the database.  If no such arguments are provided it is the same as providing as arguments all the user (not system) tables in the database.

For each argument table it generates a .csv file with name the same as the table.   
Fields are separated by commas, and no check is made that the table
fields do not contain commas. 
The first line of the .csv file contains the Access column names.

The purpose is to provide a facility to create an SQLite database from
an access database.   
The .csv files can be manually imported into an SQLite database using
SQLiteStudio.  Or you can use the following procedure:

1.  Run AccessToCSV to generate a collection of .csv files.

2.  Delete any files of tables not required

3.  In a command shell, use the command

for %f in (*.csv) do @echo .import %f %~nf

to generate a list of sqlite .import commands

4.  Create a file F containing

.open X.sqlite
.mode csv
IMPORTS
.quit

where X is the intended sqlite database name (may or may not already
exist)
and IMPORTS is the sequence of .import commands (copied from comand shell)

5.  Run the command

C:/Program Files/SQLite ODBC Driver for Win64/sqlite3.exe < F

This initally seems to bring up a 'select file' window: click Cancel.

6.  Since there is no schema defined, the fields are all text by
default.  Seems to be no easy way to extract a table schema from
Access.
 
Field types and primary keys can be defined manually in SQLiteStudio.

The project file currently places AccessToCSV.exe in the parent of the project folder, i.e.
C:\SWAT\SWATPlus\Tools\ConvertFromArc
when it is built. 
There is a copy in obj/Debug.


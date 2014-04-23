#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import glob
import os
import sqlite3
import sys

sys.path.append("web2py")
from models.Corpus_DB import Corpus_DB

def ImportFolder(corpus_folder):
	filenames = glob.glob(corpus_folder)
	for filename in sorted(filenames):
		with open(filename, 'r') as f:
			doc_content = f.read().decode('utf-8', 'ignore')
			yield filename, doc_content

def ImportFile(corpus_filename):
	with open(corpus_filename, 'r') as f:
		for index, line in enumerate(f):
			values = line.decode('utf-8', 'ignore').rstrip('\n').split('\t')
			if len(values) == 1:
				doc_id = 'doc{}'.format(index+1)
				doc_content = values[0]
			else:
				doc_id = values[0]
				doc_content = values[1]
			yield doc_id, doc_content

def ReadFromStdin():
	for index, line in enumerate(sys.stdin):
		values = line.decode('utf-8', 'ignore').rstrip('\n').split('\t')
		if len(values) == 1:
			doc_id = 'doc{}'.format(index+1)
			doc_content = values[0]
		else:
			doc_id = values[0]
			doc_content = values[1]
		yield doc_id, doc_content

def UpdateFieldsTable(fields, conn, cursor):
	records = [[field] for field in fields]
	with conn:
		conn.executemany('insert or ignore into fields(field_name) values (?)', records)
	cursor.execute('select field_name, field_index from fields')
	field_indexes = {}
	for record in cursor:
		field_name, field_index = record
		field_indexes[field_name] = field_index
	return field_indexes

def UpdateDocsTable(doc_id, conn, cursor):
	with conn:
		conn.execute('insert or ignore into docs(doc_id) values (?)', [doc_id])
	cursor.execute('select doc_index from docs where doc_id = ?', [doc_id])
	record = cursor.fetchone()
	doc_index = record[0]
	return doc_index

def UpdateCorpusTable(doc_index, fields, values, field_indexes, conn, cursor):
	records = [ [doc_index, field_indexes[field], values[index]] for index, field in enumerate(fields) ]
	with conn:
		conn.executemany('insert or ignore into corpus(doc_index, field_index, value) values (?, ?, ?)', records)

def CreateDatabase(corpus_filename_or_folder, database_path):
	if corpus_filename_or_folder is not None:
		if os.path.isfile(corpus_filename_or_folder):
			corpus_iterator = ImportFile(corpus_filename_or_folder)
		else:
			corpus_iterator = ImportFolder(corpus_filename_or_folder)
	else:
		corpus_iterator = ReadFromStdin()
		
	database_filename = '{}/{}'.format(database_path, Corpus_DB.FILENAME)
	with Corpus_DB(database_path, forceCommit=True) as _:
		print 'Importing into database at {}'.format(database_filename)
	
	conn = sqlite3.connect(database_filename)
	cursor = conn.cursor()
	fields = ['doc_id', 'doc_content']
	field_indexes = UpdateFieldsTable(fields, conn, cursor)
	for doc_id, doc_content in corpus_iterator:
		doc_index = UpdateDocsTable(doc_id, conn, cursor)
		UpdateCorpusTable(doc_index, fields, [doc_id, doc_content], field_indexes, conn, cursor)
	cursor.close()
	conn.close()
	
def main():
	parser = argparse.ArgumentParser( description = 'Import a TSV file or a folder into a SQLite3 Database.' )
	parser.add_argument( 'database', type = str, help = 'Output database path' )
	parser.add_argument( 'corpus'  , type = str, help = 'Input corpus (filename or folder path)', nargs = '?', default = None )
	args = parser.parse_args()
	CreateDatabase(args.corpus, args.database)

if __name__ == '__main__':
	main()
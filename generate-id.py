import argparse
import datetime
import os
import os.path
import random
import sys

try:
	from . import zettel
except ImportError:
	import zettel

def main(args):
	path = os.path.abspath(args.path)
	if not os.path.exists(path):
		print(f"No such directory: '{path}'")
		sys.exit(1)

	markdown = zettel.NoteMarkdown()
	noteFactory = lambda file_name: zettel.Note(file_name, markdown)

	collection = zettel.NoteCollection()
	collection.import_files(args.path, args.extension, noteFactory)

	new_id = suggest_id_from_date(args.date)
	while new_id in collection.notes:
		new_id = suggest_id_from_date(args.date)
	
	print(new_id)

def suggest_id_from_date(date: str) -> str:
	if len(date) == 4:
		# Add month, day, hour, minute, second
		return date + "0101" + random_number(23) + random_number(59) + random_number(59)
	elif len(date) == 6:
		# Add day, hour, minute, second
		return date + "01" + random_number(23) + random_number(59) + random_number(59)
	elif len(date) == 8:
		# Add hour, minute, second
		return date + random_number(23) + random_number(59) + random_number(59)
	elif len(date) == 10:
		# Add minute, second
		return date + random_number(59) + random_number(59)
	elif len(date) == 12:
		# Add second
		return date + random_number(59)
	elif len(date) == 14:
		# Replace seconds
		return date + date[:12] + random_number(59)
	else:
		raise ValueError(f"Unknown date format: {date}")

def random_number(max: int, positions: int = 2) -> str:
	return str(random.randint(0, max)).zfill(positions)

def parse_args():
	parser = argparse.ArgumentParser(description="Generate zettelkasten id for date")
	parser.add_argument("path", nargs="?", default=os.getcwd())
	parser.add_argument("-e", "--extension", default=".md", help="file extension of note files")
	parser.add_argument("-d", "--date", default=datetime.datetime.now().strftime("%Y%m%d%H%M"), help="date or time stamp to embed in id")
	return parser.parse_args()

if __name__ == "__main__":
	main(parse_args())

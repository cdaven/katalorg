import argparse
import datetime
import os
import os.path
import random
import re
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
	#print(f"Notes found: {len(collection.notes)}")

	changed_ids = []

	for note in collection.notes.values():
		if note.file_name.startswith(args.index):
			#print(f"- Ignores index file {note.file_name}")
			continue

		if not note.id:
			print(f"- Ignores file {note.file_name} without ID")
			continue

		title = strip_date_from_title(note.get_title(default=""))

		date = get_date_from_file_name(note.file_name)
		if date != None and len(date) < 14 and not note.id.startswith(date):
			# Date in file name is shorter than an ID and doesn't match ID
			old_id = note.id
			new_id = suggest_id_from_date(date)
			while new_id in collection.notes:
				print("- Duplicate note id, generating again")
				new_id = suggest_id_from_date(date)

			note.id = new_id
			changed_ids.append((old_id, new_id))

		new_file_name = escape_file_name(f"{note.id} {title}".strip()) + args.extension
		note_path = os.path.dirname(note.file_path)
		new_file_path = os.path.join(note_path, new_file_name)

		if note.file_name != new_file_name:
			print(f"- Renaming {note.file_name} --> {new_file_name}")
			os.rename(note.file_path, new_file_path)

	print_sed_replacements(changed_ids)

def print_sed_replacements(replacements: list):
	for (old_id, new_id) in replacements:
		print(f"grep -FirlZ '{old_id}' | xargs -0 sed -i 's/{old_id}/{new_id}/g'")

def suggest_id_from_date(date: str) -> str:
	if len(date) == 4:
		# Add month and day
		date += "0101"
	elif len(date) == 6:
		# Add day
		date += "01"
	
	if len(date) != 8:
		raise ValueError(f"Unknown date format: {date}")

	ts = datetime.datetime.strptime(date, "%Y%m%d") + \
		datetime.timedelta(seconds=random.randint(0, 86399))

	return ts.strftime("%Y%m%d%H%M%S")

def strip_date_from_title(title: str) -> str:
	# Allow "x" in date strings
	return re.sub(r"^[12]\d{3}[x\d]* ", "", title)

def get_date_from_file_name(file_name: str) -> bool:
	match = re.match(r"^([12]\d{3}\d*)[ x]", file_name)
	if match:
		return match.group(1)
	else:
		return None

def escape_file_name(file_name: str) -> str:
	return \
		re.sub(r"[<>:*?\"“”]", "", # Remove these characters
		re.sub(r"[/\\]", "-", # Replace these with a dash
			file_name))

def parse_args():
	parser = argparse.ArgumentParser(description="Rename zettelkasten note files")
	parser.add_argument("path", nargs="?", default=os.getcwd())
	parser.add_argument("-e", "--extension", default=".md", help="file extension of note files")
	parser.add_argument("-i", "--index", default="§§", help="prefix for index files, not to be renamed")
	return parser.parse_args()

if __name__ == "__main__":
	main(parse_args())

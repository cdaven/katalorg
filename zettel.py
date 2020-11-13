import os
import os.path
import re
from datetime import datetime
from typing import Final, Pattern, Callable

###################################################################################################

class NoteMarkdown:
	DEFAULT_ID_PATTERN: Final[Pattern] = r"(?:19|20)\d{12}"
	DEFAULT_LINK_PREFIX: Final[str] = "[["
	DEFAULT_LINK_POSTFIX: Final[str] = "]]"
	WORD_BOUNDARY: Final[Pattern] = r"\b"

	def __init__(self, id_pattern: Pattern="", link_prefix="", link_postfix=""):
		self.id_pattern = self.as_word(id_pattern or NoteMarkdown.DEFAULT_ID_PATTERN)
		self.link_prefix = link_prefix or NoteMarkdown.DEFAULT_LINK_PREFIX
		self.link_postfix = link_postfix or NoteMarkdown.DEFAULT_LINK_POSTFIX

		# Matches an ID not between link start and link end
		self.id_regex = re.compile(self.get_nonlink_id_regex_pattern())

		# Matches an ID between link start and link end
		self.link_regex = re.compile(self.get_link_regex_pattern())

		# Matches Markdown level 1 header on a line of its own
		self.title_regex = re.compile(r"^#\s+(.+)$", re.MULTILINE)

		self.backlinks_section = "\n---\n\n**Backlinks** <!-- generated on {timestamp} -->\n"
		self.backlinks_section_pattern = re.compile(
			re.escape(self.backlinks_section).replace(r"\{timestamp\}", "(.+?)") + r"(.+)\Z",
			re.DOTALL
		)

	def get_note_id(self, text: str) -> str:
		"""Extract ID from note text"""

		match = self.id_regex.search(text)
		if match:
			return match.group(0)
		else:
			return None

	def get_note_links(self, text: str) -> list[str]:
		"""Extract links from note text"""
		return self.link_regex.findall(text)

	def get_note_title(self, text: str) -> str:
		"""Extract level 1 title from note text"""

		match = self.title_regex.search(text)
		if match:
			return match.group(1)
		else:
			return None

	def remove_id_prefix(self, text: str) -> str:
		"""Remove potential ID prefix from string"""
		
		id = re.search(r"^" + self.id_pattern + r"\s*", text)
		if id:
			return text.removeprefix(id.group(0))
		else:
			return text

	def get_nonlink_id_regex_pattern(self) -> str:
		return self.not_preceded_by(re.escape(self.link_prefix)) + "(" + self.id_pattern + ")" + self.not_followed_by(re.escape(self.link_postfix))

	def get_link_regex_pattern(self, id_pattern: str = None) -> str:
		if not id_pattern:
			id_pattern = self.id_pattern
			
		return re.escape(self.link_prefix) + "(" + id_pattern + ")" + re.escape(self.link_postfix)

	def link(self, id: str) -> str:
		if id:
			return self.link_prefix + id + self.link_postfix
		else:
			return ""

	def as_word(self, s: str) -> Pattern:
		return NoteMarkdown.WORD_BOUNDARY + s + NoteMarkdown.WORD_BOUNDARY

	def not_followed_by(self, s: str) -> Pattern:
		return "(?!" + s + ")"

	def not_preceded_by(self, s: str) -> Pattern:
		return "(?<!" + s + ")"

	def get_backlinks(self, text: str) -> list:
		section = self.backlinks_section_pattern.search(text)
		if section:
			# TODO: Fångar inte upp länkar med icke fullgoda ZID. Är det ett problem?
			pattern = r"^- " + self.get_link_regex_pattern(r".*?") + r" (.*)$"
			return re.findall(pattern, section.group(2), re.MULTILINE)
		else:
			return []

	def remove_backlinks(self, text: str) -> str:
		"""Remove backlinks section from note text"""
		return self.backlinks_section_pattern.sub("", text)

	def append_backlinks(self, text: str, links: list[str]) -> str:
		return text.rstrip() + "\n" + \
			self.backlinks_section.format(timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")) + \
			"".join(list(map(lambda l: "\n- " + l, links)))

###################################################################################################

class Note:
	def __init__(self, file_path: str, markdown: NoteMarkdown=None):
		self.file_path = file_path
		self.file_name = os.path.basename(file_path)
		self.markdown = markdown or NoteMarkdown()
		self.read_from_file()

	def read_from_file(self) -> None:
		with open(self.file_path, "r", encoding="utf-8") as file:
				self.file_content = file.read()

		# Don't analyse generated backlinks
		file_content_except_backlinks = self.markdown.remove_backlinks(self.file_content)

		self.id = self.markdown.get_note_id(file_content_except_backlinks)
		self.title = self.markdown.get_note_title(file_content_except_backlinks)
		self.links = self.markdown.get_note_links(file_content_except_backlinks)

		if not self.id:
			# Try if filename contains ID if note doesn't,
			# but the note should be able to override filename
			self.id = self.markdown.get_note_id(self.file_name)
	
	def write_to_file(self):
		with open(self.file_path, "w", encoding="utf-8") as file:
			file.seek(0)
			file.truncate()
			file.write(self.file_content.rstrip() + "\n")

	def backlinks_has_changed(self, linking_notes: list["Note"]) -> bool:
		current_list = set(self.markdown.get_backlinks(self.file_content))
		new_list = set(map(lambda n: (n.get_id(), n.get_title()), linking_notes))
		# If there is any added or removed link, update the section
		return len(current_list ^ new_list) > 0

	def update_backlinks(self, linking_notes: list["Note"], overwrite=False) -> bool:
		if overwrite or self.backlinks_has_changed(linking_notes):
			self.file_content = self.markdown.remove_backlinks(self.file_content)
			if len(linking_notes) > 0:
				self.file_content = self.markdown.append_backlinks(
					self.file_content,
					list(
						map(
							lambda n: f"{self.markdown.link(n.get_id())} {n.get_title()}",
							linking_notes
						)
					)
				)
			return True
		else:
			return False

	def get_id(self) -> str:
		return self.id or ""

	def get_title(self) -> str:
		if self.title:
			return self.title
		else:
			file_name = os.path.splitext(self.file_name)[0]
			file_name_without_id = self.markdown.remove_id_prefix(file_name)
			if file_name_without_id:
				return file_name_without_id
			else:
				return "(no title)"

	def __str__(self):
		return self.file_name + ": " + self.get_id() + ", " + self.get_title()

###################################################################################################

class NoteCollection:
	def import_files(self, path=".", extension=".md", noteFactory: Callable[[str], Note]=None) -> None:
		"""Import files with notes from the given path"""

		self.notes: dict[str, Note] = {}

		if not noteFactory:
			noteFactory = lambda file_name: Note(file_name)

		for file_name in os.listdir(path):
			file_path = os.path.join(path, file_name)
			if not os.path.isfile(file_path) or not file_name.endswith(extension):
				continue

			note = noteFactory(file_path)

			if note.id:
				self.notes[note.id] = note
			elif note.title:
				self.notes[note.title] = note
			else:
				self.notes[note.file_name] = note

	def find_backlinks(self) -> None:
		# Key = target note id
		self.backlinks: dict[str, list[Note]] = {}

		for note in self.notes.values():
			for linked_id in note.links:
				if linked_id in self.backlinks:
					self.backlinks[linked_id].append(note)
				else:
					self.backlinks[linked_id] = [note]

	def get_more_note_data(self) -> None:
		self.orphans: list[Note] = []
		self.notes_without_id: list[Note] = []
		self.broken_links: list[str] = []

		for note in self.notes.values():
			if not note.id:
				self.notes_without_id.append(note)
			elif note.id not in self.backlinks:
				self.orphans.append(note)
			
			self.broken_links.extend([link for link in note.links if link not in self.notes])

	def update_backlinks_sections(self, overwrite=False) -> int:
		count = 0

		for backlink in self.backlinks:
			if not backlink in self.notes:
				# Broken link, no target to update
				continue

			target_note = self.notes[backlink]
			linking_notes = self.backlinks[backlink]

			if target_note.update_backlinks(linking_notes, overwrite):
				count += 1
				target_note.write_to_file()
		
		for orphan in self.orphans:
			# Remove previous backlinks from orphans
			if orphan.update_backlinks([], overwrite):
				count += 1
				orphan.write_to_file()
		
		return count

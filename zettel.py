import os
import os.path
import pathlib
import re
from datetime import datetime
from typing import Callable, Optional


class NoteMarkdownParser:
    DEFAULT_ID_PATTERN = r"(?:19|20)\d{12}"
    DEFAULT_LINK_PREFIX = "[["
    DEFAULT_LINK_POSTFIX = "]]"
    WORD_BOUNDARY = r"\b"

    def __init__(self, id_pattern: str = "", link_prefix="", link_postfix=""):
        self.id_pattern = self.as_word(id_pattern or NoteMarkdownParser.DEFAULT_ID_PATTERN)
        self.link_prefix = link_prefix or NoteMarkdownParser.DEFAULT_LINK_PREFIX
        self.link_postfix = link_postfix or NoteMarkdownParser.DEFAULT_LINK_POSTFIX

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

    def get_note_id(self, text: str) -> Optional[str]:
        """Extract ID from note text"""

        match = self.id_regex.search(text)
        if match:
            return match.group(0)
        else:
            return None

    def get_note_links(self, text: str) -> list[str]:
        """Extract links from note text"""
        return self.link_regex.findall(text)

    def get_note_title(self, text: str) -> Optional[str]:
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
        return self.not_preceded_by(re.escape(self.link_prefix)) + \
            "(" + self.id_pattern + ")" + \
            self.not_followed_by(re.escape(self.link_postfix))

    def get_link_regex_pattern(self, id_pattern: str = None) -> str:
        if not id_pattern:
            id_pattern = self.id_pattern

        return re.escape(self.link_prefix) + "(" + id_pattern + ")" + re.escape(self.link_postfix)

    def link(self, id: str) -> str:
        if id:
            return self.link_prefix + id + self.link_postfix
        else:
            return ""

    def as_word(self, s: str) -> str:
        return NoteMarkdownParser.WORD_BOUNDARY + s + NoteMarkdownParser.WORD_BOUNDARY

    def not_followed_by(self, s: str) -> str:
        return "(?!" + s + ")"

    def not_preceded_by(self, s: str) -> str:
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
            self.backlinks_section.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M")) + \
            "".join(list(map(lambda l: "\n- " + l, links)))


class NoteFile:
    def __init__(self, path: str, encoding: str = "utf-8"):
        self.__path = path
        self.__encoding = encoding

    def get_name(self) -> str:
        return os.path.basename(self.__path)

    def read(self) -> str:
        with open(self.__path, "r", encoding=self.__encoding) as file:
            return file.read()

    def write(self, contents: str):
        with open(self.__path, "w", encoding=self.__encoding) as file:
            file.seek(0)
            file.truncate()
            file.write(contents)

    def rename(self, name: str):
        new_path = os.path.join(os.path.dirname(self.__path), name)
        os.rename(self.__path, new_path)
        self.__path = new_path


class Note:
    def __init__(self, file: NoteFile, parser: Optional[NoteMarkdownParser] = None):
        self.__file = file
        self.__parser = parser or NoteMarkdownParser()
        self.read_from_file()

    def read_from_file(self) -> None:
        self.__content = self.__file.read()

        # Don't analyse generated backlinks
        content_except_backlinks = self.__parser.remove_backlinks(self.__content)

        self.__id = self.__parser.get_note_id(content_except_backlinks)
        self.__title = self.__parser.get_note_title(content_except_backlinks)
        self.__links = self.__parser.get_note_links(content_except_backlinks)

        if not self.__id:
            # Try if filename contains ID if note doesn't,
            # but the note should be able to override filename
            self.__id = self.__parser.get_note_id(self.__file.get_name())

    def write_to_file(self):
        self.__file.write(self.__content.rstrip() + "\n")

    def rename_file(self, name: str):
        self.__file.rename(name)

    def backlinks_has_changed(self, linking_notes: list["Note"]) -> bool:
        current_list = set(self.__parser.get_backlinks(self.__content))
        new_list = set(map(lambda n: (n.get_id(), n.get_title()), linking_notes))
        # If there is any added or removed link, update the section
        return len(current_list ^ new_list) > 0

    def update_backlinks(self, linking_notes: list["Note"], overwrite=False) -> bool:
        if overwrite or self.backlinks_has_changed(linking_notes):
            self.__content = self.__parser.remove_backlinks(self.__content)
            if len(linking_notes) > 0:
                self.__content = self.__parser.append_backlinks(
                    self.__content,
                    list(
                        map(
                            lambda n: f"{self.__parser.link(n.get_id())} {n.get_title()}",
                            linking_notes
                        )
                    )
                )
            return True
        else:
            return False

    def get_id(self) -> str:
        return self.__id or ""

    def set_id(self, id: str):
        self.__id = id

    def get_file_name(self) -> str:
        return self.__file.get_name()

    def get_title(self, default: str = "(no title)") -> str:
        if self.__title:
            return self.__title
        else:
            file_name = os.path.splitext(self.get_file_name())[0]
            file_name_without_id = self.__parser.remove_id_prefix(file_name)
            return file_name_without_id or default

    def get_links(self) -> list[str]:
        return self.__links

    def __str__(self):
        return self.get_file_name() + ": " + self.get_id() + ", " + self.get_title()


class NoteCollection:
    def import_files(self, path: str, extension: str, noteFactory: Callable[[str], Note]) -> None:
        """Import files with notes from the given path"""

        self.notes: dict[str, Note] = {}

        for file_name_obj in pathlib.Path(path).rglob("*" + extension):
            file_path = str(file_name_obj)
            if not os.path.isfile(file_path) or not file_name_obj.suffix == extension:
                continue

            self.add_note(noteFactory(file_path))

    def add_note(self, note: Note):
        identifier = note.get_id() or note.get_title(default="") or note.get_file_name()
        if identifier in self.notes:
            raise IndexError(f"Duplicate note identifier {identifier}")
        else:
            self.notes[identifier] = note

    def find_backlinks(self) -> None:
        # Key = target note id
        self.backlinks: dict[str, list[Note]] = {}

        for note in self.notes.values():
            for linked_id in note.get_links():
                if linked_id in self.backlinks:
                    self.backlinks[linked_id].append(note)
                else:
                    self.backlinks[linked_id] = [note]

    def get_more_note_data(self) -> None:
        self.orphans: list[Note] = []
        self.notes_without_id: list[Note] = []
        self.broken_links: list[str] = []

        for note in self.notes.values():
            if not note.get_id():
                self.notes_without_id.append(note)
            elif note.get_id() not in self.backlinks:
                self.orphans.append(note)

            self.broken_links.extend([link for link in note.get_links() if link not in self.notes])

    def update_backlinks_sections(self, overwrite=False) -> int:
        count = 0

        for backlink in self.backlinks:
            if backlink not in self.notes:
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

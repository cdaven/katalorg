import os
import os.path
import pathlib
import re
import collections
from typing import Callable, Optional


def stricmp(a: Optional[str], b: Optional[str]) -> bool:
    """Case insensitive string comparison"""
    if a and b:
        return a.casefold() == b.casefold()
    else:
        return False


class RegEx:
    NEWLINE = r"(?:\r?\n)"

    @staticmethod
    def as_word(s: str) -> str:
        return r"\b" + s + r"\b"

    @staticmethod
    def not_followed_by(s: str) -> str:
        return f"(?!{s})"

    @staticmethod
    def not_preceded_by(s: str) -> str:
        return f"(?<!{s})"


class NoteMarkdownParser:
    DEFAULT_ID_PATTERN = r"(?:19|20)\d{12}"
    DEFAULT_LINK_PREFIX = "[["
    DEFAULT_LINK_POSTFIX = "]]"

    def __init__(self, id_pattern: str = "", link_prefix: str = "", link_postfix: str = ""):
        self.__id_pattern = RegEx.as_word(id_pattern or NoteMarkdownParser.DEFAULT_ID_PATTERN)
        self.__link_prefix = link_prefix or NoteMarkdownParser.DEFAULT_LINK_PREFIX
        self.__link_postfix = link_postfix or NoteMarkdownParser.DEFAULT_LINK_POSTFIX

        # Matches an ID not between link start and link end
        self.__id_regex = re.compile(self.get_nonlink_id_regex_pattern())

        # Matches anything between link start and link end
        self.__link_regex = re.compile(self.get_link_regex_pattern(id_pattern=r"[^][]+?"))

        # Matches Markdown level 1 header on a line of its own
        self.__title_regex = re.compile(r"^#\s+(.+)$", re.MULTILINE)

        self.__backlinks_section_heading = "\n-----------------\n**Links to this note**\n"
        self.__backlinks_section_pattern = re.compile(
            r"\n[-*]{3,}\n+\*\*(?:Backlinks|Links to this note)\*\*(.+)\Z".replace(r"\n", RegEx.NEWLINE),
            re.DOTALL | re.IGNORECASE
        )

    def get_note_id(self, text: str) -> Optional[str]:
        """Extract ID from note text"""

        match = self.__id_regex.search(text)
        if match:
            return match.group(0)
        else:
            return None

    def get_note_links(self, text: str) -> set[str]:
        """Extract links from note text"""
        return set(self.__link_regex.findall(text))

    def get_note_title(self, text: str) -> Optional[str]:
        """Extract level 1 title from note text"""

        match = self.__title_regex.search(text)
        if match:
            return match.group(1)
        else:
            return None

    def remove_id_prefix(self, text: str) -> str:
        """Remove potential ID prefix from string"""

        id = re.search(fr"^{self.__id_pattern}\s*", text)
        if id:
            return text.removeprefix(id.group(0))
        else:
            return text

    def get_nonlink_id_regex_pattern(self) -> str:
        return RegEx.not_preceded_by(re.escape(self.__link_prefix)) + \
            "(" + self.__id_pattern + ")" + \
            RegEx.not_followed_by(re.escape(self.__link_postfix))

    def get_link_regex_pattern(self, id_pattern: str = None) -> str:
        if not id_pattern:
            id_pattern = self.__id_pattern

        return re.escape(self.__link_prefix) + f"({id_pattern})" + re.escape(self.__link_postfix)

    def create_link(self, uri: str) -> str:
        if uri:
            return self.__link_prefix + uri + self.__link_postfix
        else:
            return ""

    def get_backlinks(self, text: str) -> list[str]:
        match = self.__backlinks_section_pattern.search(text)
        if match:
            section = match.group(1)
            return re.findall(r"^[-*] (.*)$", section, re.MULTILINE)
        else:
            return []

    def remove_backlinks(self, text: str) -> str:
        """Remove backlinks section from note text"""
        return self.__backlinks_section_pattern.sub("", text)

    def append_backlinks(self, text: str, links: list[str]) -> str:
        return text.rstrip() + "\n" + \
            self.__backlinks_section_heading + \
            "".join(list(map(lambda l: "\n- " + l, links)))


class NoteFile:
    def __init__(self, path: str, encoding: str = "utf-8"):
        self.__path = path
        self.__encoding = encoding

    def get_name(self) -> str:
        return os.path.basename(self.__path)

    def get_name_without_extension(self) -> str:
        return os.path.splitext(self.get_name())[0]

    def read(self) -> str:
        with open(self.__path, "r", encoding=self.__encoding) as file:
            return file.read()

    def write(self, contents: str):
        with open(self.__path, "w", encoding=self.__encoding) as file:
            file.seek(0)
            file.truncate()
            file.write(contents)

    def rename(self, name: str) -> str:
        new_path = os.path.join(os.path.dirname(self.__path), NoteFile.escape_filename(name))
        os.rename(self.__path, new_path)
        self.__path = new_path
        return new_path

    @staticmethod
    def escape_filename(filename: str) -> str:
        return \
               re.sub(r"[<>:*?\"“”]", "",  # Remove these characters
                      re.sub(r"[/\\]", "-",  # Replace these with a dash
                             filename))


class Note:
    def __init__(self, file: NoteFile, parser: Optional[NoteMarkdownParser] = None):
        self.__file = file
        self.__parser = parser or NoteMarkdownParser()
        self.__read_from_file()

    def __read_from_file(self):
        self.__content = self.__file.read()
        content_except_backlinks = self.__parser.remove_backlinks(self.__content)
        self.__title = self.__parser.get_note_title(content_except_backlinks)
        self.__links = self.__parser.get_note_links(content_except_backlinks)
        self.__uri = \
            self.__parser.get_note_id(content_except_backlinks) or \
            self.__parser.get_note_id(self.get_filename()) or \
            self.get_filename_without_extension()

    def write_to_file(self):
        self.__file.write(self.__content.rstrip() + "\n")

    def rename_file(self, name: str) -> str:
        return self.__file.rename(name)

    def backlinks_has_changed(self, linking_notes: list["Note"]) -> bool:
        current_list = list(self.__parser.get_backlinks(self.__content))
        new_list = list(map(lambda n: n.create_link_to(), linking_notes))
        # If there is any added or removed link, update the section
        return collections.Counter(current_list) != collections.Counter(new_list)

    def update_backlinks(self, linking_notes: list["Note"], overwrite: bool = False) -> bool:
        if overwrite or self.backlinks_has_changed(linking_notes):
            content = self.__parser.remove_backlinks(self.__content)
            if len(linking_notes) > 0:
                content = self.__parser.append_backlinks(
                    content,
                    list(
                        map(
                            lambda n: n.create_link_to(),
                            linking_notes
                        )
                    )
                )
            self.__content = content
            return True
        else:
            return False

    def get_id(self) -> str:
        return self.__uri or ""

    def set_id(self, id: str):
        self.__uri = id

    def get_filename(self) -> str:
        """Returns file name without path, but with extension"""
        return self.__file.get_name()

    def get_filename_without_extension(self) -> str:
        """Returns file name without path and extension"""
        return self.__file.get_name_without_extension()

    def get_title(self) -> str:
        return \
            self.__title or \
            self.__parser.remove_id_prefix(self.get_filename_without_extension())

    def get_uri(self) -> str:
        """Returns URI for links to this note"""
        return self.get_id() or self.get_filename_without_extension()

    def create_link_to(self, append_title: bool = True) -> str:
        uri = self.get_uri()
        link = self.__parser.create_link(uri)
        if append_title:
            title = self.get_title()
            if title and not stricmp(uri, title):
                return f"{link} {title}".rstrip()

        return link

    def get_outgoing_links(self) -> set[str]:
        return self.__links


class NoteCollection:
    def import_files(self, path: str, extension: str, noteFactory: Callable[[str], Note]) -> None:
        """Import files with notes from the given path"""

        self.notes: dict[str, Note] = {}

        for filename_obj in pathlib.Path(path).rglob("*" + extension):
            file_path = str(filename_obj)
            if not os.path.isfile(file_path) or not filename_obj.suffix == extension:
                continue

            self.add_note(noteFactory(file_path))

    def add_note(self, note: Note):
        uri = note.get_uri()
        if uri in self.notes:
            raise IndexError(f"Duplicate note URI {uri}")
        else:
            self.notes[uri] = note

    def find_backlinks(self) -> None:
        # Key = target note id
        self.backlinks: dict[str, list[Note]] = {}

        for note in self.notes.values():
            for linked_id in note.get_outgoing_links():
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

            self.broken_links.extend([link for link in note.get_outgoing_links() if link not in self.notes])

    def update_backlinks_sections(self, overwrite: bool = False) -> int:
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

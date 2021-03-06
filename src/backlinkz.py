import argparse
import os
import os.path
import sys
from datetime import datetime


def main(args):
    path = os.path.abspath(args.path)
    if not os.path.exists(path):
        print(f"No such directory: '{path}'")
        sys.exit(1)

    parser = katalorg.NoteMarkdownParser()
    def noteFactory(filename: str): return katalorg.Note(katalorg.NoteFile(filename), parser)

    print("# Backlinkz Report\n")
    print(f"Path:        {path}")
    print("Time:        " + datetime.now().strftime("%Y-%m-%d %H:%M"))

    collection = katalorg.NoteCollection()
    collection.import_files(args.path, args.extension, noteFactory)
    print(f"Notes found: {len(collection.notes)}")
    collection.find_backlinks()
    collection.get_more_note_data()

    updated_backlinks = collection.update_backlinks_sections(args.overwrite)
    print(f"\nUpdated backlinks in {updated_backlinks} files")

    if args.missing and collection.notes_without_id:
        print("\n## Notes Without ID\n")
        for note in collection.notes_without_id:
            print(f"- {note.get_filename()}")

    if args.broken and collection.broken_links:
        print("\n## Broken Links\n")
        for link in collection.broken_links:
            print(f"- {link}")

    if args.orphans and collection.orphans:
        print("\n## Orphans\n")
        for note in collection.orphans:
            print(f"- {note.create_link_to()}")

    # TODO: Generate PUML graph of links


def parse_args():
    default_path = os.getcwd()
    if __debug__:
        default_path = "C:/Users/ChristianDaven/Sync/Notes"

    parser = argparse.ArgumentParser(description="Add backlinks to wiki-linked notes")
    parser.add_argument("path", nargs="?", default=default_path)
    parser.add_argument("-o", "--overwrite", action="store_true", help="overwrite existing backlinks, even if the same")
    parser.add_argument("-e", "--extension", default=".md", help="file extension of note files")
    parser.add_argument("--missing", action="store_true", default=False, help="print list of notes missing id")
    parser.add_argument("--broken", action="store_true", default=False, help="print list of broken links")
    parser.add_argument("--orphans", action="store_true", default=False, help="print list of orphans")
    return parser.parse_args()


if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import katalorg

    main(parse_args())

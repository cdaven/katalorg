import unittest
import zettel


class TestStringMethods(unittest.TestCase):

    def test_get_links(self):
        note_file = zettel.NoteFile("testdata/Links.md")
        note_contents = note_file.read()
        parser = zettel.NoteMarkdownParser()

        expected_links = set([
            "20210104073402",
            "Filename Link",
            "Search Query Link",
            "20210103212011",
            "Regular Link To Wiki URI",
            "#my-custom-id",
            "Inside Fenced Code Block"
        ])
        links = parser.get_note_links(note_contents)
        self.assertEqual(0, len(links ^ expected_links))

    def test_backlinks_section(self):
        note_file = zettel.NoteFile("testdata/BackLinks.md")
        note_contents = note_file.read()
        parser = zettel.NoteMarkdownParser()

        content = parser.remove_backlinks(note_contents)
        self.assertTrue(content.endswith("Some note text\n"))

        expected_backlinks = [
            "[[§An outline note]]",
            "[[20201012145848]] Another note",
            "Not a link"
        ]
        links = parser.get_backlinks(note_contents)

        self.assertEqual(len(expected_backlinks), len(links))
        for i in range(len(expected_backlinks)):
            self.assertEqual(expected_backlinks[i], links[i])


if __name__ == '__main__':
    unittest.main()

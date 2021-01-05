# katalorg

Python library/script that help with catalogueing and organizing your [Zettelkasten](https://en.wikipedia.org/wiki/Zettelkasten)-like pile of notes with \[\[wiki-style\]\] links between them.

## Collecting backlinks

By running the script xyz.py and pointing it at your pile of notes, all wiki-style links will be collected, and each note will get a list of backlinks at the end:

```md
-----------------
**Links to this note**

- [[20201020093536]] Some random thoughts
- [[20201020113715]] The meaning of life, the universe, and everything
```

These lists will update every time the script is run. Do not write anything after them, as that will be removed.

_(Why is this not a section with its own heading? Syntactically, it probably should be, but I prefer my backlinks a bit less intrusive.)_

### Linking notes

Notes can be linked by using either

1. the target note's file name without the extension: `[[Some random thoughts]]`, or
2. the target note's (Zettelkasten) id

The idea of using an id (pun intended) comes from the Zettelkasten principles, and [Zettlr](https://docs.zettlr.com/en/academic/zkn-method/#internal-linking) specifically.

## Inspiration and related projects

- [Andy Matuschak's note-link-janitor](https://github.com/andymatuschak/note-link-janitor/) does about the same thing, but probably not exactly the same. I haven't tried it.
- [Foam](https://foambubble.github.io/foam/) gives you backlinks and a graph inside Visual Studio Code.
- [Obsidian](https://obsidian.md/) has this stuff built into the application itself. (But make sure you read the license if you don't want to pay for it.)

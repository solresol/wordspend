import unittest

from wordspend.book_alignment import extract_translation_books, roman_to_int


TEXT = (
    "BOOK I.\r\n\r\n"
    "Editorial summary one.\r\n\r\n"
    "Sing, goddess, Achilles' wrath.\r\n"
    "A second translated line.\r\n\r\n"
    "BOOK II.\r\n\r\n"
    "Editorial summary two.\r\n\r\n"
    "Now all the other gods slept.\r\n"
)

POPE_STYLE_TEXT = (
    "BOOK I.\r\n\r\n"
    "ARGUMENT.\r\n\r\n"
    "THE CONTENTION.\r\n\r\n"
    "The synopsis of the first book.\r\n\r\n"
    "Achilles' wrath, to Greece the direful spring.\r\n\r\n"
    "[Illustration: ] A WRAPPED CAPTION\r\n"
    "CONTINUED ON THIS LINE\r\n\r\n"
    "Of woes unnumber'd, heavenly goddess, sing!\r\n"
)


class BookAlignmentTests(unittest.TestCase):
    def test_parses_only_canonical_roman_numerals(self):
        self.assertEqual(roman_to_int("XXIV"), 24)
        with self.assertRaisesRegex(ValueError, "non-canonical"):
            roman_to_int("IIII")

    def test_extracts_consecutive_books_and_skips_declared_summary(self):
        books = extract_translation_books(
            TEXT,
            "en",
            expected_book_count=2,
            leading_paragraphs_to_skip=1,
        )

        self.assertEqual([book.book for book in books], [1, 2])
        self.assertEqual(
            books[0].text,
            "Sing, goddess, Achilles' wrath.\nA second translated line.",
        )
        self.assertEqual(books[0].start_line, 5)
        self.assertEqual(books[0].token_count, 8)
        self.assertEqual(books[0].excluded_paragraph_count, 0)
        self.assertEqual(
            TEXT[books[1].start_char : books[1].end_char],
            "Now all the other gods slept.",
        )

    def test_rejects_missing_book_heading(self):
        with self.assertRaisesRegex(ValueError, "expected 3 BOOK headings"):
            extract_translation_books(
                TEXT,
                "en",
                expected_book_count=3,
                leading_paragraphs_to_skip=1,
            )

    def test_skips_pope_argument_and_strips_illustration_caption_paragraph(self):
        books = extract_translation_books(
            POPE_STYLE_TEXT,
            "en",
            expected_book_count=1,
            leading_paragraphs_to_skip=3,
            internal_paratext_policy="strip_gutenberg_illustration_paragraphs_v1",
        )

        self.assertEqual(books[0].excluded_paragraph_count, 1)
        self.assertNotIn("Illustration", books[0].text)
        self.assertNotIn("CONTINUED ON THIS LINE", books[0].text)
        self.assertTrue(books[0].text.startswith("Achilles' wrath"))
        self.assertTrue(books[0].text.endswith("heavenly goddess, sing!"))

    def test_rejects_unknown_internal_paratext_policy(self):
        with self.assertRaisesRegex(ValueError, "unsupported internal_paratext_policy"):
            extract_translation_books(
                TEXT,
                "en",
                expected_book_count=2,
                leading_paragraphs_to_skip=1,
                internal_paratext_policy="strip_everything",
            )


if __name__ == "__main__":
    unittest.main()

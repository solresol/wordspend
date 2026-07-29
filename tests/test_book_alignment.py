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


if __name__ == "__main__":
    unittest.main()

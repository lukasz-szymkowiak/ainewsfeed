import unittest

from NewsAPI.api_scrapper import dedupe_by_title, filter_by_query


def article(title=None, description=None, url=None, published="2026-09-26T12:00:00Z"):
    return dict(title=title, description=description, url=url, published=published)


class ArticleFilteringTests(unittest.TestCase):
    def test_whole_names_and_missing_fields(self):
        real = article("NASDAQ:PDD reports earnings")
        self.assertEqual(filter_by_query([
            article(), article("Temur discusses markets"), real,
        ], "pinduoduo"), [real])
        self.assertEqual(filter_by_query([real], " "), [])

    def test_figurative_names_and_actual_company_mentions(self):
        real = article("Temu Beef nickname explained", "PDD Holdings responds")
        self.assertEqual(filter_by_query([
            article("Temu Beef imports"),
            article("Car sales grow", "Dubbed the 'Temu Range Rover'"),
            real,
        ], "pinduoduo"), [real])

    def test_generic_company_and_description_match(self):
        real = article(None, "Microsoft expands its business")
        self.assertEqual(filter_by_query([real], "Microsoft"), [real])

    def test_unicode_headlines_and_tracking_urls(self):
        first = article("France: Fashion\u00a0Fines!", url="https://example.com/a?id=1&utm_source=x")
        same_title = article("FRANCE fashion fines", url="https://other.com/b")
        same_url = article("Another headline", url="https://example.com/a?fbclid=x&id=1#top")
        distinct = article("Separate report", url="https://example.com/a?id=2")
        self.assertEqual(dedupe_by_title([first, same_title, same_url, distinct]), [first, distinct])

    def test_syndication_requires_same_day_and_matching_preview(self):
        preview = "Shein and Temu are expanding across Africa with low prices and vast product ranges. Businesses warn of costs."
        first = article("How can African retailers compete with Shein and Temu?", preview)
        duplicate = article("Can African retailers compete with Shein and Temu? Changing African markets", preview)
        next_day = article("African retailers compete with Shein and Temu tomorrow", preview, published="2026-09-27T12:00:00Z")
        independent = article("African retailers face new competition from Temu", "Independent reporting with different details")
        self.assertEqual(dedupe_by_title([first, duplicate, next_day, independent]), [first, next_day, independent])

    def test_missing_titles_and_urls_do_not_collapse_records(self):
        items = [article(description="First"), article(description="Second")]
        self.assertEqual(dedupe_by_title(items), items)


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

from NewsAPI.api_scrapper import add_article_text, dedupe_by_title, filter_business_news, filter_by_query
from NewsAPI.read_json import select_article


def article(title=None, description=None, url=None, published="2026-09-26T12:00:00Z"):
    return dict(title=title, description=description, url=url, published=published)


class ArticleFilteringTests(unittest.TestCase):
    def test_refresh_preserves_existing_text_and_downloads_new_articles(self):
        saved = dict(article("PDD earnings", url="https://example.com/saved"), text="Saved body")
        new = article("Temu invests in logistics", url="https://example.com/new")
        with patch("NewsAPI.api_scrapper.fetch_url", return_value="<html>new</html>") as fetch:
            with patch("NewsAPI.api_scrapper.extract", return_value="New body"):
                result = add_article_text([saved, new])
        self.assertEqual([item["text"] for item in result], ["Saved body", "New body"])
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(fetch.call_args.args[0], "https://example.com/new")

    def test_business_context_in_description_keeps_new_developments(self):
        update = article(
            "Temu axed its $1 billion network of fake influencer accounts on Meta",
            "Temu had spent nearly $1 billion funding partnership ads with influencers.",
        )
        digest = article("Digest: McDonald's Bets on $1bn Ad Business; Temu Cuts Fake Influencer Network on Meta")
        lifestyle = article(
            "Shein, Temu shoppers keep adding to cart despite environmental concerns",
            "A study found shoppers care about price, convenience and variety.",
        )
        self.assertEqual(filter_business_news([update, digest, lifestyle], "pinduoduo"),
                         [update, digest])

    def test_business_news_excludes_lifestyle_and_product_reviews(self):
        earnings = article("PDD reports quarterly earnings")
        logistics = article("Temu owner invests in local fulfillment")
        regulation = article("France targets Shein and Temu with fast fashion fees")
        items = [
            article("Shein, Temu shoppers keep adding to cart despite environmental concerns"),
            article("Expert finds this Temu Wi-Fi extender is full of security issues"),
            article("Shirt brand owner shares fix to remove Temu dupes"),
            article("Retail earnings rise", "Shoppers also use Temu"),
            earnings, logistics, regulation,
        ]
        self.assertEqual(filter_business_news(items, "pinduoduo"),
                         [earnings, logistics, regulation])

    def test_selection_skips_missing_text_and_lifestyle_stories(self):
        lifestyle = dict(article("Temu shoppers keep adding to cart"), text="Shopping study")
        missing = dict(article("PDD reports earnings"), text=None)
        blank = dict(article("Temu faces new fees"), text="  ")
        valid = dict(article("Temu invests in logistics"), text="Company operations report")
        self.assertEqual(select_article([lifestyle, missing, blank, valid]), valid)
        with self.assertRaisesRegex(ValueError, "No company business news"):
            select_article([lifestyle, missing, blank])
        with self.assertRaises(ValueError):
            select_article([])

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

    def test_seller_promotions_are_filtered_before_article_download(self):
        education = article("Temu Expands Seller Education with Bureau Veritas")
        integration = article("TopDawg Launches Temu Integration for Retailers, Expanding Multi-Channel Dropshipping Platform")
        earnings = article("PDD earnings rise as merchant investments continue")
        regulation = article("Temu sellers face new regulations")
        self.assertEqual(
            filter_by_query([education, integration, earnings, regulation], "pinduoduo"),
            [earnings, regulation],
        )

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

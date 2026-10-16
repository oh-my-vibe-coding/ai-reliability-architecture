"""Regression checks for chapter links across GitHub and the reading site."""

from types import SimpleNamespace
import unittest

from heading_anchors import on_page_content


class HeadingAnchorsTest(unittest.TestCase):
    def test_chinese_link_and_old_permalink_both_work(self):
        page = SimpleNamespace(present_anchor_ids={"15-vs"})
        html = '<h3 id="15-vs">1.5 开源 vs 闭源的差距变化<a class="headerlink">¶</a></h3>'
        result = on_page_content(html, page=page)
        self.assertIn('id="15-开源-vs-闭源的差距变化"', result)
        self.assertIn('id="15-vs"', result)
        self.assertIn("15-开源-vs-闭源的差距变化", page.present_anchor_ids)

    def test_inline_markup_and_punctuation(self):
        result = on_page_content('<h2 id="old">Pattern 2 · <code>Cache Miss Storm</code>（缓存风暴）</h2>')
        self.assertIn('id="pattern-2--cache-miss-storm缓存风暴"', result)

    def test_duplicate_titles_have_unique_aliases(self):
        result = on_page_content('<h2 id="a">概念</h2><h2 id="b">概念</h2>')
        self.assertEqual(result.count('id="概念"'), 1)
        self.assertEqual(result.count('id="概念-1"'), 1)

    def test_existing_id_is_not_duplicated(self):
        html = '<h2 id="概念">概念</h2>'
        self.assertEqual(on_page_content(html), html)

    def test_second_pass_is_idempotent(self):
        html = '<h2 id="old">中文 &amp; English</h2>'
        once = on_page_content(html)
        self.assertEqual(on_page_content(once), once)


if __name__ == "__main__":
    unittest.main()

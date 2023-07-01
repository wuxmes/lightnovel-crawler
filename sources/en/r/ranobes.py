# -*- coding: utf-8 -*-
import logging
import re

from typing import Generator, Union

from bs4 import BeautifulSoup, Tag

from lncrawl.models import Chapter, SearchResult, Volume
from lncrawl.templates.browser.searchable import SearchableBrowserTemplate
from lncrawl.core.exeptions import FallbackToBrowser

from urllib.parse import urljoin, quote_plus

logger = logging.getLogger(__name__)


digit_regex = re.compile(r"\/(\d+)-")


class RanobeLibCrawler(SearchableBrowserTemplate):
    base_url = [
        "https://ranobes.top/",
    ]
    has_manga = False
    has_mtl = False

    def initialize(self) -> None:
        self.cleaner.bad_css.update([".free-support", 'div[id^="adfox_"]'])

    def select_search_items_in_browser(self, query: str) -> Generator[Tag, None, None]:
        self.visit(urljoin(self.home_url, "/search/{}/".format(quote_plus(query))))
        self.browser.wait(".breadcrumbs-panel")
        for elem in self.browser.find_all(".short-cont .title a"):
            yield elem.as_tag()

    def select_search_items(self, query: str) -> Generator[Tag, None, None]:
        raise FallbackToBrowser()

    def parse_search_item(self, tag: Tag) -> SearchResult:
        return SearchResult(
            title=tag.text.strip(),
            url=self.absolute_url(tag["href"]),
        )

    def visit_novel_page_in_browser(self) -> BeautifulSoup:
        self.visit(self.novel_url)
        self.browser.wait(".body_left_in")
        self.novel_id = digit_regex.search(self.novel_url).group(1)

    def parse_title(self, soup: BeautifulSoup) -> str:
        tag = soup.select_one("h1.title")
        assert tag
        return tag.text.strip()

    def parse_cover(self, soup: BeautifulSoup) -> str:
        tag = soup.select_one(".r-fullstory-poster .poster a img")
        assert tag
        if tag.has_attr("data-src"):
            return self.absolute_url(tag["data-src"])
        if tag.has_attr("src"):
            return self.absolute_url(tag["src"])

    def parse_authors(self, soup: BeautifulSoup) -> Generator[str, None, None]:
        for a in soup.select('.tag_list a[href*="/authors/"]'):
            yield a.text.strip()

    def parse_chapter_list_in_browser(
        self,
    ) -> Generator[Union[Chapter, Volume], None, None]:
        self.browser.visit(urljoin(self.home_url, f"/chapters/{self.novel_id}/"))
        self.browser.wait(".chapters__container")
        _pages = max(
            int(a["value"]) for a in self.browser.soup.select(".form_submit option")
        )
        if not _pages:
            _page = 1
        tags = self.browser.soup.select(".chapters__container .cat_line a")
        for i in range(2, _pages + 1):
            self.browser.visit(
                urljoin(self.home_url, f"/chapters/{self.novel_id}/page/{i}/")
            )
            self.browser.wait(".chapters__container")
            tags += self.browser.soup.select(".chapters__container .cat_line a")

        for _id, _t in enumerate(reversed(tags)):
            yield Chapter(
                id=_id, url=self.absolute_url(_t.get("href")), title=_t.get("title")
            )

    def parse_chapter_list(
        self, soup: BeautifulSoup
    ) -> Generator[Union[Chapter, Volume], None, None]:
        pass

    def visit_chapter_page_in_browser(self, chapter: Chapter) -> None:
        self.visit(chapter.url)
        self.browser.wait(".structure")

    def select_chapter_body(self, soup: BeautifulSoup) -> Tag:
        return soup.select_one("div#arrticle")

    def download_chapter_body_in_scraper(self, chapter: Chapter) -> str:
        raise FallbackToBrowser()

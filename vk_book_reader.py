from typing import Dict, List, Any, AsyncGenerator, Optional
import asyncio
import os
from enum import Enum
import logging
from aiohttp import ClientSession

from dataclasses import dataclass


@dataclass
class Book:
    id: int
    owner_id: int
    title: str
    size: int
    ext: str
    url: str
    date: int
    type: int
    preview: Dict = None

    def __eq__(self, other):
        return self.id == other.id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.id)


class Extensions(str, Enum):
    MOBI = 'mobi'
    PDF = 'pdf'
    FB2 = 'fb2'
    EPUB = 'epub'

    @staticmethod
    def values():
        return [elem for elem in Extensions]


class VkBookReader:
    API_URL_SEARCH = 'https://api.vk.com/method/docs.search'
    VERSION = '5.131'
    COUNT = 101
    THRESHOLD_SIZE_BYTES = 1048576  # 1MB
    RETURN_SIZE = 10
    ALLOWED_EXTENSIONS = (Extensions.PDF, Extensions.FB2,)
    LOW_SIZE_EXTENTIONS = (Extensions.MOBI, Extensions.EPUB)

    def __init__(self, ext_to_search: str):
        self.token = os.environ.get('VK_ACCESS_TOKEN')
        self.ext_to_search = ext_to_search

    async def get_books_by_search(self, q: str) -> Optional[List[Book]]:
        url = f"{self.API_URL_SEARCH}?q={q}&count={self.COUNT}&access_token={self.token}&v={self.VERSION}"

        try:
            async with ClientSession() as session:
                res = await session.get(url)
                res_json = await res.json()
                books = res_json['response']['items']
                books = self._map_books(books)
                filtered_books = self._filter_books(books)
                checked_books = self._check_block_book(filtered_books, session)
                deduplicated_books = {book async for book in checked_books}

                return (
                    list(deduplicated_books)
                    if len(deduplicated_books) < self.RETURN_SIZE
                    else list(deduplicated_books)[:self.RETURN_SIZE]
                )
        except Exception as e:
            logging.error(e)
            return None

    @staticmethod
    async def _map_books(books: List[Any]) -> AsyncGenerator[Book, Book]:
        for book in books:
            yield Book(**book)

    async def _filter_books(self, books: AsyncGenerator[Book, Book]) -> AsyncGenerator[Book, Book]:
        async for book in books:
            if book.ext == self.ext_to_search:
                if self.ext_to_search in self.LOW_SIZE_EXTENTIONS:
                    yield book
                elif self.ext_to_search in self.ALLOWED_EXTENSIONS and book.size > self.THRESHOLD_SIZE_BYTES:
                    yield book

    @staticmethod
    async def _check_block_book(books: AsyncGenerator[Book, Book], session: ClientSession) -> AsyncGenerator[Book, Book]:
        async for book in books:
            text = ''
            try:
                res = await session.get(book.url, timeout=0.5)
                text = await res.text()
            except asyncio.exceptions.TimeoutError:
                yield book

            if 'class="message_page_body"' not in text:
                yield book

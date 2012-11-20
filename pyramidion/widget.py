# Copyright (C) 2012 the Pyramidion authors and contributors
# <see AUTHORS file>
#
# This module is part of Pyramidion and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from collections import namedtuple
import math


class SearchResult(object):

    def __init__(self, results, cols=None, paginator=None):
        self.results = results or []
        self.cols = cols or []
        self.paginator = paginator or Paginator(len(self.results), 0, 25)

    def rows(self):
        for obj in self.results:
            yield self.row(obj)

    def row(self, obj):
        for col in self.cols:
            item = obj
            for name in col.split('.'):
                item = getattr(obj, name, None)

            yield item


class Paginator(object):

    def __init__(self, total, start, limit, factory=None):
        self.total = int(total)
        self.start = int(start)
        self.limit = int(limit)
        self.pages = int(math.ceil(float(self.total) / self.limit))
        if factory is None:
            factory = namedtuple('Page', ['number', 'start', 'limit'])

        self.Page = factory

    def _compute_start(self, page):
        # Subtract -1 to page because 'start' begin from 0
        page = page - 1
        if page < 0:
            page = 0
        return page * self.limit

    def _compute_page(self, start):
        return int(math.ceil(float(start) / self.limit)) + 1

    @property
    def first(self):
        return self.Page(number=1, start=0, limit=self.limit)

    @property
    def previous(self):
        start = self.start - self.limit
        if start <= 0:
            start = 0
        return self.Page(number=self._compute_page(start),
                         start=start,
                         limit=self.limit)

    @property
    def current(self):
        return self.Page(number=self._compute_page(self.start),
                         start=self.start,
                         limit=self.limit)

    def get_pages(self, length=5, include_current=False):

        current_page = self._compute_page(self.start)
        last_page = current_page + length

        if length > 0 and last_page > self.pages:
            last_page = self.pages

        elif length < 0 and last_page < 1:
            last_page = 1

        if current_page <= last_page:
            start = current_page
            end = last_page + 1

        else:  # page > last
            start = last_page
            end = current_page + 1

        for n in range(start, end):

            if n <= 0 or n > self.pages or \
               (not include_current and n == current_page):
                continue

            else:
                yield self.Page(number=n,
                                start=self._compute_start(n),
                                limit=self.limit)

    @property
    def next(self):
        start = self.start + self.limit
        if start >= self.total:
            start = self._compute_start(self.pages)
        return self.Page(number=self._compute_page(start),
                         start=start,
                         limit=self.limit)

    @property
    def last(self):
        start = self._compute_start(self.pages)
        return self.Page(number=self._compute_page(start),
                         start=start,
                         limit=self.limit)

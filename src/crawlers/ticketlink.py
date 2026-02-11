"""티켓링크 티켓 크롤러"""
import logging
from typing import List
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base import BaseCrawler, RawConcertData
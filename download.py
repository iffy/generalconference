#!/usr/bin/env python
import argparse
import requests
import lxml
import hashlib
import sys
from filepath import FilePath
from lxml.html import soupparser

def log(*args):
    sys.stderr.write(' '.join(map(unicode, args)) + '\n')


def getURL(data_dir, url):
    """
    Fetch a web page either from the local cache or else
    from the Internet.
    """
    cache_dir = data_dir.child('.cache')
    if not cache_dir.exists():
        cache_dir.makedirs()
    cache_key = hashlib.sha1(url).hexdigest()
    cache_file = cache_dir.child(cache_key)
    if not cache_file.exists():
        log('GET', url)
        r = requests.get(url)
        cache_file.setContent(r.content)
    else:
        log('[CACHE] GET', url)
    return cache_file.getContent()


def extractTalk(html):
    """
    Extract the actual talk portion and associated metadata
    from the full HTML page.
    """


def getTalkURLs(data_dir, year, month, lang):
    root = 'https://www.lds.org/general-conference/sessions'
    url = '{root}/{year}/{month:02d}?lang={lang}'.format(**locals())
    html = getURL(data_dir, url)

    parsed = soupparser.fromstring(html)
    talks = parsed.xpath("//span[@class='talk']/a")
    for talk in talks:
        yield talk.attrib['href']

def getSingleConference(data_dir, year, month, lang):
    talk_urls = getTalkURLs(data_dir, year, month, lang)
    for url in talk_urls:
        getURL(data_dir, url)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()

    ap.add_argument('--verbose', '-v',
        action='store_true',
        help='If supplied, verbose information will be printed out')
    ap.add_argument('--data-dir', '-D',
        default="data",
        type=FilePath,
        help='Root directory of where you store the data.'
             ' Default: %(default)r')
    ap.add_argument('--lang', '-L',
        default='eng',
        help='Language to fetch. Currently, only English is tested'
             ' but other languages might work, too.  Use the clang'
             ' or lang value in the URL of lds.org for the language'
             ' you want.')

    ap.add_argument('year', type=int,
        help="Year of the conference (e.g. 2015)")
    ap.add_argument('month', type=int,
        help="Month of the conference (e.g. 10 or 4)")

    args = ap.parse_args()

    if not args.verbose:
        log = lambda *a:None

    if not args.data_dir.exists():
        args.data_dir.makedirs()

    result = getSingleConference(args.data_dir, args.year, args.month,
        args.lang)
    print result

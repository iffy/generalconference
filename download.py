#!/usr/bin/env python
import argparse
import requests
import hashlib
import sys
import yaml
import re
from collections import deque
from urlparse import urlparse
from filepath import FilePath
from lxml import etree
from lxml.html import soupparser
from HTMLParser import HTMLParser

def log(*args):
    sys.stderr.write(' '.join(map(unicode, args)) + '\n')


def writeIfDifferent(fp, content):
    if not fp.exists() or fp.getContent() != content:
        fp.setContent(content)
        fp.chmod(0664)
        log('wrote {path} ({size} bytes)'.format(size=len(content), path=fp.path))

cache_dir = FilePath('.cache')

def getURL(url):
    """
    Fetch a web page either from the local cache or else
    from the Internet.
    """
    global cache_dir
    if not cache_dir.exists():
        cache_dir.makedirs()
    cache_key = hashlib.sha1(url).hexdigest()
    cache_file = cache_dir.child(cache_key)
    if not cache_file.exists():
        log('GET', url)
        r = requests.get(url)
        cache_file.setContent(r.content)
        cache_file.chmod(0664)
    else:
        log('[CACHE] GET', url)
    return cache_file.getContent()


def makeCounter():
    i = 0
    while True:
        yield i
        i += 1

def getTalkURLs(data_dir, year, month, lang):
    """
    Return a generator of talk metadata available from the index.
    """
    root = 'https://www.lds.org/general-conference/sessions'
    url = '{root}/{year}/{month:02d}?lang={lang}'.format(**locals())
    html = getURL(url)

    parsed = soupparser.fromstring(html)

    sessions = parsed.xpath('//table[@class="sessions"]')
    counter = makeCounter()
    for session_num, session in enumerate(sessions):
        session_id = session.attrib.get('id', None)
        if not session_id:
            continue

        session_title = session.xpath('.//tr[@class="head-row"]//h2')[0].text
        
        rows = session.xpath('tr')
        for row in rows:
            talk = row.xpath(".//span[@class='talk']/a")
            song = row.xpath(".//span[@class='song']")
            if not talk and not song:
                continue

            item_number = '{0:03d}'.format(counter.next())

            if song:
                # skipping for now
                continue
            elif talk:
                talk = talk[0]
                speaker = row.xpath(".//span[@class='speaker']")[0]
                url = talk.attrib['href']
                slug = urlparse(url).path.split('/')[-1]
                file_slug = '{item}-{slug}'.format(item=item_number,
                    slug=slug)
                yield {
                    'session_id': session_id,
                    'session_title': session_title,
                    'item': item_number,
                    'speaker': speaker.text,
                    'url': url,
                    'title': talk.text,
                    'slug': slug,
                    'key': file_slug,
                }


def getSingleConference(data_dir, year, month, lang):
    """
    Download and store data for a single general conference.
    """
    talk_urls = getTalkURLs(data_dir, year, month, lang)
    conf_path = data_dir.child(lang).child('{year}-{month:02d}'.format(**locals()))
    if not conf_path.exists():
        conf_path.makedirs()
    index = []
    for meta in talk_urls:
        index.append(meta)
        html = getURL(meta['url'])
        extracted_html = extractTalkAsMarkdown(html, meta)
        fp = conf_path.child(meta['key'])
        writeIfDifferent(fp, extracted_html)

    index_file = conf_path.child('index.yml')
    index_data = {
        'items': index,
    }
    writeIfDifferent(index_file,
        yaml.safe_dump(index_data, default_flow_style=False))


def extractTalkAsMarkdown(html, metadata):
    """
    Extract the talk as stripped-down HTML.
    """
    parsed = soupparser.fromstring(html)
    primary = parsed.get_element_by_id('primary')
    metadata['article_id'] = primary.get_element_by_id('article-id').text

    todelete = [
        '//div[@class="kicker"]',
        '//div[@id="video-player"]',
        '//div[@id="audio-player"]',
        '//span[@id="article-id"]',
    ]
    for x in todelete:
        elems = primary.xpath(x)
        for elem in elems:
            elem.getparent().remove(elem)
    
    import html2text
    h = html2text.HTML2Text()
    h.ignore_images = True
    h.reference_links = True
    #h.skip_internal_links = False
    markdown = h.handle(etree.tostring(primary))
    if isinstance(markdown, unicode):
        markdown = markdown.encode('utf-8')
    return markdown


class TalkParser(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.ignore_depth = None
        self.stack = deque()
        self.normalized = ''

    def startIgnoring(self):
        if self.ignore_depth is None:
            self.ignore_depth = len(self.stack)

    def stopIgnoring(self):
        self.ignore_depth = None

    def handle_starttag(self, tag, attrs):
        print 'start', tag, attrs
        d = dict(attrs)
        self.stack.append(tag)

        if d.get('id') in ('audio-player', 'video-player'):
            self.startIgnoring()

        if self.ignore_depth:
            print 'IGNORING'
            return

    def handle_endtag(self, tag):
        print 'end', tag
        self.stack.pop()

        if self.ignore_depth is not None and len(self.stack) < self.ignore_depth:
            self.stopIgnoring()

    def handle_data(self, data):
        print 'data'
        if self.ignore_depth:
            print 'IGNORING'
            return

if __name__ == '__main__':
    ap = argparse.ArgumentParser()

    ap.add_argument('--verbose', '-v',
        action='store_true',
        help='If supplied, verbose information will be printed out')
    ap.add_argument('--cache-dir', '-c',
        default='.cache',
        type=FilePath,
        help='Directory where downloaded files are cached '
             '(to preserve bandwidth).  Default: %(default)s')
    ap.add_argument('--data-dir', '-D',
        default="data",
        type=FilePath,
        help='Root directory of where you store the data.'
             ' Default: %(default)s')
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

    cache_dir = args.cache_dir

    if not args.data_dir.exists():
        args.data_dir.makedirs()

    result = getSingleConference(args.data_dir, args.year, args.month,
        args.lang)
    print result

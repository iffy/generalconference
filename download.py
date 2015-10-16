#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import requests
import hashlib
import sys
import yaml
import copy
from urlparse import urlparse
from filepath import FilePath
from lxml import etree
from lxml.html import soupparser

def log(*args):
    sys.stderr.write(' '.join(map(unicode, args)) + '\n')


def writeIfDifferent(fp, content):
    if not fp.exists() or fp.getContent() != content:
        fp.setContent(content)
        fp.chmod(0664)
        log('wrote {path} ({size} bytes)'.format(size=len(content), path=fp.path))

def mergeYAML(fp, data):
    merged_data = copy.deepcopy(data)
    if fp.exists():
        existing_data = yaml.safe_load(fp.open('rb'))
        existing_data.update(merged_data)
        merged_data = existing_data
    writeIfDifferent(fp, yaml.safe_dump(merged_data, default_flow_style=False))

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
        
        fp = conf_path.child(meta['key'])
        if not fp.exists():
            fp.makedirs()

        # text.md
        markdown = extractTalkAsMarkdown(html, meta)
        writeIfDifferent(fp.child('text.md'), markdown)

        # metadata.yml
        mergeYAML(fp.child('metadata.yml'), meta)

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
        '//div[@id="video-player"]',
        '//div[@id="audio-player"]',
        '//span[@id="article-id"]',
        '//li[@class="prev"]',
        '//li[@class="next"]',
    ]
    for x in todelete:
        elems = primary.xpath(x)
        for elem in elems:
            elem.getparent().remove(elem)

    # Remove the blockquote
    kicker = primary.xpath('.//blockquote[@class="intro dontHighlight"]')
    for k in kicker:
        k.getparent().remove(k)

    # remove no-link-style links
    for link in primary.xpath('.//a[@class="no-link-style"]'):
        link.drop_tag()

    # fix lists
    list_items = primary.xpath('.//ul[@class="bullet"]/li')
    list_items += primary.xpath('.//ol/li')
    for li in list_items:
        label = li.xpath('.//span[@class="label"]')[0]
        label.text = ''
        label.drop_tag()
        for anchor in li.xpath('.//a[@name]'):
            anchor.getparent().remove(anchor)

    # replace citations
    for citation in primary.xpath('.//sup[@class="noteMarker"]/a'):
        citation.text = '[' + citation.text + ']'
        citation.drop_tag()
    
    import html2text
    h = html2text.HTML2Text()
    h.ignore_images = True
    h.reference_links = True
    markdown = h.handle(etree.tostring(primary))
    markdown = markdown.encode('utf-8')

    # replace some common fancy chars and other things
    replacements = {
        u'…'.encode('utf-8'): '...',
        '\xc2\xa0': ' ',
        '#### Show References': '## References',
    }
    for k,v in replacements.items():
        markdown = markdown.replace(k, v)

    # get main title
    title = primary.xpath('//h1')[0].text.strip()
    markdown = '# ' + title.encode('utf-8') + '\n\n' + markdown

    return markdown


if __name__ == '__main__':
    ap = argparse.ArgumentParser()

    ap.add_argument('--quiet', '-q',
        action='store_true',
        help='If supplied, logging information will be suppressed.')
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
             ' you want.  Default: %(default)s')

    ap.add_argument('year', type=int,
        help="Year of the conference (e.g. 2015)")
    ap.add_argument('month', type=int,
        help="Month of the conference (e.g. 10 or 4)")

    args = ap.parse_args()

    if args.quiet:
        log = lambda *a:None ; # NOQA

    cache_dir = args.cache_dir

    if not args.data_dir.exists():
        args.data_dir.makedirs()

    getSingleConference(args.data_dir, args.year, args.month,
        args.lang)

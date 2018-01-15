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


class CachingDownloader(object):

    cache_dir = FilePath('.cache')

    def getURL(self, url):
        """
        Fetch a web page either from the local cache or else
        from the Internet.
        """
        global cache_dir
        if not self.cache_dir.exists():
            self.cache_dir.makedirs()
        cache_key = hashlib.sha1(url).hexdigest()
        cache_file = self.cache_dir.child(cache_key)
        if not cache_file.exists():
            log('GET', url, cache_key)
            r = requests.get(url)
            cache_file.setContent(r.content)
            cache_file.chmod(0664)
        else:
            log('[CACHE] GET', url, cache_key)
        return cache_file.getContent()

downloader = CachingDownloader()
getURL = downloader.getURL


def conferenceURL(year, month, lang):
    root = 'https://www.lds.org/general-conference'
    url = '{root}/{year}/{month:02d}?lang={lang}'.format(**locals())
    return url


def makeCounter():
    i = 0
    while True:
        yield i
        i += 1

def innerText(elem):
    return etree.tostring(elem, method='text', encoding='utf-8')

REPLACEMENTS = {
    u'…'.encode('utf-8'): '...',
    '\xc2\xa0': ' ',
    '&#x27;': "'",
    '\xe2\x80\x99': "'",
    '\xe2\x80\x9c': '"',
    '\xe2\x80\x9d': '"',
}

def unfancy(x):
    ret = x
    for k, v in REPLACEMENTS.items():
        ret = ret.replace(k, v)
    return ret

def getTalkURLs(data_dir, year, month, lang):
    """
    Return a generator of talk metadata available from the index.
    """
    url = conferenceURL(year, month, lang)
    html = getURL(url)

    parsed = soupparser.fromstring(html)

    links = parsed.xpath('//a[@class="lumen-tile__link"]')
    for item_number, link in enumerate(links):
        href = link.attrib['href']
        title = ''
        titles = link.xpath('.//div[@class="lumen-tile__title"]')
        if len(titles):
            title = unfancy(innerText(titles[0]).strip())

        speaker = ''
        speakers = link.xpath('.//div[@class="lumen-tile__content"]')
        if len(speakers):
            speaker = unfancy(innerText(speakers[0]).strip())

        slug = urlparse(href).path.split('/')[-1]
        file_slug = '{item}-{slug}'.format(item=str(item_number).zfill(3),
                slug=slug)

        # try by ancestor
        session_title = 'UNKNOWN'
        session_titles = link.xpath('ancestor::div[contains(@class, "tile-wrapper")]//span[@class="section__header__title"]')
        if len(session_titles):
            session_title = unfancy(innerText(session_titles[-1]).strip())
        else:
            # try be predecesor
            # print 'trying predecesor'
            session_titles = link.xpath('preceding::div[contains(@class, "tile-wrapper")]//span[@class="section__header__title"]')
            if len(session_titles):
                session_title = unfancy(innerText(session_titles[-1]).strip())

        yield {
            'session_title': session_title,
            'item': item_number+1,
            'speaker': speaker,
            'url': 'https://www.lds.org' + href,
            'title': title,
            'slug': slug,
            'key': file_slug,
            'year': int(year),
            'month': int(month),
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
        'year': year,
        'month': int(month),
        'items': index,
    }
    writeIfDifferent(index_file,
        yaml.safe_dump(index_data, default_flow_style=False))


def extractTalkAsMarkdown(html, metadata):
    """
    Extract the talk as stripped-down HTML.
    """
    parsed = soupparser.fromstring(html)
    content = parsed.xpath('//div[@class="body-block"]')[0]

    todelete = [
        # '//div[@id="video-player"]',
        # '//div[@id="audio-player"]',
        # '//span[@id="article-id"]',
        # '//li[@class="prev"]',
        # '//li[@class="next"]',
    ]
    for x in todelete:
        elems = content.xpath(x)
        for elem in elems:
            elem.getparent().remove(elem)

    # # Remove the blockquote
    # kicker = content.xpath('.//blockquote[@class="intro dontHighlight"]')
    # for k in kicker:
    #     k.getparent().remove(k)

    # remove no-link-style links
    for link in content.xpath('.//a[@class="no-link-style"]'):
        link.drop_tag()

    # fix lists
    list_items = content.xpath('.//ul[@class="bullet"]/li')
    list_items += content.xpath('.//ol/li')
    for li in list_items:
        label = li.xpath('.//span[@class="label"]')
        if label:
            label = label[0]
            label.text = ''
            label.drop_tag()
            for anchor in li.xpath('.//a[@name]'):
                anchor.getparent().remove(anchor)
        else:
            # 1990 Oct, Elder Scott
            childs = li.getchildren()
            for child in childs:
                child.drop_tag()

    # replace citations
    for citation in content.xpath('.//a[@class="note-ref"]/sup'):
        citation.text = '[' + innerText(citation) + ']'
        citation.drop_tag()
    
    article_html = etree.tostring(content)

    # References
    article_html += '<h2>References</h2><ol>'
    refs = parsed.xpath('//div[@id="toggledReferences"]//ol//ol//li')
    for ref in refs:
        for a in ref.xpath('.//a'):
            if 'href' in a.attrib and a.attrib['href'].startswith('/'):
                a.attrib['href'] = 'https://www.lds.org' + a.attrib['href']
        article_html += etree.tostring(ref)
    article_html += '</ol>'

    import html2text
    h = html2text.HTML2Text()
    h.ignore_images = True
    h.reference_links = True
    markdown = h.handle(article_html)
    markdown = markdown.encode('utf-8')

    # replace some common fancy chars and other things
    markdown = unfancy(markdown)

    # get main title
    title = innerText(parsed.xpath('//h1')[0]).strip()
    markdown = '# ' + title + '\n\n' + markdown

    return markdown


def listLanguages(year, month):
    url = conferenceURL(year, month, 'eng')
    html = getURL(url)
    parsed = soupparser.fromstring(html)
    for option in parsed.xpath('//div[@id="clang-selector"]/select/option'):
        value = option.attrib['value']
        if not value:
            continue
        code = value[-3:] # how stable do think this magic number will be? :)
        yield code, option.text

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

    ap.add_argument('--list-langs',
        action='store_true',
        help='Instead of download stuff, just list the available languages'
             ' for this conference.')

    ap.add_argument('year', type=int,
        help="Year of the conference (e.g. 2015)")
    ap.add_argument('month', type=int,
        help="Month of the conference (e.g. 10 or 4)")

    args = ap.parse_args()

    if args.quiet:
        log = lambda *a:None ; # NOQA

    downloader.cache_dir = args.cache_dir

    if args.list_langs:
        for code, name in listLanguages(args.year, args.month):
            print code, name
    else:
        if not args.data_dir.exists():
            args.data_dir.makedirs()

        getSingleConference(args.data_dir, args.year, args.month,
        args.lang)

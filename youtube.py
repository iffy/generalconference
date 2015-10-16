import argparse
import sys
import yaml
from filepath import FilePath
from lxml.html import soupparser

from download import mergeYAML


def parseYoutubeHTML(fh):
    parsed = soupparser.fromstring(fh.read())
    videos = parsed.xpath('//tr[@data-video-id]')

    for video in videos:
        yield {
            'url': 'https://www.youtube.com/watch?v=' + video.attrib['data-video-id'],
            'title': video.attrib['data-title'],
        }

def listExistingTalks(conf_dir):
    return yaml.safe_load(conf_dir.child('index.yml').open('rb'))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    
    def openfile(x):
        if x is None:
            return sys.stdin
        else:
            return open(x, 'rb')
    ap.add_argument('--input', '-i',
        type=openfile,
        help='File to read youtube HTML from.  Default: stdin')

    ap.add_argument('conf_dir',
            type=FilePath,
            help='Conference directory (e.g. data/eng/2015-10)')

    args = ap.parse_args()

    conf_dir = args.conf_dir
    youtube_videos = list(parseYoutubeHTML(args.input))
    yi = 0
    conf_index = listExistingTalks(conf_dir)
    for item in conf_index['items']:
        for i,y in enumerate(youtube_videos[yi:]):
            if item['speaker'].count(y['title']) \
                    or y['title'].count(item['speaker']) \
                    or y['title'] in (item['title'], item['speaker']):
                item['youtube'] = y['url']
                yi += i
                break
        if item.get('youtube'):
            mergeYAML(conf_dir.child(item['key']).child('metadata.yml'), item)

    mergeYAML(conf_dir.child('index.yml'), conf_index)
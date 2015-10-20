This is a repository of programmer-friendly versions of [General Conference](https://www.lds.org/general-conference) talks of [The Church of Jesus Christ of Latter-day Saints](https://www.lds.org/).  It is **not** an official church project and The Church owns the copyright to the content of the talks.

I made this because I often want to do programmatic things with the talks, and don't want to write the downloader/parser for every project.

**Pull requests are welcome!**

## Usage ##

First, clone this repo, then:

    pip install -r requirements.txt
    python download.py --help

So, to get the talks for April 2005, this would work:

    python download.py 2005 4

## Directory structure

The [`data/`](data/) directory contains directories for each language.  Inside each language directory, (e.g. [`data/eng/`](data/eng/)), there is a directory for each General Conference.

Inside each General Conference directory (e.g. [`data/eng/2015-10/`](data/eng/2015-10/)) you will find:

- An `index.yml` file with data for the whole conference. [Example](data/eng/2015-10/index.yml)
- A directory for each talk

Inside each talk directory (e.g. [`data/eng/2015-10/012-it-works-wonderfully`](data/eng/2015-10/012-it-works-wonderfully/)) you will find:

- A `metadata.yml` file with information about the talk.  [Example](data/eng/2015-10/012-it-works-wonderfully/metadata.yml)
- A `text.md` file with the content of the talk in it. [Example](data/eng/2015-10/012-it-works-wonderfully/text.md)
- Optionally, a `youtube_timing.yml` file information to match the text of a talk with the timing of the YouTube video.  [Example](data/eng/2015-10/012-it-works-wonderfully/youtube_timing.yml)
# Various functions for migrating content from
# - encyc-mw
# - encyc-psms
# using code from encyc-core

# Yes I know the name clashes with Django's migrations/ dir.

from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
from pathlib import Path
import re
import shutil
import subprocess
import sys
import traceback

from bs4 import BeautifulSoup, Comment
from bs4.element import Tag, NavigableString
from dateutil import parser
from django.conf import settings
from django.core.cache import cache
from django.core.files import File
from django.core.files.images import ImageFile
from django.db.utils import IntegrityError
from django.template.defaultfilters import truncatewords
from django.utils.text import slugify
import djclick as click  # https://github.com/GaretJax/django-click
from psycopg.errors import NotNullViolation
from wagtail.documents.models import Document
from wagtail.images.models import Image
from wagtail.models.collections import Collection
from wagtailmedia.models import Media

# encyc-core
from encyc import config
from encyc.models.legacy import Proxy
from encyc.models.legacy import Page as LegacyPage
from encyc.models.legacy import Source as LegacySource, SOURCE_FIELDS
from encyc.models.legacy import wikipage
from encyc import wiki
# encyc-tail
from editors.models import Author
from encyclopedia.blocks import (
    ArticleTextBlock, EncycStreamBlock, HeadingBlock, QuoteBlock,
    ImageBlock, VideoBlock, DocumentBlock,
    DataboxCampBlock)
from encyclopedia.models import ArticlesIndexPage
from encyclopedia.models import Page, Article, Footnotary
from encyclopedia import models as encyclopedia_models
from encyclopedia import databoxes

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
ARTICLES_INDEX_PAGE = 'Encyclopedia'
ARTICLES_IMAGE_COLLECTION = 'Article Images'


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('--debug','-d', is_flag=True, default=False)
def encyctail(debug):
    """encyctail - Tools for migrating Densho Encyclopedia content to Wagtail

    \b
    See "namesdb help" for examples.
    """
    if debug:
        click.echo('Debug mode is on')

@encyctail.command()
def help():
    """Detailed help and usage examples
    """
    click.echo('No help yet sry.')

@encyctail.command()
@click.option('--debug','-d', is_flag=True, default=False, help='HELP TEXT GOES HERE')
@click.argument('model')
def reset(debug, model):
    """Reset data in Wagtail database"""
    if model == 'author':
        Authors.reset()


@encyctail.command()
@click.option('--debug','-d', is_flag=True, default=False, help='HELP TEXT GOES HERE')
def authors(debug):
    """Migrate MediaWiki author pages to editors.Author wagtail.snippets
    TODO check if author exists before creating
    """
    Authors.import_authors(debug)

@encyctail.command()
@click.option('--debug','-d', is_flag=True, default=False, help='HELP TEXT GOES HERE')
@click.argument('filename')
def sources(debug, filename):
    """Migrate primary sources

    \b
    filename: Path to JSONL file containing sources info. Source binaries must
    be in same folder.
    Use prep_test_data() on packrat to prep sources data and files.
    """
    jsonl_path = Path(filename)
    sources_dir = jsonl_path.parent
    primary_sources = Sources.load_psms_sources_jsonl(jsonl_path)
    # just one for now
    primary_sources = primary_sources[:1]
    # import
    Sources.import_sources(primary_sources, sources_dir)

@encyctail.command()
@click.option('--debug','-d', is_flag=True, default=False, help='HELP TEXT GOES HERE')
@click.option('--dryrun','-D', is_flag=True, default=False, help='HELP TEXT GOES HERE')
def articles(debug, dryrun):
    """Migrate articles"""
    Articles.import_articles(debug, dryrun)


# setup ----------------------------------------------------------------

def initial_setup():
    # article images collection
    root_collection = Collection.objects.get(name='Root')
    article_images = Collection(name=ARTICLES_IMAGE_COLLECTION)
    root_collection.add_child(instance=article_images)
    # articles index page
    home_page = Page.objects.get(title='Home')
    articles_index = ArticlesIndexPage(title=ARTICLES_INDEX_PAGE)
    home_page.add_child(instance=articles_index)


# authors --------------------------------------------------------------

class Authors():

    @staticmethod
    def import_authors(debug):
        """Migrate MediaWiki author pages to editors.Author wagtail.snippets
        TODO check if author exists before creating
        """
        mw = wiki.MediaWiki()
        mwauthor_titles = Authors.mw_author_titles(mw)
        num = len(mwauthor_titles)
        for n,title in enumerate(mwauthor_titles):
            click.echo(f"{n}/{num} {title=}")
            family_name = title.split()[-1]
            given_name = ' '.join(title.split()[:-1])
            display_name = title
            mwauthor = Authors.mw_author(mw, title)
            if debug: click.echo(f"{mwauthor=}")
            try:
                wtauthor = Author.objects.get(
                    family_name=family_name,
                    given_name=given_name,
                    display_name=display_name,
                )
            except Author.DoesNotExist:
                wtauthor = Author(
                    family_name=family_name,
                    given_name=given_name,
                    display_name=display_name,
                )
            wtauthor.family_name = family_name
            wtauthor.given_name = given_name
            wtauthor.display_name = display_name
            wtauthor.description = mwauthor.description
            if debug: click.echo(f"{wtauthor=}")
            result = wtauthor.save()
            if debug: click.echo('Saved: {result}')

    """
    mwauthor.__dict__={
        'url_title': 'Kaori Akiyama',
        'title': 'Kaori Akiyama',
        'title_sort': 'akiyamakaori',
        'body': '<div class="mw-parser-output">\n <p>\n  <b>\n   Kaori Akiyama\n  </b>\n  is a Ph.D. student at the Graduate University for Advanced Study in Japanese contemporary history focusing on Japanese in Hawai\'i. Her interests are historical representation in exhibits, and also wartime experiences of Japanese people in Hawai\'i.\n </p>\n <!-- \nNewPP limit report\nCached time: 20240523205402\nCache expiry: 86400\nDynamic content: false\nComplications: []\nCPU time usage: 0.004 seconds\nReal time usage: 0.008 seconds\nPreprocessor visited node count: 6/1000000\nPost‐expand include size: 158/2097152 bytes\nTemplate argument size: 0/2097152 bytes\nHighest expansion depth: 2/40\nExpensive parser function count: 0/100\nUnstrip recursion depth: 0/20\nUnstrip post‐expand size: 0/5000000 bytes\nExtLoops count: 0\n-->\n <!--\nTransclusion expansion time report (%,ms,calls,template)\n100.00%    5.628      1 Template:Published\n100.00%    5.628      1 -total\n-->\n <!-- Saved in parser cache with key encycmw:pcache:idhash:3281-0!canonical and timestamp 20240523205402 and revision id 16698\n -->\n</div>\n<div class="toplink">\n <a href="#top">\n  <i class="icon-chevron-up">\n  </i>\n  Top\n </a>\n</div>\n',
        'description': "Kaori Akiyama\n  \n  is a Ph.D. student at the Graduate University for Advanced Study in Japanese contemporary history focusing on Japanese in Hawai'i. Her interests are historical representation in exhibits, and also wartime experiences of Japanese people in Hawai'i.",
        'author_articles': ['Japanese Immigrants in the United States and the War Era (exhibition)']
    }
    """

    @staticmethod
    def reset():
        """TODO Delete all editors.models.Author objects"""
        for author in Author.objects.all():
            author.delete()

    @staticmethod
    def mw_author_titles(mw):
        key = 'encyctng:migration:mwauthortitles'
        cached = cache.get(key)
        if not cached:
            mw_author_titles = Proxy.authors(mw)
            cached = mw_author_titles
            cache.set(key, cached, settings.CACHE_TIMEOUT_LONG)
        return cached

    @staticmethod
    def mw_author(mw, title):
        key = f"encyctng:migration:mwauthor:{slugify(title).replace('-','')}"
        cached = cache.get(key)
        if not cached:
            mw_author = LegacyPage.get(mw, title)
            cached = mw_author
            cache.set(key, cached, settings.CACHE_TIMEOUT_LONG)
        return cached

    @staticmethod
    def mediawiki_authors():
        """Return dict of all authors and their articles

        for name,articles in author_articles.items():
        print(f"{name}: {articles}")
        """
        mw = wiki.MediaWiki()
        author_articles = {}
        mw_author_titles = Proxy.authors(mw, cached_ok=False)
        for n,title in enumerate(mw_author_titles):
            print(f"{n}/{len(mw_author_titles)} {title=}")
            family_name = title.split()[-1]
            given_name = ' '.join(title.split()[:-1])
            display_name = title
            mwauthor = LegacyPage.get(mw, title)
            author_articles[display_name] = mwauthor.author_articles
        return author_articles

    @staticmethod
    def alt_names(filename='/opt/encyc-tng/data/author-alts.txt'):
        """Read file of alternative author names and return a dict
        Document is formatted:
        Odo,F:                 Odo,Franklin
        Odo,F.:                Odo,Franklin
        """
        alts = {}
        with Path(filename).open('r') as f:
            lines = f.readlines()
        alts = {}
        for line in lines:
            if not line[0] == '#':
                alt_name,canonical_name = line.strip().split(':')
                alt_name = alt_name.strip()
                canonical_name = canonical_name.strip()
                alts[alt_name] = canonical_name
        return alts


# sources --------------------------------------------------------------

# We will not import Primary Sources as first-class objects with all their
# fields, to be linked to Articles.
# Rather we will
# - Import images, PDFs, videos, transcripts as Wagtail Image, Document,
#   and (wagtailmedia) Media files,
# - Separately download Primary Source metadata from the PSMS API,
# - And then while creating the Article, make StreamField blocks from the
#   sources.  Blocks point to the Image, Document, Media files by their `id`s.

class Sources():
    """
    # download image files, documents, videos for a page
    destination_dir = '/opt/encyc-tail/data/sources'
    from pathlib import Path; import httpx
    def download(source, destination_dir):
        for key in ['original_path', 'display_path', 'transcript']:
            if source.get(key):
                filename = Path(source[key]).name
                dest_dir = Path(destination_dir)
                dest_path = dest_dir / filename
                url = f"https://encyclopedia.densho.org/media/encyc-psms/{filename}"
                print(f"{url} -> {dest_path}")
                r = httpx.get(url, timeout=30)
                with dest_path.open('wb') as f:
                    f.write(r.content)

    for source in sources['Manzanar']:
        download(source, destination_dir)

    # Import image/document/video files and create Wagtail Image, Document, and Media objects

    titles = ['Manzanar', 'Manzanar Free Press (newspaper)']
    jsonl_path = '/opt/encyc-tail/data/densho-psms-sources-20240617.jsonl'
    src_dir = '/opt/encyc-tail/data/sources'
    from wagtail.models.collections import Collection
    from encyclopedia.migration import Sources
    collection = Collection.objects.get(name=ARTICLES_IMAGE_COLLECTION)
    sources = Sources.load_psms_sources_jsonl(jsonl_path)
    for title in titles:
        for source in sources[title]:
            Sources.import_file(source, src_dir, collection)

    """

    @staticmethod
    def import_sources(psms_sources, sources_dir):
        """Import files from sources_dir using metadata from psms_sources JSONL file

        #psms_sources = Sources.load_psms_sources_api()
        psms_sources = Sources.load_psms_sources_jsonl('/opt/encyc-tail/data/sources/sources-all-20240617.jsonl')
        Sources.import_sources(psms_sources, sources_dir=Path('/opt/encyc-tail/data/sources/'))
        """
        # https://www.yellowduck.be/posts/programatically-importing-images-wagtail
        # https://stackoverflow.com/questions/63181320/bulk-uploading-and-creating-pages-with-images-in-wagtail-migration
        print(f"{len(psms_sources)=}")
        # PSMS images attached to a collection
        collection = Collection.objects.get(name=ARTICLES_IMAGE_COLLECTION)
        print(f"{collection=}")
        num = len(psms_sources)
        for article,sources in psms_sources.items():
            for source in sources:
                print(f"{article } - {source['media_format']} {source['encyclopedia_id']}")
                Sources.import_file(source, sources_dir, collection=collection)

    @staticmethod
    def import_file(source, sources_dir, collection):
        """
        """
        src_dir = Path(sources_dir)
        if source['media_format'] == 'image':
            image = Sources.get_image(collection, src_dir / Path(source['original_path']).name)
            image.save()
            #print(f"{image=}")
        elif source['media_format'] == 'document':
            doc = Sources.get_document(collection, src_dir / Path(source['original_path']).name)
            doc.save()
            #print(f"{doc=}")
            display = Sources.get_image(collection, src_dir / Path(source['display_path']).name)
            display.save()
            #print(f"{display=}")
        elif source['media_format'] == 'video':
            display = Sources.get_image(collection, src_dir / Path(source['display_path']).name)
            display.save()
            #print(f"{display=}")
            media = Sources.get_media(
                collection,
                src_dir / Path(source['original_path']).name,
                src_dir / Path(source['display_path']).name
            )
            media.save()
            #print(f"{media=}")
            transcript = Sources.get_document(collection, src_dir / Path(source['transcript']).name)
            transcript.save()
            #print(f"{transcript=}")

    @staticmethod
    def reset():
        """TODO Delete all primary source objects
        """
        collection = Collection.objects.get(name=ARTICLES_IMAGE_COLLECTION)
        for mediatype in [Image, Document, Media]:
            for item in mediatype.objects.filter(collection=collection):
                item.delete()

    @staticmethod
    def load_psms_sources_api():
        """Load from PSMS - DOES NOT WORK OUTSIDE COLO!
        config.SOURCES_API
        config.SOURCES_API_USERNAME
        config.SOURCES_API_PASSWORD
        config.SOURCES_API_HTUSER
        config.SOURCES_API_HTPASS
        """
        return Sources.sources_by_headword(Proxy.sources_all())

    @staticmethod
    def load_psms_sources_jsonl(jsonl_path):
        """Load Sources from JSONL dump

    jsonl_path = '/opt/encyc-tail/data/densho-psms-sources-20240617.jsonl'
    from encyclopedia.migration import load_psms_sources_jsonl
    sources = load_psms_sources_jsonl(jsonl_path)

        """
        with Path(jsonl_path).open('r') as f:
            # make a list first
            return Sources.sources_by_headword(
                [json.loads(line) for line in f.readlines()]
            )

    @staticmethod
    def sources_by_headword(sources_list):
        sources_list = Sources.discard_fields(sources_list)
        # make dict of empty lists for each title
        sources = {source['headword']: [] for source in sources_list}
        # fill up those lists
        for source in sources_list:
            sources[source['headword']].append(source)
        return sources

    DISCARD_FIELDS = [
        'created', 'modified', 'aspect_ratio',
        'original', 'original_size', 'original_url', 'original_path_abs',
        'display', 'display_size', 'display_url', 'display_path_abs',
    ]
    @staticmethod
    def discard_fields(sources):
        for source in sources:
            for field in Sources.DISCARD_FIELDS:
                source.pop(field)
        return sources

    @staticmethod
    def save_psms_sources_jsonl(sources, json_path):
        """Dump Sources to JSONL
        """
        lines = [json.dumps(source) for source in sources]
        with open(json_path, 'w') as f:
            f.write('\n'.join(lines))

    @staticmethod
    def source_keys_by_filename(sources, collection):
        """Map source images to their format and wagtail..Image ID

from pathlib import Path
from wagtail.documents.models import Document
from wagtail.images.models import Image
from wagtailmedia.models import Media
from wagtail.models.collections import Collection
from encyclopedia.migration import Sources
jsonl_path = '/opt/encyc-tail/data/densho-psms-sources-20240617.jsonl'
sources_by_headword = Sources.load_psms_sources_jsonl(jsonl_path)
collection = Collection.objects.get(name=ARTICLES_IMAGE_COLLECTION)
source_pks_by_filename = Sources.source_keys_by_filename(sources_by_headword['Manzanar'], collection)
        """
        return {
            'image':    {x.title: x.id for x in Image.objects.filter(   collection=collection)},
            'document': {x.title: x.id for x in Document.objects.filter(collection=collection)},
            'video':    {x.title: x.id for x in Media.objects.filter(   collection=collection)},
        }

    @staticmethod
    def prep_test_data():
        """Prepare test data with binary files; run on packrat
        """
        sources_dir = Path('/tmp/sources')
        json_path = sources_dir / 'sources-all-20240617.jsonl'
        sources_dir.mkdir(parents=True)
        with json_path.open('r') as f:
            sources = [json.loads(line) for line in f.readlines()][:100]
        for source in sources:
            src = Path(source['original_path_abs'])
            if src.exists():
                dst = sources_dir / src.name
                shutil.copy(src,dst)

    @staticmethod
    def get_image(collection, path):
        """Get new or existing wagtail.images.models.Image"""
        try:                               # existing
            return Image.objects.get(collection=collection, title=path.name)
        except Image.DoesNotExist as err:  # new
            f = ImageFile(path.open('rb'), name=path.name)  # django..ImageFile
            return Image(collection=collection, file=f, title=path.name)
        except Image.MultipleObjectsReturned as err:
            print(f"Image.objects.get(collection={collection}, title={path.name})")
            print(err); sys.exit(1)

    @staticmethod
    def get_document(collection, path):
        """Get new or existing wagtail.documents.models.Document"""
        try:                               # existing
            return Document.objects.get(collection=collection, title=path.name)
        except Document.DoesNotExist as err:  # new
            f = File(path.open('rb'), name=path.name)  # django..File
            return Document(collection=collection, file=f, title=path.name)
        except Document.MultipleObjectsReturned as err:
            print(f"Document.objects.get(collection={collection}, title={path.name})")
            print(err); sys.exit(1)

    @staticmethod
    def get_media(collection, original_path, display_path):
        """Get new or existing wagtailmedia.models.Media"""
        try:                               # existing
            media = Media.objects.get(collection=collection, title=original_path.name)
        except Media.DoesNotExist as err:  # new
            media = Media(
                collection=collection,
                file=File(original_path.open('rb'), name=original_path.name),  # django..File
                thumbnail=File(display_path.open('rb'), name=display_path.name),  # django..File
                title=original_path.name,
            )
        except Media.MultipleObjectsReturned as err:
            print(f"Media.objects.get(collection={collection}, title={original_path.name})")
            print(err); sys.exit(1)
        #if display:
        #    media.thumbnail = display
        media.type = 'video'
        media.width,media.height,media.duration = Sources._ffmpeg_media_info(original_path)
        return media

    @staticmethod
    def _ffmpeg_media_info(path):
        cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=width,height,duration', '-of', 'json', path]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out,err = p.communicate()
        data = json.loads(out)
        return (
            data['streams'][0]['width'],
            data['streams'][0]['height'],
            data['streams'][0]['duration'],
        )


# articles -------------------------------------------------------------

class PageIsRedirectException(Exception):
    pass

class UnhandledTagException(Exception):
    pass

class UnknownAuthorException(Exception):
    pass

TEST_ARTICLES = [
    'Barbed Wire Baseball (book)',       # Resource Guide ONLY
    'Kotonk',                            # just an article
    'A Grain of Sand (album)',           # databox-album
    'Common Ground (magazine)',          # databox-magazine
    'Conscience and the Constitution (film)', # databox-film
    'Farewell to Manzanar (book)',       # databox-book
    "Fighting for Tomorrow: Japanese Americans in America's Wars (exhibition)", # databox-exhibition
    'Fred Korematsu',                    # databox-person
    "The Hawai'i Nisei Story (website)", # databox-website
    'Manzanar',                          # databox-camp
    'Manzanar Free Press (newspaper)',   # databox-newspaper
    'Success Story, Japanese American Style (article)', # databox-article
    'Tondemonai-Never Happen! (play)',   # databox-play
]

class Articles():

    @staticmethod
    def import_articles(titles=[], dryrun=False):
        """

url_prefix = '/wiki/'
title = 'Manzanar'; slug = 'manzanar'
#title = 'Ruth Asawa'; slug = 'ruth-asawa'
jsonl_path = '/opt/encyc-tail/data/densho-psms-sources-20240617.jsonl'

from wagtail.models.collections import Collection
from encyc.models.legacy import Page as LegacyPage
from encyc import wiki
from editors.models import Author
from encyclopedia.migration import Authors, Sources, Articles
from encyclopedia.models import load_mediawiki_titles

authors_by_names = {f"{author.family_name},{author.given_name}": author for author in Author.objects.all()}

sources_by_headword = Sources.load_psms_sources_jsonl(jsonl_path)
sources_collection = Collection.objects.get(name=ARTICLES_IMAGE_COLLECTION)
source_pks_by_filename = Sources.source_keys_by_filename(
    sources_by_headword, sources_collection
)

index_page = Articles.wagtail_index_page()

mw = wiki.MediaWiki()
mw_titles = Articles.load_mwtitles(mw)

mwpage,mwtext = Articles.load_mwpage(mw, title)

Articles.import_article(mw, mwpage, mwtext, mw_titles, url_prefix, authors_by_names, sources_collection, sources_by_headword, index_page)


article_blocks = Articles.mwtext_to_streamblocks(mw, mwtext, mw_titles, url_prefix)

sources_blocks = Articles.streamfield_media_blocks(
    mwpage.title,
    sources_by_headword,
    migration.source_keys_by_filename(
        sources_by_headword[mwpage.title],
        sources_collection
    )
)

import json
from encyc.models.legacy import wikipage
mw_databoxes = wikipage.extract_databoxes(mwpage.body, databox_divs_namespaces=None)


#mwpage,mwtext = Articles.load_mwpages(title)
#mwtext_cleaned = Articles.clean_mediawiki_text(mwtext)
#mwhtml = Articles.render_mediawiki_text(mw, mwtext_cleaned, mw_titles, url_prefix)
#streamfield_blocks = Articles.html_to_streamfield(mwhtml)
#merged_blocks = Articles.merge_streamfield_blocks(streamfield_blocks)

with open(f"/tmp/{slug}-01-mwtext", 'w') as f:
    f.write(mwtext)

with open(f"/tmp/{slug}-02-mwtextcleaned", 'w') as f:
    f.write(mwtext_cleaned)

with open(f"/tmp/{slug}-03-mwhtml.html", 'w') as f:
    f.write(mwhtml)

with open(f"/tmp/{slug}-04-streamfield", 'w') as f:
    f.write(streamfield_blocks)

        """
        logger.info(f"Articles.import_articles(titles={titles}, dryrun={dryrun})")
    #    for mwpage in load_mw_articles():
    #        wagtail_import_article(mwpage, index_page)
    #    # resource guide page?
    #    if mwpage.published_rg:
        url_prefix = '/wiki/'
        jsonl_path = '/opt/encyc-tail/data/densho-psms-sources-20240617.jsonl'
        logger.info(f"{jsonl_path=}")

        authors_by_names = {
            f"{author.family_name},{author.given_name}": author
            for author in Author.objects.all()
        }
        authors_alts = Authors.alt_names(filename='/opt/encyc-tng/data/author-alts.txt')

        sources_by_headword = Sources.load_psms_sources_jsonl(jsonl_path)
        sources_collection = Collection.objects.get(name=ARTICLES_IMAGE_COLLECTION)
        source_pks_by_filename = Sources.source_keys_by_filename(
            sources_by_headword, sources_collection
        )
        logger.info(f"{len(sources_by_headword.keys())=}")
        logger.info(f"{sources_collection=}")

        index_page = Articles.wagtail_index_page()
        logger.info(f"{index_page=}")

        mw = wiki.MediaWiki()
        logger.info(f"{mw=}")
        mw_titles = Articles.load_mwtitles(mw)
        if not titles:
            titles = mw_titles
        mw_titles_slugs = Articles.load_mwtitles_to_slugs(mw)

        logger.info('')
        errors = []
        num = len(titles)
        start = datetime.now()
        for n,title in enumerate(titles):
            print(f"{n+1}/{num} {title=}")
            mwpage,mwtext = Articles.load_mwpage(mw, title)
            logger.info('importing...')
            try:
                article = Articles.import_article(
                    mw, mwpage, mwtext,
                    mw_titles, mw_titles_slugs, url_prefix,
                    authors_by_names, authors_alts,
                    sources_collection, sources_by_headword,
                    index_page,
                    dryrun=dryrun,
                )
                logger.info(f"ok")
                logger.debug(f"{datetime.now() - start} {n+1}/{num} ok | {title}\n")
            except PageIsRedirectException as err:
                logger.info(f"PageIsRedirectException: {mwpage.title}\n")
                continue
            except UnknownAuthorException as err:
                logger.error(f"UnknownAuthorException: {mwpage.title} : {err}\n")
            except UnhandledTagException as err:
                logger.error(f"UnhandledTagException: {mwpage.title} : {err}\n")
            except NotNullViolation as err:
                logger.error(f"NotNullViolation: {mwpage.title} : {err}\n")
            except IntegrityError as err:
                logger.error(f"IntegrityError: {mwpage.title} : {err}\n")
            except Exception as err:
                errors.append(title)
                logger.error(f"{datetime.now() - start} {n+1}/{num} ERR {err} | \"{title}\"\n")
                logger.error(traceback.format_exc())
            logger.info('')
        logger.info(f"{len(errors)} ERRORS - - - - - - - - - - - - - - - - - -")
        for title in errors:
            logger.info(title)
        logger.info(f"{len(errors) / len(titles)} percent")

    @staticmethod
    def wagtail_index_page(title=ARTICLES_INDEX_PAGE):
        return ArticlesIndexPage.objects.get(title=title)

    """
ENCYCFRONT ARTICLE STRUCTURE
BODY
(published)
(databox)
description
(toc)
+ header, paragraph(s), blockquote, authoredby, moreinfo, ?
(reflist/footnotes)
(category)
    """

    # Constructing a new Wagtail Article

    # Modifying StreamField data
    # https://docs.wagtail.org/en/stable/topics/streamfield.html#modifying-streamfield-data

    @staticmethod
    def import_article(mw, mwpage, mwtext, mw_titles, mw_titles_slugs, url_prefix, authors_by_names, authors_alts, sources_collection, sources_by_headword, index_page, dryrun=False):
        # resource guide page?
        if Articles.is_author(mwpage, mw):
            logger.info('AUTHOR PAGE - SKIPPING')
            return
        if Articles.is_resourceguide_only(mwpage):
            logger.info('RESOURCE-GUIDE-ONLY PAGE - SKIPPING')
            return

        article_class,databox,databox_name = Articles.article_type(mwpage)
        logger.info(f"{article_class=}")
        try:
            article = article_class.objects.get(title=title)
            article_is_new = False
        except:
            article = article_class(
                title=mwpage.title,
                body='',
            )
            article_is_new = True
        logger.info(f"{article=}")

        Articles.set_databox_fields(article, databox, databox_name)

        #article.lastmod = mwpage.lastmod

        authors = []
        if mwpage.authors and mwpage.authors.get('parsed'):
            for family_name,given_name in mwpage.authors['parsed']:
                try:
                    author = authors_by_names[f"{family_name},{given_name}"]
                    authors.append(author)
                except KeyError as err:
                    try:
                        author = authors_by_names[
                            authors_alts[f"{family_name},{given_name}"]
                        ]
                        authors.append(author)
                    except KeyError as err:
                        raise UnknownAuthorException(err)
        # authors will be saved for later
        # article must have a primary key before authors can be added

        for tag in mwpage.categories:
            article.tags.add(tag.lower())
     
        sources_blocks = Articles.streamfield_media_blocks(
            mwpage.title,
            sources_by_headword,
            Sources.source_keys_by_filename(
                sources_by_headword.get(mwpage.title,[]),
                sources_collection
            )
        )
        article.description = mwpage.description
        logger.info(f"{article.description=}")
        article_blocks = Articles.mwtext_to_streamblocks(
            mw, mwtext, mw_titles_slugs, url_prefix
        )
        logger.info(f"{len(article_blocks)=}")

        article.body = json.dumps(
            sources_blocks + article_blocks
        )
        Footnotary.update_footnotes(article, fields=None, request=None, save=False)

        if article_is_new and not dryrun:
            # place page under encyclopedia index
            logger.info(f"{index_page}.add_child(instance={article})")
            result = index_page.add_child(instance=article)

        if not dryrun:
            for author in authors:
                article.authors.add(author)
            article.save_revision().publish()

    @staticmethod
    def reset():
        """TODO Delete all encyclopedia.models.Article objects incl revisions"""
        index_page = Articles.wagtail_index_page()
        for item in index_page.children():
            item.delete()

    @staticmethod
    def load_mwtitles(mw):
        """Returns list of MediaWiki titles
        """
        key = 'encyctng:migration:mwtitles-all'
        cached = cache.get(key)
        if not cached:
            titles = [page.page_title for page in mw.mw.allpages()]
            cached = titles
            cache.set(key, cached, settings.CACHE_TIMEOUT_LONG)
        return cached

    @staticmethod
    def load_mwtitles_to_slugs(mw):
        """Returns dict of MediaWiki titles and url_titles to slugified titles
        """
        key = 'encyctng:migration:mwtitles-slugs'
        cached = cache.get(key)
        if not cached:
            allpages = [page for page in mw.mw.allpages()]
            titles = {page.normalize_title(page.page_title): slugify(page.page_title) for page in allpages}
            for page in allpages:
                titles[page.page_title] = slugify(page.page_title)
            cached = titles
            cache.set(key, cached, settings.CACHE_TIMEOUT_LONG)
        return cached

    @staticmethod
    def load_mwpage(mw, title):
        key = f"encyctng:migration:mwtitle:{slugify(title).replace('-','')}"
        cached = cache.get(key)
        if not cached:
            mwtext = mw.mw.pages[title].text()
            cached = mwtext
            cache.set(key, cached, settings.CACHE_TIMEOUT_LONG)
        # can't cache this bc contains Python objects
        mwpage = LegacyPage.get(mw,title)
        return mwpage,cached

    @staticmethod
    def load_mwpages(title: str=None, verbose: bool=False) -> list[str]:
        """Load one or all articles from encyclopedia editors' mediawiki
        mwpage,mwtext = load_mwpages('Ruth Asawa')
        """
        mw = wiki.MediaWiki()
        logger.debug(f"{mw=} {mw.mw.host=}")
        if title:
            return Articles.load_mwpage(mw,title)
        mw_articles = [d['title'] for d in Proxy.articles_lastmod(mw)]
        logger.debug(f"{len(mw_articles)=}")
        mwpages = []
        num = len(mw_articles)
        for n,title in enumerate(mw_articles[:10]):
            logger.debug(f"{n}/{num} {title}")
            mwpages.append( Articles.load_mwpage(mw,title) )
        return mwpages

    @staticmethod
    def mw_articles_lastmod(mw):
        key = f"encyctng:migration:mwarticleslastmod"
        cached = cache.get(key)
        if not cached:
            mw_articles = [d['title'] for d in Proxy.articles_lastmod(mw)]
            cached = mw_articles
            cache.set(key, cached, settings.CACHE_TIMEOUT_LONG)
        return cached

    @staticmethod
    def is_author(mwpage, mw):
        """Page is an author page
        """
        if mwpage.title in Authors.mw_author_titles(mw):
            return True
        return False

    @staticmethod
    def is_encyclopedia_only(mwpage):
        """Page is published in Encyclopedia but NOT in Resource Guide
        """
        if mwpage.published_encyc and not mwpage.published_rg:
            return True
        return False

    @staticmethod
    def is_resourceguide_only(mwpage):
        """Page is published in Resource Guide but NOT in Encyclopedia
        """
        if mwpage.published_rg and not mwpage.published_encyc:
            return True
        return False

    @staticmethod
    def article_type(mwpage):
        """Returns Article class (or subclass) and databox if present
        """
        mw_databoxes = wikipage.extract_databoxes(mwpage.body)
        # Resouce Guide databox
        # Encyclopedia migration ignores RG-only pages and content
        if 'rgdatabox-Core' in mw_databoxes.keys():
            rgdatabox = mw_databoxes.pop('rgdatabox-Core')
            logger.info(f"{rgdatabox=}")
        if mw_databoxes:
            if len(mw_databoxes.keys()) > 1:
                raise Exception(
                    f"Article has more than one databox: {mw_databoxes.keys()}"
                )
            databox_name = [key for key in mw_databoxes.keys()][0]
            databox = mw_databoxes[databox_name]
            article_class_name = databoxes.DATABOXES[databox_name]['class']
        else:
            databox_name = None
            databox = None
            article_class_name = 'Article'
        article_class = getattr(encyclopedia_models, article_class_name)
        return article_class,databox,databox_name

    @staticmethod
    def set_databox_fields(article, databox=None, databox_name=None):
        """Set fields from databox
        """
        if databox:
            for item in databoxes.DATABOXES[databox_name]['fields']:
                mw_field = item['mw'].lower()
                tng_field = item['tng']
                value = None
                if databox.get(mw_field):
                    value = databox[mw_field][0]
                if value:
                    setattr(article, tng_field, value)

    @staticmethod
    def mwtext_to_streamblocks(mw, mwtext: str, mw_titles_slugs, url_prefix) -> list[str]:
        mwtext_cleaned = Articles.clean_mediawiki_text(mwtext)
        mwhtml = Articles.render_mediawiki_text(mw, mwtext_cleaned, mw_titles_slugs, url_prefix)
        streamfield_blocks = Articles.html_to_streamfield(mwhtml)
        merged_blocks = Articles.merge_streamfield_blocks(streamfield_blocks)
        return merged_blocks

    @staticmethod
    def clean_mediawiki_text(mw_txt: str) -> str:
        """Remove tags from Mediawiki *source* text, leaving footnote <refs>
        """
        REMOVE_FROM_MEDIAWIKI_SOURCE = [
            # remove everything but headers, wiki links, <refs>
            re.compile(r"{{\s*Published\s*}}"),
            re.compile(r"{{\s*LegacyArticleNotice[a-zA-Z=|<!-> \n]*}}"),
            re.compile(r"{{\s*Databox[a-zA-Z .:;=<!->\[\]|\n]*}}"),
            re.compile(r"\[\[\s*File[a-zA-Z0-9 -_.:|]*\]\]"),
            re.compile(r"==\s*Footnotes\s*=="),
            re.compile(r"{{\s*Reflist\s*}}"),
            re.compile(r"\[\[\s*Category[a-zA-z :]*\]\]"),
            re.compile(r"{{\s*DEFAULTSORT[a-zA-z :]*}}"),
        ]
        for pattern in REMOVE_FROM_MEDIAWIKI_SOURCE:
            mw_txt = pattern.sub('', mw_txt)
        while('\n\n\n' in mw_txt):
            mw_txt = mw_txt.replace('\n\n\n', '\n\n')
        return mw_txt.strip()

    @staticmethod
    def render_mediawiki_text(mw, mwtext: str, mw_titles_slugs, url_prefix) -> str:
        """Render Mediawiki source text to HTML
        Before parsing, hide <ref> tags used for footnotes because needed later.
        """
        # hide footnotes from the mediawiki parser
        # at the same time, remove the <ref name> attribute e.g. <ref name="ftnt_ref5">
        mwtext = re.sub(r"<ref[a-zA-Z0-9 _=\"]*>", '<BLAT>', mwtext).replace('</ref>', '</BLAT>')
        # parse text to html
        html = mw.mw.parse(text=mwtext)['text']['*']
        # Restore footnote <ref> tags, but as character entity references (&lt;/ref&gt;).
        # This way they are visible in the UI but are hidden from Wagtail's
        # RichTextBlock editor and parser.
        html = html.replace('&lt;/BLAT&gt;', '&lt;/ref&gt;').replace('&lt;BLAT&gt;', '&lt;ref&gt;')
        # Remove the extra crud that MediaWiki adds
        soup = BeautifulSoup(html, features='html5lib')
        soup = Articles.strip_resourceguide_html(soup)
        # die if this is a redirect
        for tag in soup.find_all('div', class_='redirectMsg'):
            link_txt = tag.find_all('a')[0].contents[0]
            raise PageIsRedirectException(f'Redirect to "{link_txt}"')
        # remove the <div class="mw-parser-output"> wrapper
        for tag in soup.find_all(class_="mw-parser-output"):
            tag.unwrap()
        # mediawiki-generated table of contents
        for tag in soup.find_all(class_='toc'):
            tag.extract()
        # edit links
        for tag in soup.find_all(class_='mw-editsection'):
            tag.extract()
        # extra <spans> inside <hN> tags
        for hN in ['h1', 'h2', 'h3', 'h4']:
            for h in soup.find_all(hN):
                span = h.find(class_='mw-headline')
                # header contents may contain tags like <i> - convert these to str
                contents = ''.join([str(element) for element in span.contents])
                header = contents.strip()
                span.insert_before(header)
                span.extract()
        # Mediawiki-generated comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        # remove empty whitespace chunks i.e. '\n\n\n'
        for chunk in soup.body.contents:
            if type(chunk) == NavigableString and chunk.strip() in ['',None]:
                chunk.extract()
        # rewrite MediaWiki internal URLs to Wagtail slug URLs
        # example: "/wiki/Manzanar_Free_Press_(newspaper)" -> "/wiki/manzanar-free-press-newspaper"
        soup,notmatched = Articles.rewrite_internal_urls(soup, mw_titles_slugs, url_prefix)
        # remove any remaining databox divs
        for tag in soup.find_all('div'):
            if tag and tag.get('id') and ('databox-' in tag['id']):
                tag.unwrap()
        return str(soup)

    @staticmethod
    def strip_resourceguide_html(soup):
        """Strip out ResourceGuide databox from HTML
        """
        # .rgonly / rgdatabox-CoreDisplay
        for tag in soup.find_all(class_='rgonly'):
            tag.unwrap()
        for tag in soup.find_all(id='rgdatabox-Core'):
            tag.unwrap()
        for tag in soup.find_all(id='rgdatabox-CoreDisplay'):
            tag.unwrap()
        # infobox
        for tag in soup.find_all(class_='infobox'):
            tag.unwrap()
        return soup

    @staticmethod
    def rewrite_internal_urls(soup, mw_titles_slugs, url_prefix):
        """Rewrite MediaWiki internal URLs to Wagtail slug URLs
     
        example: "/wiki/Manzanar_Free_Press_(newspaper)" -> "/wiki/manzanar-free-press-newspaper"
        """
        notmatched = []
        for tag in [
            tag for tag in soup.find_all('a') if tag['href'].find(url_prefix) == 0
        ]:
            # url_prefix must include preceding AND following slashes e.g. "/wiki/"
            title = tag['href'].replace(url_prefix, '')
            if mw_titles_slugs.get(title):
                tag['href'] = f"{url_prefix}{mw_titles_slugs[title]}"
            else:
                notmatched.append(tag)
        return soup,notmatched

    @staticmethod
    def html_to_streamfield(html: str, debug: bool=False) -> list[str]:
        """Convert HTML into list of StreamField (role,html) tuples
     
        Role is one of ['heading', 'paragraph', 'embed', 'quote', ...]
        (see encyclopedia.models.Article.body)
        """
        # map HTML tags to Streamfield roles
        HEADERS = ['h1', 'h2', 'h3', 'h4']
        TAGS_TO_ROLES = {
            'h1': 'heading',
            'h2': 'heading',
            'h3': 'heading',
            'h4': 'heading',
            'p':  'paragraph',
        }
        KNOWN_TAGS = TAGS_TO_ROLES.keys()
        soup = BeautifulSoup(html, features='html5lib')
        blocks = []
        for tag in soup.body.contents:
            logger.debug(f"{tag=}")
            if type(tag) == NavigableString:
                continue
            if tag.name in ['blockquote', 'i', 'li', 'pre', 'ul']:
                continue
            # TODO what to do with <div id="authorByline">?
            if tag.name == 'div' and tag.has_attr('id') and tag['id'] == 'authorByline':
                continue
            # TODO what to do with <div id="citationAuthor">?
            if tag.name == 'div' and tag.has_attr('id') and tag['id'] == 'citationAuthor':
                continue
            if tag.name == 'p':
                block = {
                    'type': 'paragraph',
                    'value': str(tag).strip()
                }
            elif tag.name in HEADERS:
                # many headers still contain a <span id="Header Text"></span> tag
                heading_text = str(tag.contents[-1])
                block = {
                    'type': 'heading',
                    'value': {
                        'size': tag.name,
                        'heading_text': heading_text,
                    }
                }
            else:
                raise UnhandledTagException(f"UnhandledTagException: Don't know what to do with \"{tag}\"")
            logger.debug(f"{block=}")
            blocks.append(block)
        return blocks

    @staticmethod
    def merge_streamfield_blocks(blocks: list[str]) -> list[str]:
        """Merge certain successive streamfield blocks (paragraphs)
     
        blocks = [
            {'type':'heading','value':{'heading_text':'1','size':'h2'}}, {'type':'heading','value':{'heading_text':'2','size':'h2'}},
            {'type':'paragraph','value':'<p>1'},
            {'type':'heading','value':{'heading_text':'3','size':'h2'}},
            {'type':'paragraph','value':'<p>2'}, {'type':'paragraph','value':'<p>3'}, {'type':'paragraph','value':'<p>4'},
            {'type':'heading','value':{'heading_text':'4','size':'h2'}},
            {'type':'paragraph','value':'<p>5'}, {'type':'paragraph','value':'<p>6'},
        ]
        merge_streamfield_blocks(blocks)
        """
        MERGE_THESE = ['paragraph']
        newblocks = []
        for block in blocks:
            if len(newblocks) == 0:
                newblocks.append(block)
                continue
            prevblock = newblocks[-1]
            if (block['type'] == prevblock['type']) and (block['type'] in MERGE_THESE):
                prevblock['value'] = f"{prevblock['value']}\n{block['value']}"
                newblocks[-1] = prevblock
            else:
                newblocks.append(block)
        return newblocks

    @staticmethod
    def streamfield_media_blocks(title, sources_by_headword, source_pks_by_filename):
        """Consume primary source data from a page and product DDRObjectBlock data
     
        Block format:
        ('BLOCKTYPE', {'type':'BLOCKTYPE', 'value': {'FIELD1':VALUE1, ...}})
        """
        blocks = []
        for source in sources_by_headword.get(title,[]):
            if source['media_format'] == 'image':
                blocks.append(
                    ImageBlock.block_from_source(source, source_pks_by_filename)
                )
            elif source['media_format'] == 'video':
                blocks.append(
                    VideoBlock.block_from_source(source, source_pks_by_filename)
                )
            elif source['media_format'] == 'document':
                blocks.append(
                    DocumentBlock.block_from_source(source, source_pks_by_filename)
                )
            else:
                raise Exception(
                    f"Don't recognize media_format '{source['media_format']}!"
                )
        return blocks


def ddrobject_block(source):
    """Take a source from mwpage.sources and return a StreamField block
    """
    encyclopedia_id = source['encyclopedia_id']
    densho_id = source['densho_id']
    data = {
        'type': 'ddrobject',
        'value': {
            'identifier': densho_id,
            'caption': source['caption'],
            'caption_extended': source['caption_extended'],
        }
    }
    return ('ddrobject', data)

def is_ddr_object(source):
    densho_id = source.get('densho_id', None)
    assert densho_id
    assert densho_id.find('-') != -1
    chunks = densho_id.split('-')
    assert chunks[0] == 'ddr'    # repo
    assert chunks[1].isalpha()   # org
    assert chunks[2].isnumeric() # collection id
    assert len(chunks) > 3
    assert chunks[3].isnumeric() # object id
    return True

"""
is_ddr_object({'densho_id': 'denshopd-i67-00075'})                        # NO
is_ddr_object({'densho_id': 'denshovh-hnorman-01-0017'})                  # NO
is_ddr_object({'densho_id': 'en-densho-miho-1-1'})                        # NO
is_ddr_object({'densho_id': 'sos_24-san-1'})                              # NO
is_ddr_object({'densho_id': 'ddr-densho-93'})                             # NO
is_ddr_object({'densho_id': 'ddr-densho-93-23'})                          # YES
is_ddr_object({'densho_id': 'ddr-densho-93-23-1'})                        # YES
is_ddr_object({'densho_id': 'ddr-densho-93-23-1-mezzanine-a1b2c3d4e5f6'}) # YES
"""



def _clean_mw_body(html):
    """Strip extra tags out of article body

import mwparserfromhell
wikicode = mwparserfromhell.parse(text)

import wikitextparser as wtp
with open('/opt/encyc-tail/Manzanar_source.txt','r') as f:
    parsed = wtp.parse(f.read())
pretty = parsed.pformat()
# normalizes wikitext format (easier parsing?)
with open('/opt/encyc-tail/Manzanar_pformatted.txt','w') as f:
    f.write(parsed.pformat())

with open('/opt/encyc-tail/Manzanar_pformatted.txt','r') as f:
    parsed = wtp.parse(f.read())


    """
    # OBSOLETE - works on *parsed* html, footnotes already converted
    #from bs4 import BeautifulSoup
    #soup = BeautifulSoup('html', features='html5lib')
    ## MW images
    #for tag in soup.find_all(class_='floatright'):
    #    tag.extract()
    ## Contents
    #for tag in soup.find_all(class_='toc'):
    #    tag.extract()
    ## Extract content from div.section
    #for section in soup.find_all(class_='section'):
    #    section.unwrap()
    ## Remove span.mw-headline from h2
    #for h2 in soup.find_all('h2'):
    #    span = h2.find(class_='mw-headline')
    #    header = span.contents[0].strip()
    #    span.insert_before(header)
    #    span.extract()
    ## Extract content from div.section-content
    #for section_content in soup.find_all(class_='section_content'):
    #    section_content.unwrap()
    pass

def _mw_databox(mw_page):
    databoxcamp = DataboxCampBlock(
        sos_uid                 = "w-mini",
        densho_name             = "Minidoka",
        usg_name                = "Minidoka Relocation Center",
        facility_type_url       = "https://editors.densho.org/wiki/Sites_of_incarceration#Concentration_Camp",
        facility_type           = "Concentration Camp",
        admin_agency            = "War Relocation Authority",
        date_opened             = "August 10, 1942",
        date_closed             = "October 28, 1945",
        location_name           = "Hunt, Idaho",
        city_name               = "Hunt",
        state_name              = "ID",
        gis_lat                 = "42.6667",
        gis_long                = "-114.2333",
        gis_tgn_id              = "2025735",
        description             = "Located at 4,000 feet of elevation on uneven terrain in southern Idaho, Minidoka is in the Snake River Plain of Jerome County, 15 miles east of Jerome and 15 miles north of Twin Falls. The 33,000 acres of arid desert was dominated by sagebrush; the southern boundary of the camp was formed by the man-made North Side canal.",
        current_disposition     = "",
        population_description  = "Held people from Washington, Oregon, and Alaska; in 1943 many of the incarcerees from Bainbridge Island, Washington, were transferred at their own request to Minidoka from Manzanar.",
        exit_destination        = "",
        peak_population         = "9,397",
        peak_date               = "1943-03-01",
        nps_link                = "http://www.nps.gov/miin/",
        official_link           = "",
    )







if __name__ == '__main__':
    encyctail()

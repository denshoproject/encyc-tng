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
import pickle
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
from wagtail.models.media import Collection
from wagtailmedia.models import Media

# encyc-core
from encyc import config
from encyc.models.legacy import Proxy
from encyc.models.legacy import Page as LegacyPage
from encyc.models.legacy import Source as LegacySource, SOURCE_FIELDS
from encyc.models.legacy import wikipage
from encyc import wiki
# encyc-tail
from encyclopedia.footnotes import Footnotary
from editors.models import Author
from encyclopedia.blocks import (
    ArticleTextBlock, EncycStreamBlock, HeadingBlock, QuoteBlock,
    ImageBlock, VideoBlock, DocumentBlock,
    DataboxCampBlock)
from encyclopedia.models import ArticlesIndexPage
from encyclopedia.models import Page, Article
from encyclopedia.models import MediawikiWagtail
from encyclopedia import models as encyclopedia_models
from encyclopedia import databoxes
from encyclopedia.topics import topics_items

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
#ARTICLES_INDEX_PAGE = 'Encyclopedia'
ARTICLES_INDEX_PAGE = 'Home'
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
    root_collection = Collection.objects.get(name='Root')
    # article images collection
    article_images_collection = Collection(name=ARTICLES_IMAGE_COLLECTION)
    root_collection.add_child(instance=article_images_collection)
    # homepage collection
    homepage_collection = Collection(name='Home page')
    root_collection.add_child(instance=homepage_collection)
    # topics collection
    topics_collection = Collection(name='Topics')
    root_collection.add_child(instance=topics_collection)
    # authors collection
    authors_collection = Collection(name='Authors')
    root_collection.add_child(instance=authors_collection)

    ## NOPE: articles will be under 'Home'
    # articles index page
    articles_index = ArticlesIndexPage(title=ARTICLES_INDEX_PAGE)
    #home_page = Page.objects.get(title='Home')
    #home_page.add_child(instance=articles_index)


# authors --------------------------------------------------------------

class Authors():

    @staticmethod
    def import_authors(basedir, debug):
        """Migrate MediaWiki author pages to editors.Author wagtail.snippets
        TODO check if author exists before creating
        """
        authors_collection = Collection.objects.get(name='Authors')
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
            image_path = Path(basedir) / f"authors/authors-{slugify(display_name)}.jpg"
            if image_path.exists():
                f = ImageFile(image_path.open('rb'), name=display_name)
                i = Image(file=f, title=display_name, collection=authors_collection)
                i.save()
                wtauthor.image = i
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
            try:
                cache.set(key, cached, settings.CACHE_TIMEOUT_LONG)
            except RecursionError:
                print(f"RecursionError: {key=}")
                pass
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
    def alt_names(filename='/opt/encyc-tng/data/authors-alts.txt'):
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

    @staticmethod
    def import_sources(psms_sources, sources_dir, dryrun=False):
        """Import files from sources_dir using metadata from psms_sources JSONL file
        """
        # https://www.yellowduck.be/posts/programatically-importing-images-wagtail
        # https://stackoverflow.com/questions/63181320/bulk-uploading-and-creating-pages-with-images-in-wagtail-migration
        print(f"{len(psms_sources)=}")
        # PSMS images attached to a collection
        collection = Collection.objects.get(name=ARTICLES_IMAGE_COLLECTION)
        print(f"{collection=}")
        errors = []
        num = len(psms_sources)
        for n,article_sources in enumerate(psms_sources.items()):
            article,sources = article_sources
            for source in sources:
                print(f"{n}/{num} {article } - {source['media_format']} {source['encyclopedia_id']}")
                result = Sources.import_file(
                    article, source, sources_dir, collection=collection, dryrun=dryrun
                )
                if result and result.get('error'):
                    errors.append(result)
        print(f"{len(errors)} errors")
        for error in errors:
            print(f"{error['error']}")
        return errors

    @staticmethod
    def import_file(article, source, sources_dir, collection, dryrun=False):
        """
        """
        src_dir = Path(sources_dir)
        if source['media_format'] == 'image':
            try:
                image = Sources.get_image(collection, src_dir / Path(source['original_path']))
                if not dryrun:
                    image.save()
                #print(f"{image=}")
            except Exception as err:
                return {'article': article, 'error': err, 'source': source}
        elif source['media_format'] == 'document':
            try:
                doc = Sources.get_document(collection, src_dir / Path(source['original_path']))
                if not dryrun:
                    doc.save()
                #print(f"{doc=}")
                display = Sources.get_image(collection, src_dir / Path(source['display_path']))
                if not dryrun:
                    display.save()
                #print(f"{display=}")
            except Exception as err:
                return {'article': article, 'error': err, 'source': source}
        elif source['media_format'] == 'video':
            try:
                display = Sources.get_image(collection, src_dir / Path(source['display_path']))
                if not dryrun:
                    display.save()
                #print(f"{display=}")
                media = Sources.get_media(
                    collection,
                    src_dir / Path(source['original_path']),
                    src_dir / Path(source['display_path'])
                )
                if not dryrun:
                    media.save()
                #print(f"{media=}")
                transcript = Sources.get_document(collection, src_dir / Path(source['transcript']))
                if not dryrun:
                    transcript.save()
                #print(f"{transcript=}")
            except Exception as err:
                return {'article': article, 'error': err, 'source': source}
        return {}

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
        return Sources.sources_by_headword(
            [source.to_dict() for source in Proxy.sources_all()]
        )

    @staticmethod
    def load_psms_sources_jsonl(jsonl_path):
        """Load Sources from JSONL dump
        """
        with Path(jsonl_path).open('r') as f:
            lines = f.readlines()
        sources = []
        # each line contains a list of sources dicts for a single article
        datas = [json.loads(line.strip()) for line in lines]
        for data in datas:
            for source in data:
                sources.append(source)
        return Sources.sources_by_headword(sources)

    @staticmethod
    def sources_by_headword(sources_list):
        sources_list = Sources.discard_fields(sources_list)
        sources = {}
        for source in sources_list:
            if not sources.get(source['headword']):
                sources[source['headword']] = []
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
                try:
                    source.pop(field)
                except KeyError:
                    pass
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


# topics ---------------------------------------------------------------

def import_topics_images(basedir):
    topics_collection = Collection.objects.get(name='Topics')
    print(f"{topics_collection=}")
    for topic in topics_items():
        tid = topic['id']
        title = topic['title']
        path = Path(basedir) / f"topics/encyctng-topics-{tid}.png"
        print(f"{path=}")
        f = ImageFile(path.open('rb'), name=title)  # django..ImageFile
        i = Image(file=f, title=title, collection=topics_collection)
        i.save()



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

SKIP_ARTICLES = [
]

class Articles():

    @staticmethod
    def download_articles(mw, basedir, titles=[]):
        """Download articles and metadata from MediaWiki
        
        TODO Handle redirects
        TODO Handle titles with apersands
        TODO Handle ValueErrors (on authors?)
        """
        basedir = Path(basedir)
        basedir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Articles.download_articles(basedir={basedir}, titles={titles}")

        alts_path = basedir / 'authors-alts.txt'
        logger.info('Downloading authors')
        authors_by_names,authors_alts = Articles.download_authors(alts_path)
        Articles.dump_authors(
            authors_by_names, authors_alts, basedir
        )

        logger.info('Downloading sources')
        sources_path = basedir / "densho-psms-sources.jsonl"
        sources_collection,sources_by_headword = Articles.download_sources(sources_path)
        Articles.dump_sources(
            sources_collection,sources_by_headword, basedir
        )
        logger.info(f"{len(sources_by_headword.keys())=}")
        logger.info(f"{sources_collection=}")

        logger.info('Downloading articles')
        url_prefix = '/wiki/'
        titles,mw_titles,mw_titles_slugs = Articles.download_mw(
            mw, url_prefix, titles=titles
        )
        Articles.dump_mw(titles, mw_titles, mw_titles_slugs, basedir)
        errors = []
        num = len(titles)
        start = datetime.now()
        for n,title in enumerate(titles):
            click.echo(f"{n+1}/{num} {title=}")
            try:
                mwpage,mwtext = Articles.load_mwpage(mw, title)
                pagedata = json.loads(mwpage.pagedata(mw, title))['parse']
                mwppath,mwtpath,pgdpath,errpath = Articles.dump_article(
                    mwpage, mwtext, pagedata, basedir
                )
            except Exception as err:
                logger.error(f"{datetime.now() - start} {n+1}/{num} ERR {err} | \"{title}\"\n")
                logger.error(traceback.format_exc())

    @staticmethod
    def import_articles(basedir, sources_jsonl, titles=[], justload=False, dryrun=False, errorquit=False, offset=0, limit=None, skip=[], errfile=''):
        """
        """
        logger.info(f"Articles.import_articles(basedir={basedir}, dryrun={dryrun})")
        basedir = Path(basedir)
        mw = wiki.MediaWiki()
        url_prefix = '/wiki/'
        authors_by_names,authors_alts, \
            sources_collection,sources_by_headword, \
            saved_titles,mw_titles,mw_titles_slugs, \
            redirects = Articles.load_articles_metadata(basedir, sources_jsonl)
        if not titles:
            titles = saved_titles
        
        logger.info(f"{mw=}")
        index_page = Articles.prep_wagtail()
        logger.info(f"{index_page=}")

        logger.info('')
        errors = []
        num = len(titles)
        start = datetime.now()
        for n,title in enumerate(titles):
            if limit and n > limit:
                logger.info('LIMIT')
                click.secho('LIMIT')
                break

            if (title in skip) or (n < offset):
                logger.info(f"{n+1}/{num} [ skipped] {title=}")
                click.secho(f"{n+1}/{num} [ skipped] {title=}", fg=(50,50,50))
                continue

            if title in redirects.keys():
                logger.info(f"{n+1}/{num} [redirect] {title=} -> {redirects[title]}")
                click.secho(f"{n+1}/{num} [redirect] {title=} -> {redirects[title]}", fg=(50,50,50))
                # TODO add Wagtail redirect
                continue

            try:
                mwpage,mwtext,pagedata,pgerrors = Articles.load_article(basedir, title)
                if justload:
                    # just load from MediaWiki and quit (testing)
                    continue
            except Exception as err:
                logger.error(f"{datetime.now() - start} {n+1}/{num} ERR {err} | \"{title}\"\n")
                logger.error(traceback.format_exc())
                Articles.log_error(title, err, errfile)
            if not mwpage:
                logger.info(f"{n+1}/{num} [  ERROR ] {title=} -- NO MWPAGE")
                click.secho(f"{n+1}/{num} [  ERROR ] {title=} -- NO MWPAGE", fg='red')
                continue

            if Articles.is_author(mwpage, mw):
                logger.info(f"{n+1}/{num} [  author] {title=}")
                click.secho(f"{n+1}/{num} [  author] {title=}", fg=(50,50,50))
                continue

            is_resourceguide_only = Articles.is_resourceguide_only(mwpage, pagedata)
            logging.info(f"{is_resourceguide_only=}")
            if is_resourceguide_only:
                logger.info(f"{n+1}/{num} [ rsguide] {title=}")
                click.secho(f"{n+1}/{num} [ rsguide] {title=}", fg=(50,50,50))
                continue

            logger.info('------------------------------------------------------------------------')
            logger.info(f"{n+1}/{num} [ARTICLE ] {title=}")
            click.secho(f"{n+1}/{num} [ARTICLE ] {title=}", bold=True)
            try:
                article = Articles.import_article(
                    mw, mwpage, mwtext, pagedata,
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
                Articles.log_error(title, err, errfile)
                if errorquit:
                    return
            except UnhandledTagException as err:
                logger.error(f"UnhandledTagException: {mwpage.title} : {err}\n")
                Articles.log_error(title, err, errfile)
                if errorquit:
                    return
            except NotNullViolation as err:
                logger.error(f"NotNullViolation: {mwpage.title} : {err}\n")
                Articles.log_error(title, err, errfile)
                if errorquit:
                    return
            except IntegrityError as err:
                logger.error(f"IntegrityError: {mwpage.title} : {err}\n")
                Articles.log_error(title, err, errfile)
                if errorquit:
                    return
            except Exception as err:
                errors.append(title)
                click.secho(f"{datetime.now() - start} {n+1}/{num} ERR {err} | {title}", fg='red')
                click.echo(traceback.format_exc())
                logger.error(f"{datetime.now() - start} {n+1}/{num} ERR {err} | \"{title}\"\n")
                logger.error(traceback.format_exc())
                Articles.log_error(title, err, errfile)
                if errorquit:
                    return
            logger.info('')
        logger.info(f"{len(errors)} ERRORS - - - - - - - - - - - - - - - - - -")
        for title in errors:
            logger.info(title)
        logger.info(f"{len(errors) / len(titles)} percent")

    @staticmethod
    def load_articles_metadata(basedir, sources_jsonl):
        authors_by_names,authors_alts = Articles.load_authors(basedir)
        sources_collection,sources_by_headword = Articles.load_sources(basedir, sources_jsonl)
        saved_titles,mw_titles,mw_titles_slugs = Articles.load_mw(basedir)
        redirects = Articles.load_redirects(basedir)
        return [
            authors_by_names,authors_alts,
            sources_collection,sources_by_headword,
            saved_titles,mw_titles,mw_titles_slugs,
            redirects
        ]

    @staticmethod
    def download_authors(alts_path):
        authors_by_names = {
            f"{author.family_name},{author.given_name}": author
            for author in Author.objects.all()
        }
        authors_alts = Authors.alt_names(filename=alts_path)
        return authors_by_names,authors_alts

    @staticmethod
    def dump_authors(authors_by_names, authors_alts, basedir):
        path = basedir / 'authors-by-names.pickle'
        with path.open('wb') as f:
            sys.setrecursionlimit(10000)
            pickle.dump(authors_by_names, f, pickle.HIGHEST_PROTOCOL)
        path = basedir / 'authors-alts.json'
        with path.open('w') as f:
            f.write(json.dumps(authors_alts))

    @staticmethod
    def load_authors(basedir):
        #path = basedir / 'authors-by-names.pickle'
        #with path.open('rb') as f:
        #    authors_by_names = pickle.load(f)
        # no longer makes sense to load from pickle
        # migrate process has evolved and by this point in process
        # the authors are already in the database
        authors_by_names = {
            f"{author.family_name},{author.given_name}": author
            for author in Author.objects.all()
        }
        path = basedir / 'authors-alts.json'
        with path.open('r') as f:
            authors_alts = json.loads(f.read())
        return authors_by_names,authors_alts

    @staticmethod
    def download_sources(jsonl_path):
        logger.info(f"{jsonl_path=}")
        #sources_by_headword = Sources.load_psms_sources_api()
        sources_by_headword = Sources.load_psms_sources_jsonl(jsonl_path)
        try:
            sources_collection = Collection.objects.get(name=ARTICLES_IMAGE_COLLECTION)
        except Collection.DoesNotExist:
            click.echo(f"Collection {Collection} does not exist: Try running migration.initial_setup().")
            return
        source_pks_by_filename = Sources.source_keys_by_filename(
            sources_by_headword, sources_collection
        )
        return sources_collection,sources_by_headword

    @staticmethod
    def dump_sources(sources_collection,sources_by_headword, basedir):
        path = basedir / 'sources-collection.pickle'
        with path.open('wb') as f:
            sys.setrecursionlimit(10000)
            pickle.dump(sources_collection, f, pickle.HIGHEST_PROTOCOL)
        path = basedir / 'sources-by-headword.json'
        with path.open('w') as f:
            f.write(json.dumps(sources_by_headword))

    @staticmethod
    def load_sources(basedir, jsonl_path):
        path = basedir / 'sources-collection.pickle'
        with path.open('rb') as f:
            sources_collection = pickle.load(f)
        sources_by_headword = Sources.load_psms_sources_jsonl(jsonl_path)
        return sources_collection,sources_by_headword

    @staticmethod
    def download_mw(mw, url_prefix, titles=[]):
        mw_titles = Articles.load_mwtitles(mw)
        if not titles:
            titles = mw_titles
        mw_titles_slugs = Articles.load_mwtitles_to_slugs(mw)
        return titles,mw_titles,mw_titles_slugs

    @staticmethod
    def dump_mw(titles, mw_titles, mw_titles_slugs, basedir):
        path = basedir / 'titles.json'
        with path.open('w') as f:
            f.write(json.dumps(titles))
        path = basedir / 'mw-titles.json'
        with path.open('w') as f:
            f.write(json.dumps(mw_titles))
        path = basedir / 'mw-titles-slugs.json'
        with path.open('w') as f:
            f.write(json.dumps(mw_titles_slugs))

    @staticmethod
    def load_mw(basedir):
        path = basedir / 'titles.json'
        with path.open('r') as f:
            titles = json.loads(f.read())
        path = basedir / 'mw-titles.json'
        with path.open('r') as f:
            mw_titles = json.loads(f.read())
        path = basedir / 'mw-titles-slugs.json'
        with path.open('r') as f:
            mw_titles_slugs = json.loads(f.read())
        return titles,mw_titles,mw_titles_slugs

    @staticmethod
    def prep_wagtail():
        index_page = Articles.wagtail_index_page()
        return index_page

    @staticmethod
    def cache_paths(basedir, title):
        article_dir = basedir / 'articles' / title
        article_dir.mkdir(parents=True, exist_ok=True)
        mwppath = article_dir / 'mwpage.pickle'
        mwtpath = article_dir / 'mwtext.json'
        pgdpath = article_dir / 'pagedata.json'
        errpath = article_dir / 'error.json'
        return mwppath,mwtpath,pgdpath,errpath

    @staticmethod
    def dump_article(mwpage, mwtext, pagedata, basedir):
        mwppath,mwtpath,pgdpath,errpath = Articles.cache_paths(basedir, mwpage.title)
        errors = {}
        # TODO makedir
        if 'redirectMsg' in mwtext:
            errors['PageIsRedirectException'] = 'PageIsRedirectException'
        with mwppath.open('wb') as f:
            sys.setrecursionlimit(20000)
            pickle.dump(mwpage, f, pickle.HIGHEST_PROTOCOL)
        with mwtpath.open('w') as f:
            f.write(json.dumps(mwtext))
        with pgdpath.open('w') as f:
            f.write(json.dumps(pagedata))
        with errpath.open('w') as f:
            f.write(json.dumps(errors))
        return mwppath,mwtpath,pgdpath,errpath

    @staticmethod
    def load_article(basedir, title):
        mwppath,mwtpath,pgdpath,errpath = Articles.cache_paths(basedir, title)
        try:
            with mwppath.open('rb') as f:
                mwpage = pickle.load(f)
        except FileNotFoundError:
            mwpage = None
        try:
            with mwtpath.open('r') as f:
                mwtext = json.loads(f.read())
        except FileNotFoundError:
            mwtext = None
        try:
            with pgdpath.open('r') as f:
                pagedata = json.loads(f.read())
        except FileNotFoundError:
            pagedata = None
        try:
            with errpath.open('r') as f:
                errors = json.loads(f.read())
        except FileNotFoundError:
            errors = None
        return mwpage,mwtext,pagedata,errors

    @staticmethod
    def load_redirects(basedir):
        path = basedir / 'redirects.txt'
        with path.open('r') as f:
            text = f.read()
        return {
            line.split('|')[0].strip(): line.split('|')[1].strip()
            for line in [
                    line.replace('\u200e','') for line in text.splitlines()
            ]
        }

    @staticmethod
    def wagtail_index_page(title=ARTICLES_INDEX_PAGE):
        #return ArticlesIndexPage.objects.get(title=title)
        return Page.objects.get(title=title)

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
    def import_article(mw, mwpage, mwtext, pagedata, mw_titles, mw_titles_slugs, url_prefix, authors_by_names, authors_alts, sources_collection, sources_by_headword, index_page, dryrun=False):
        article_class,databox,databox_name = Articles.article_type(mwpage)
        logger.info(f"{article_class=}")
        try:
            article = article_class.objects.get(title=mwpage.title)
            article_is_new = False
        except:
            article = article_class(
                title=mwpage.title,
                body='',
            )
            article_is_new = True
        logger.info(f"{article=}")
        logger.info(f"{article_is_new=}")

        if mwpage.title_sort:
            article.title_sort = mwpage.title_sort
        else:
            article.title_sort = slugify(mwpage.title)

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

        # TODO collect related articles and attach when we have Wagtail IDs
        # TODO write related articles to file? database?
        related_articles = Articles.parse_related_articles(mwtext)

        sources_for_title = sources_by_headword.get(mwpage.title,[])
        source_pks = Sources.source_keys_by_filename(
            sources_for_title, sources_collection
        )
        sources_blocks = Articles.streamfield_media_blocks(
            sources_by_headword.get(mwpage.title, []), source_pks,
        )

        article.description = mwpage.description
        if not article.description:
            article.description = ''
        logger.info(f"{article.description=}")
        article_blocks = Articles.mwtext_to_streamblocks(
            article, mw, mwtext, mw_titles_slugs, url_prefix
        )
        logger.info(f"{len(article_blocks)=}")
        if article_blocks and not article.description:
            logger.info("Making block 0 the description")
            # article.description is a StreamField,
            # which is a list containing StreamBlocks
            article.description = [article_blocks.pop(0)]
        # only prepend Source blocks that are not None
        for source_block in sources_blocks:
            if source_block:
                article_blocks.insert(0, source_block)
        article.body = json.dumps(article_blocks)
        Footnotary.update_footnotes(article, fields=None, request=None, save=False)

        if article_is_new and not dryrun:
            # place page under encyclopedia index
            logger.info(f"{index_page}.add_child(instance={article})")
            result = index_page.add_child(instance=article)

        if not dryrun:
            for author in authors:
                article.authors.add(author)
            # remove mistaken authors on updates
            if not article_is_new:
                for author in article.authors.all():
                    if author not in authors:
                        article.authors.remove(author)
            article.save_revision().publish()

        wm = MediawikiWagtail(
            mediawiki_url=mwpage.url_title,
            wagtail_slug=slugify(mwpage.title),
        )
        wm.save()

        return article,related_articles

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
        mwpage = LegacyPage.get(mw,title, migration=False)
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
    def is_resourceguide_only(mwpage, pagedata):
        """Page is published in Resource Guide but NOT in Encyclopedia
        """
        if mwpage.published_rg and not mwpage.published_encyc:
            return True
        templates = [x['*'] for x in pagedata['templates']]
        if 'Template:publish-rgonly' in templates:
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
    def mwtext_to_streamblocks(article, mw, mwtext: str, mw_titles_slugs, url_prefix) -> list[str]:
        mwtext_cleaned = Articles.clean_mediawiki_text(mwtext)
        mwhtml = Articles.render_mediawiki_text(mw, mwtext_cleaned, mw_titles_slugs, url_prefix)
        streamfield_blocks = Articles.html_to_streamfield(article, mwhtml)
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
        soup = BeautifulSoup(html, 'lxml')
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
    def html_to_streamfield(article, html: str, debug: bool=False) -> list[str]:
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
        def table_is_rgmediatype_databox(tag):
            for t in tag.find_all('th'):
                if t.contents and t.contents[0] == 'RG Media Type':
                    return True
            return False
        soup = BeautifulSoup(html, 'lxml')
        blocks = []
        for tag in soup.body.contents:
            logger.debug(f"{tag=}")
            if type(tag) == NavigableString:
                continue
            if tag.name in ['blockquote', 'i', 'li', 'pre', 'ul', 'dl']:
                continue
            # TODO what to do with <div id="authorByline">?
            if tag.name == 'div' and tag.has_attr('id') and tag['id'] == 'authorByline':
                continue
            # TODO what to do with <div id="citationAuthor">?
            if tag.name == 'div' and tag.has_attr('id') and tag['id'] == 'citationAuthor':
                continue
            if tag.name == 'div' and tag.has_attr('class') and tag['class'] == 'alert alert-info':
                # <div class="alert alert-info">...little available research
                # <div class="alert alert-info">...still under development
                # article tags attached in import_article
                if 'little available research' in tag.contents:
                    article.tags.add('needsmoreresearch')
                    continue
                if 'still under development' in tag.contents:
                    article.tags.add('underdevelopment')
                    continue
            # drop RG Media Type databoxes
            if tag.name == 'tbody' and table_is_rgmediatype_databox(tag):
                tag.decompose()
                continue
            # ignore tables.  TODO handle tables?
            if tag.name in ['table', 'tbody']:
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
                raise UnhandledTagException(f"UnhandledTagException: Don't know what to do with \"{tag.name}\"")
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
    def streamfield_media_blocks(sources, source_pks_by_filename):
        """Consume primary source data from a page and product DDRObjectBlock data

        Block format:
        ('BLOCKTYPE', {'type':'BLOCKTYPE', 'value': {'FIELD1':VALUE1, ...}})
        """
        blocks = []
        for source in sources:
            block = None
            if source['media_format'] == 'image':
                block = ImageBlock.block_from_source(source, source_pks_by_filename)
            elif source['media_format'] == 'video':
                block = VideoBlock.block_from_source(source, source_pks_by_filename)
            elif source['media_format'] == 'document':
                block = DocumentBlock.block_from_source(source, source_pks_by_filename)
            else:
                raise Exception(
                    f"Don't recognize media_format '{source['media_format']}!"
                )
            if block:
                blocks.append(block)
        return blocks

    @staticmethod
    def parse_related_articles(mwtext):
        """Parse mwtext and return list of related articles
        
        <div id="RelatedArticlesDisplay">
        <h2>Related Articles</h2>
        <p class="mw-empty-elt"></p>
        <div id="RelatedArticlesSectionDisplay">
        <h3>General</h3>
        <p class="mw-empty-elt"></p>
        <ul><li><a href="/wiki/hostels" title="Hostels">Hostels</a></li>
        <li><a href="/wiki/resettlement" title="Resettlement">Resettlement</a></li></ul>
        </div>
        </div>
        """
        soup = BeautifulSoup(mwtext, 'lxml')
        div = soup.find(id='RelatedArticlesSectionDisplay')
        if div:
            return [(li.a['href'],li.a['title']) for li in div.find_all('li')]
        return []

    @staticmethod
    def log_error(title, error, path=None):
        """Log article title, error signature and traceback to JSONL file
        """
        if not path:
            return
        data = {}
        data['ts'] = datetime.now().strftime('%Y-%m-%d-T%H:%M:%S')
        data['title'] = title.strip()
        data['error'] = str(error.__class__.__name__).strip()
        data['traceback'] = ''.join(traceback.format_exception(error)).strip()
        with path.open('a') as f:
            f.write(f"{json.dumps(data)}\n")

    @staticmethod
    def log_error_analyze(path):
        with path.open('r') as f:
            lines = f.readlines()
        errors_by_sig = {}
        for line in lines:
            data = json.loads(line)
            if not errors_by_sig.get(data['error']):
                errors_by_sig[data['error']] = []
            errors_by_sig[data['error']].append(data)
        for key in errors_by_sig.keys():
            print(f"{len(errors_by_sig[key])}: {key}")
        return errors_by_sig


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
    #soup = BeautifulSoup('html', 'lxml')
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



def test_import_articles(limit=None):
    jsonl_path = '/opt/encyc-tng/data/densho-psms-sources.jsonl'
    #from pathlib import Path
    #from encyclopedia import migration
    basedir = Path('/opt/encyc-tng/data')
    Articles.import_articles(basedir, jsonl_path, limit=limit)

def test_import_article(title):
    #from pathlib import Path
    #from encyc import wiki
    #from encyclopedia.migration import Authors, Articles
    jsonl_path = '/opt/encyc-tng/data/densho-psms-sources.jsonl'
    basedir = Path('/opt/encyc-tng/data')
    url_prefix = '/wiki/'
    mw = wiki.MediaWiki()
    authors_by_names,authors_alts, sources_collection,sources_by_headword, saved_titles,mw_titles,mw_titles_slugs, redirects = Articles.load_articles_metadata(basedir, jsonl_path)
    index_page = Articles.prep_wagtail()
    mwpage,mwtext,pagedata,pgerrors = Articles.load_article(basedir, title)
    article,related_articles = Articles.import_article(mw, mwpage, mwtext, pagedata, mw_titles, mw_titles_slugs, url_prefix, authors_by_names, authors_alts, sources_collection, sources_by_headword, index_page)
    return article,related_articles



if __name__ == '__main__':
    encyctail()

from pathlib import Path

from wagtail.admin.panels import (
    FieldPanel, FieldRowPanel, InlinePanel, MultiFieldPanel
)
from wagtail.blocks import (
    BooleanBlock, CharBlock, TextBlock, RichTextBlock, URLBlock, ChoiceBlock,
    StreamBlock, StructBlock,
)
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.embeds.blocks import EmbedBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtailmedia.blocks import VideoChooserBlock


class ArticleTextBlock(RichTextBlock):
    pass


class DataboxBlock(StructBlock):
    pass


"""
MariaDB [encycpsms]> describe sources_source;
    id               | int(11)      
    created          | datetime     
    modified         | datetime     
    published        | tinyint(1)   
    densho_id        | varchar(255) 
    headword         | varchar(255) # discard
    encyclopedia_id  | varchar(255) 
    caption          | longtext     
    caption_extended | longtext     
    courtesy         | longtext     
    institution_id   | varchar(255) # "Vol. 21, Sec. C, WRA no. C-705", "hwrd0148", "LC-DIG-hec-23812", ...
    collection_name  | varchar(255) # "Jiro Onuma papers (#2000-27)", "FSA-OWI Collection", ...
    external_url     | varchar(200) # "http://ddr.densho.org/ddr/densho/242/29/", "http://www.oac.cdlib.org/ark:/13030/ft800007k2/?brand=oac4", ...
    creative_commons | tinyint(1)   
    original         | varchar(100) 
    original_size    | int(11)      
    streaming_url    | varchar(200) # ex: rtmp://streaming.densho.org/denshostream/production/encyclopedia/en-denshovh-kyuri-01-0007-1.mp4
    transcript       | varchar(100) # sources/1/1577/en-denshovh-bdennis-02-0005-1.htm
    display          | varchar(100) 
    update_display   | tinyint(1)   
    media_format     | varchar(32)  
    aspect_ratio     | varchar(32)  
    notes            | longtext     # not used

Observations:
- densho_id: DDR ID, blank, "densho", "denshopd-NNN-NNNNN", "denshovh-NAME-NN-NNNN", "sos_NN-NAME-N"
- external_url is DDR URL WHEN densho_id is DDR ID
- external_url is blank   WHEN densho_id = "sos_NN-NAME-N"
- external_url is blank   WHEN densho_id is well-formed denshopd-*/denshovh-* EXCEPT "denshopd-p10-00012" -> "http://ddr.densho.org/ddr/densho/10/12/"
- 14 rows where caption_extended AND collection_name AND institution_id populated
- 31 unpublished items (1 document, 30 images)

TODO if DDRID, make external_url to DDR
TODO ? put densho_id "denshopd-*" or "denshovh-*" in external_url?
TODO ? put densho_id "sos_NN-NAME-N" in external_url?
TODO ? keep collection_name,institution_id? append to caption_extended?
TODO do migration on same machine as encyc-psms

templates/wikiprox/source.html
    source.encyclopedia_id  # discard, it's just the filename
    source.densho_id        # put DDR IDs in ext_url
    source.institution_id   # IMPORTANT: 175 records ! ! !
    source.collection_name  # IMPORTANT: 159 records ! ! !
    source.caption
    source.caption_extended
    source.courtesy
    source.creative_commons
    if source.media_format == 'document':  -> https://docs.wagtail.org/en/v2.16.2/editor_manual/documents_images_snippets/documents.html
        source.institution_id
        source.collection_name
        #source.external_url
        #source.original_path
        #source.original_size
        #document_download_url
    if source.media_format == 'image':
        source.institution_id
        source.collection_name
        source.external_url
        #source.img_url_local  # get from wagtail..Image?
        #source.img_path       # get from wagtail..Image?
        #source.original_size  # get from wagtail..Image?
    if source.media_format == 'video' -> https://github.com/torchbox/wagtailmedia
        source.img_url_local   # get from wagtailmedia?
        source.aspect_ratio    # get from wagtailmedia?
        source.streaming_path  # discard: not used
        source.rtmp_path       # TODO 253 rows of rtmp://streaming.densho.org/denshostream/ links, but these are all .mp4 files
        source.transcript_path 
"""

class ImageBlock(StructBlock):
    image = ImageChooserBlock(required=True)
    caption = TextBlock(required=False)
    caption2 = TextBlock(required=False)
    courtesy = CharBlock(required=False)
    creative_commons = BooleanBlock(required=False)
    ext_url = URLBlock(required=False)

    class Meta:
        icon = 'image'
        label = 'Image'
        template = 'encyclopedia/blocks/imageblock.html'

    @staticmethod
    def block_from_source(source, source_pks_by_filename):
        """StreamField representation of ImageBlock from PSMS source"""
        print(f"{source=}")
        filename = Path(source['original_path']).name
        print(f"{filename=}")
        image_pk = source_pks_by_filename['image'].get(
            filename
        )
        print(f"{image_pk=}")
        return {
            'type': 'imageblock',
            'value': {
                'image': image_pk,
                'caption': source['caption'],
                'caption2': source['caption_extended'],
                'courtesy': source['courtesy'],
                'creative_commons': source['creative_commons'],
                'ext_url': source['external_url'],
            }
        }

class VideoBlock(StructBlock):
    """
    if source.media_format == 'video' -> https://github.com/torchbox/wagtailmedia
        source.img_url_local
        source.aspect_ratio
        source.streaming_path
        source.rtmp_path
        source.transcript_path
    """
    video = VideoChooserBlock(required=False)
    transcript = DocumentChooserBlock(required=False)
    caption = TextBlock(required=False)
    caption2 = TextBlock(required=False)
    courtesy = CharBlock(required=False)
    creative_commons = BooleanBlock(required=False)

    class Meta:
        icon = 'media'
        label = 'Video'
        template = 'encyclopedia/blocks/videoblock.html'

    @staticmethod
    def block_from_source(source, source_pks_by_filename):
        """StreamField representation of VideoBlock from PSMS source"""
        video_pk = source_pks_by_filename['video'].get(
            Path(source['original_path']).name
        )
        transcript_pk = source_pks_by_filename['document'].get(
            Path(source['transcript']).name
        )
        return {
            'type': 'videoblock',
            'value': {
                'video': video_pk,
                'transcript': transcript_pk,
                'caption': source['caption'],
                'caption2': source['caption_extended'],
                'courtesy': source['courtesy'],
                'creative_commons': source['creative_commons'],
            }
        }


class DocumentBlock(StructBlock):
    """
    if source.media_format == 'document':  -> https://docs.wagtail.org/en/v2.16.2/editor_manual/documents_images_snippets/documents.html
        source.original_path
        source.original_size
        document_download_url
    """
    document = DocumentChooserBlock(required=True)
    display = ImageChooserBlock(required=False)
    caption = TextBlock(required=False)
    caption2 = TextBlock(required=False)
    courtesy = CharBlock(required=False)
    creative_commons = BooleanBlock(required=False)
    ext_url = URLBlock(required=False)

    class Meta:
        icon = 'doc-full'
        label = 'Document'
        template = 'encyclopedia/blocks/documentblock.html'

    @staticmethod
    def block_from_source(source, source_pks_by_filename):
        """StreamField representation of DocumentBlock from PSMS source"""
        document_pk = source_pks_by_filename['document'].get(
            Path(source['original_path']).name
        )
        display_pk = source_pks_by_filename['image'].get(
            Path(source['display_path']).name
        )
        return {
            'type': 'documentblock',
            'value': {
                'document': document_pk,
                'display': display_pk,
                'caption': source['caption'],
                'caption2': source['caption_extended'],
                'courtesy': source['courtesy'],
                'creative_commons': source['creative_commons'],
                'ext_url': source['external_url'],
            }
        }


class DDRObjectBlock(StructBlock):
    identifier = CharBlock(required=True, help_text='DDR Identifier')
    caption = TextBlock(required=False)
    caption_extended = TextBlock(required=False)

    class Meta:
        icon = 'image'
        label = 'DDR Object'
        template = 'encyclopedia/blocks/ddrobject.html'


class HeadingBlock(StructBlock):
    heading_text = CharBlock(classname='title', required=True)
    size = ChoiceBlock(
        choices=[
            ('', 'Select a heading size'),
            ('h2', 'H2'),
            ('h3', 'H3'),
            ('h4', 'H4'),
        ],
        blank=True,
        required=False,
    )

    admin_panels = [
        FieldRowPanel([
            FieldPanel('heading_text'),
            FieldPanel('size'),
        ], heading='Header'),
    ]

    class Meta:
        icon = 'title'
        template = 'encyclopedia/blocks/heading_block.html'


class EncycStreamBlock(StreamBlock):
    heading_block = HeadingBlock()
    paragraph_block = RichTextBlock(icon='pilcrow')
    image_block = ImageBlock()
    embed_block = EmbedBlock(
        help_text='Insert a URL to embed. For example, https://youtu.be/sWqDIZxO-nU',
        icon='media',
    )


class QuoteBlock(StructBlock):
    quotation = RichTextBlock(icon='pilcrow')
    attribution = CharBlock(required=False)

    admin_panels = [
        MultiFieldPanel([
            FieldPanel('quotation'),
            FieldPanel('attribution'),
        ], heading='Quotation'),
    ]

    class Meta:
        icon = 'openquote'
        template = 'encyclopedia/blocks/quote_block.html'


class DataboxCampBlock(StructBlock):
    sos_uid                = CharBlock(required=False, label='Sites of Shame UID')  # SoSUID
    densho_name            = CharBlock(required=False, label='Densho name')  # DenshoName
    usg_name               = CharBlock(required=False, label='US Gov name')  # USGName
    facility_type_url      = URLBlock(required=False, label='Facility type URL')  # Type
    facility_type          = CharBlock(required=False, label='Facility type')  # Type
    admin_agency           = CharBlock(required=False, label='Administrative agency')  # AdminAgency
    date_opened            = CharBlock(required=False, label='Date opened')  # DateOpened
    date_closed            = CharBlock(required=False, label='Date closed')  # DateClosed
    location_name          = CharBlock(required=False, label='Location')  # LocationName
    city_name              = CharBlock(required=False, label='City')  # CityName
    state_name             = CharBlock(required=False, label='State name')  # StateName
    gis_lat                = CharBlock(required=False, label='Latitude')  # GISLat
    gis_long               = CharBlock(required=False, label='Longitude')  # GISLong
    gis_tgn_id             = CharBlock(required=False, label='GIS TGN ID')  # GISTGNId
    description            = TextBlock(required=False, label='General description')  # Description
    current_disposition    = TextBlock(required=False, label='Current disposition')  # CurrentDisposition
    population_description = TextBlock(required=False, label='Population description')  # PopulationDescription
    exit_destination       = CharBlock(required=False, label='Exit destination')  # ExitDestination
    peak_population        = CharBlock(required=False, label='Peak population')  # PeakPopulation
    peak_date              = CharBlock(required=False, label='Peak date')  # PeakDate
    nps_link               = URLBlock(required=False, label='National Park Service Info')  # NPSMoreInfoResourceLink
    official_link          = URLBlock(required=False, label='Other Info')  # OfficialResourceLink

    admin_panels = [
        MultiFieldPanel([
            FieldPanel('sos_uid'),
            FieldPanel('densho_name'),
            FieldPanel('usg_name'),
            FieldPanel('facility_type_url'),
            FieldPanel('facility_type'),
            FieldPanel('admin_agency'),
            FieldPanel('date_opened'),
            FieldPanel('date_closed'),
            FieldPanel('location_name'),
            FieldPanel('city_name'),
            FieldPanel('state_name'),
            FieldPanel('gis_lat'),
            FieldPanel('gis_long'),
            FieldPanel('gis_tgn_id'),
            FieldPanel('description'),
            FieldPanel('current_disposition'),
            FieldPanel('population_description'),
            FieldPanel('exit_destination'),
            FieldPanel('peak_population'),
            FieldPanel('peak_date'),
            FieldPanel('nps_link'),
            FieldPanel('official_link'),
        ], heading='Databox Camp'),
    ]

    class Meta:
        label = 'Databox Camp'
        template = 'encyclopedia/blocks/databox_camp_block.html'

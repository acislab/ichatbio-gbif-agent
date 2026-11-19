from datetime import datetime
from uuid import UUID

from enums.common import ContinentEnum, LicenseEnum, GbifRegionEnum, MediaObjectTypeEnum, CountryEnum
from enums.occurrences import BasisOfRecordEnum, OccurrenceStatusEnum
from enums.species import TaxonomicStatusEnum, TypeStatusEnum
from log import logger
from models.base import ProductionBaseModel
from pydantic import Field, field_validator


class TaxonomicFilters(ProductionBaseModel):
    """Filters for occurrences by taxonomic classification (scientific name, taxonKey, or specific rank keys)."""

    scientificName: list[str] | None = Field(
        None,
        description="Only use this parameter if the user has provided a scientific name. All included and synonym taxa are included in the search. Under the hood a call to the taxon match service is done first to retrieve a taxonKey. Only unique scientific names will return results, homonyms (many monomials) return nothing! Consider to use the taxonKey parameter instead and the taxon match service directly",
        examples=[
            ["Quercus robur"],
            ["Homo sapiens", "Canis lupus"],
            ["Puma concolor"],
        ]
    )

    taxonKey: list[str] | None = Field(
        None,
        description="A CoL XR taxon key. Also matches children and synonyms"
    )

    acceptedTaxonKey: list[str] | None = Field(
        None,
        description="A CoL XR taxon key. Parameter may be repeated"
    )

    kingdomKey: list[str] | None = Field(
        None,
        description="Kingdom taxon key. Do not make up this parameter value. It must be explicitly mentioned in the user request"
    )

    phylumKey: list[str] | None = Field(
        None,
        description="Phylum taxon key. Do not make up this parameter value. It must be explicitly mentioned in the user request"
    )

    classKey: list[str] | None = Field(
        None,
        description="Class taxon key. Do not make up this parameter value. It must be explicitly mentioned in the user request"
    )

    orderKey: list[str] | None = Field(
        None,
        description="Order taxon key. Do not make up this parameter value. It must be explicitly mentioned in the user request"
    )

    familyKey: list[str] | None = Field(
        None,
        description="Family taxon key. Do not make up this parameter value. It must be explicitly mentioned in the user request"
    )

    genusKey: list[str] | None = Field(
        None,
        description="Genus taxon key. Do not make up this parameter value. It must be explicitly mentioned in the user request"
    )

    speciesKey: list[str] | None = Field(
        None,
        description="Species taxon key. Do not make up this parameter value. It must be explicitly mentioned in the user request"
    )

    # checklistKey - don't make it configurable, force to CoL XR

    taxonConceptId: list[str] | None = Field(
        None,
        description="An identifier for the taxonomic concept to which the record refers - not for the nomenclatural details of a taxon. Parameter may be repeated",
        examples=[["8fa58e08-08de-4ac1-b69c-1235340b7001"]]
    )

    taxonId: list[str] | None = Field(
        None,
        description="The taxon identifier provided to GBIF by the data publisher. Parameter may be repeated",
        examples=[["urn:lsid:dyntaxa.se:Taxon:103026"]]
    )

    taxonomicStatus: TaxonomicStatusEnum | None = Field(
        None,
        description="Filters by the taxonomic status to distinguish between accepted names, synonyms, and doubtful names. Essential for taxonomic research and data quality control"
    )

    verbatimScientificName: list[str] | None = Field(
        None,
        description="The scientific name provided to GBIF by the data publisher, before interpretation and processing by GBIF. Parameter may be repeated",
        examples=[["Quercus robur L"]]
    )


class GadmFilters(ProductionBaseModel):
    """Filters for occurrences by GADM geographic identifier."""

    gadmGid: list[str] | None = Field(
        None,
        description="A GADM geographic identifier at any level, for example AGO, AGO.1_1, AGO.1.1_1 or AGO.1.1.1_1. Parameter may be repeated",
        examples=[["AGO.1_1"]]
    )

    gadmLevel0Gid: list[str] | None = Field(
        None,
        description="A GADM geographic identifier at the zero level, for example AGO. Parameter may be repeated",
        examples=[["AGO"]]
    )

    gadmLevel1Gid: list[str] | None = Field(
        None,
        description="A GADM geographic identifier at the first level, for e``xample AGO.1_1. Parameter may be repeated",
        examples=[["AGO.1_1"]]
    )

    gadmLevel2Gid: list[str] | None = Field(
        None,
        description="A GADM geographic identifier at the second level, for example AFG.1.1_1. Parameter may be repeated",
        examples=[["AFG.1.1_1"]]
    )

    gadmLevel3Gid: list[str] | None = Field(
        None,
        description="A GADM geographic identifier at the third level, for example AFG.1.1.1_1. Parameter may be repeated",
        examples=[["AFG.1.1.1_1"]]
    )


class GeographicFilters(GadmFilters):
    """Filters for occurrences by geographic location (country, coordinates, geometry, water bodies, etc.)."""

    continent: list[ContinentEnum] | None = Field(
        None,
        description="Continent, as defined in our Continent vocabulary. The continent, based on a 7 continent model described on Wikipedia and the World Geographical Scheme for Recording Plant Distributions (WGSRPD). This splits the Americas into North and South America with North America including the Caribbean (except Trinidad and Tobago) and reaching down and including Panama"
    )

    country: list[CountryEnum] | None = Field(
        None,
        description="The 2-letter country code (as per ISO-3166-1) of the country in which the occurrence was recorded"
    )

    stateProvince: list[str] | None = Field(
        None,
        description="The name of the next smaller administrative region than country (state, province, canton, department, region, etc.) in which the Location occurs. This term does not have any data quality checks; see also the GADM parameters. Parameter may be repeated"
    )

    locality: list[str] | None = Field(
        None,
        description="It's an exact match field, Use this when user insists on a locality name",
        examples=[["Miami-Dade County, Florida"]]
    )

    waterBody: list[str] | None = Field(
        None,
        description="The name of the water body in which the Location occurs",
        examples=[["Atlantic Ocean"], ["Lake Michigan"]]
    )

    island: list[str] | None = Field(
        None,
        description="The name of the island on or near which the location occurs",
        examples=[["Zanzibar"]]
    )

    islandGroup: list[str] | None = Field(
        None,
        description="The name of the island group in which the location occurs",
        examples=[["Seychelles"]]
    )

    higherGeography: list[str] | None = Field(
        None,
        description="Geographic name less specific than the information captured in the locality term. Parameter may be repeated",
        examples=[["Argentina"]]
    )

    decimalLatitude: str | None = Field(
        None,
        description="Latitude in decimal degrees between -90° and 90° based on WGS 84. Supports range queries",
        examples=["40.5,45", "-90,90", "30,50"]
    )

    decimalLongitude: str | None = Field(
        None,
        description="Longitude in decimals between -180 and 180 based on WGS 84. Supports range queries",
        examples=["-120,-95.5", "-180,180", "-100,-50"]
    )

    coordinateUncertaintyInMeters: str | None = Field(
        None,
        description="The horizontal distance (in metres) from the given decimalLatitude and decimalLongitude describing the smallest circle containing the whole of the Location. Supports range queries",
        examples=["0,500"]
    )

    elevation: int | None = Field(
        None,
        description="Elevation (altitude) in metres above sea level. Parameter may be repeated or a range",
        examples=[[1000, 1250]]
    )

    depth: int | None = Field(
        None,
        description="Depth in metres relative to altitude. For example 10 metres below a lake surface with given altitude. Parameter may be repeated or a range",
        examples=[[10, 20]]
    )

    hasCoordinate: bool | None = Field(
        None,
        description="Limits searches to occurrence records which contain a value in both latitude and longitude (i.e. hasCoordinate=true limits to occurrence records with coordinate values and hasCoordinate=false limits to occurrence records without coordinate values)"
    )

    hasGeospatialIssue: bool | None = Field(
        None,
        description="Includes/excludes occurrence records which contain spatial issues (as determined in our record interpretation), i.e. hasGeospatialIssue=true returns only those records with spatial issues while hasGeospatialIssue=false includes only records without spatial issues. The absence of this parameter returns any record with or without spatial issues"
    )

    distanceFromCentroidInMeters: int | None = Field(
        None,
        description="The horizontal distance (in metres) of the occurrence from the nearest centroid known to be used in automated georeferencing procedures, if that distance is 5000m or less. Occurrences (especially specimens) near a country centroid may have a poor-quality georeference, especially if coordinateUncertaintyInMeters is blank or large. Supports range queries",
        examples=[[0, 500]]
    )

    geoDistance: str | None = Field(
        None,
        description="Filters to match occurrence records with coordinate values within a specified distance of a coordinate. Distance may be specified in kilometres (km) or metres (m)",
        examples=["90,100,5km"]
    )

    geometry: list[str] | None = Field(
        None,
        description="Searches for occurrences inside a polygon described in Well Known Text (WKT) format. Only POLYGON and MULTIPOLYGON are accepted WKT types. Polygons must have anticlockwise ordering of points. (A clockwise polygon represents the opposite area: the Earth's surface with a 'hole' in it. Such queries are not supported.)",
        examples=[["POLYGON ((30.1 10.1, 40 40, 20 40, 10 20, 30.1 10.1))"]]
    )

    georeferencedBy: list[str] | None = Field(
        None,
        description="Name of a person, group, or organization who determined the georeference (spatial representation) for the location",
        examples=[["Brad Millen"]]
    )

    gbifRegion: list[GbifRegionEnum] | None = Field(
        None,
        description="Gbif region based on country code. Parameter may be repeated"
    )


class TemporalFilters(ProductionBaseModel):
    """Filters for occurrences by date/time (year, month, eventDate, lastInterpreted, etc.)."""

    year: list[str] | None = Field(
        None,
        description="The 4 digit year. 98 will be interpreted as AD 98",
        examples=[["2020"], ["2010,2020"], ["2010", "2015", "2020"]]
    )

    month: list[str] | None = Field(
        None,
        description="The month of the year as numeric value. Map the month name to the numeric value",
        examples=[["5"], ["1,12"], ["5", "6", "7"]]
    )

    day: list[str] | None = Field(
        None,
        description="The day of the month (1-31)",
        examples=[["1"], ["1,31"], ["1", "15", "30"]]
    )

    eventDate: list[str] | None = Field(
        None,
        description="Occurrence date in ISO 8601 format: yyyy, yyyy-MM or yyyy-MM-dd.\n\n*Parameter may be repeated or a range",
        examples=[["2020"], ["2020-01", "2020-12"], ["2000,2001-06-30"]]
    )

    eventId: list[str] | None = Field(
        None,
        description="An identifier for the information associated with a sampling event. Parameter may be repeated",
        examples=[["A 123"]]
    )

    parentEventId: list[str] | None = Field(
        None,
        description="An identifier for the information associated with a parent sampling event. Parameter may be repeated",
        examples=[["A 123"]]
    )

    startDayOfYear: list[int] | None = Field(
        None,
        description="The earliest integer day of the year on which the event occurred. Parameter may be repeated",
        examples=[[5]]
    )

    endDayOfYear: list[int] | None = Field(
        None,
        description="The latest integer day of the year on which the event occurred. Parameter may be repeated",
        examples=[[6]]
    )

    lastInterpreted: list[str] | None = Field(
        None,
        description="""This date the record was last modified in GBIF, in ISO 8601 format: yyyy, yyyy-MM, yyyy-MM-dd, or MM-dd.
        
        Note that this is the date the record was last changed in GBIF, not necessarily the date the record was first/last changed by the publisher. Data is re-interpreted when GBIF changes the taxonomic backbone, geographic data sources, or interpretation processes.
        
        Parameter may be repeated or a range.""",
        examples=[["2023-02"]]
    )

    modified: list[str] | None = Field(
        None,
        description="The most recent date-time on which the occurrence was changed, according to the publisher. Parameter may be repeated or a range",
        examples=[["2023-02-20"]]
    )

    # --- Field validators ---
    @field_validator("year", "month", "day", mode="before")
    def normalize_to_list(cls, v, info):
        """Normalize input to list format."""
        if v is None:
            return None

        if isinstance(v, str):
            return [v]

        if isinstance(v, int):
            return [str(v)]

        if isinstance(v, list):
            return [str(item) if isinstance(item, int) else item for item in v]

        raise TypeError(
            f"{info.field_name}: expected str, int, or list. Got {type(v).__name__}"
        )

    @field_validator("year", "month", "day", mode="after")
    def validate_format_and_values(cls, values, info):
        """
        Validates that:
        1. All strings contain valid integers
        2. Ranges have exactly 2 values (start,end) and are ascending
        3. Values are within valid bounds
        4. Cannot mix ranges with discrete values
        """
        logger.info(f"Validate:: field={info.field_name} | input_values={values}")

        if values is None:
            return None

        field_name = info.field_name

        # Parse each value and categorize as single or range
        parsed_items = []

        for raw_value in values:
            logger.info(
                f"Validate:: field={field_name} | processing raw_value='{raw_value}' type={type(raw_value).__name__}"
            )

            if not isinstance(raw_value, str):
                error_msg = f"{field_name}: all items must be strings. Got {type(raw_value).__name__} for value '{raw_value}'"
                logger.error(f"Validate:: field={field_name} | ERROR: {error_msg}")
                raise TypeError(error_msg)

            # Split by comma to check if it's a range
            parts = [p.strip() for p in raw_value.split(",")]
            parts = [p for p in parts if p]
            logger.info(f"Validate:: field={field_name} | split into parts: {parts}")

            if len(parts) == 0:
                error_msg = f"{field_name}: empty string is not allowed"
                logger.error(f"Validate:: field={field_name} | ERROR: {error_msg}")
                raise ValueError(error_msg)

            if len(parts) > 2:
                error_msg = (
                    f"{field_name}: invalid range format '{raw_value}'. "
                    f"A range must have exactly 2 values separated by comma, e.g., '2010,2020'. "
                    f"For multiple discrete values, use separate strings: ['2010','2015','2020']"
                )
                logger.error(f"Validate:: field={field_name} | ERROR: {error_msg}")
                raise ValueError(error_msg)

            # Validate all parts are integers
            try:
                nums = [int(p) for p in parts]
                logger.info(
                    f"Validate:: field={field_name} | successfully converted '{raw_value}' to integers: {nums}"
                )
            except ValueError as e:
                error_msg = (
                    f"{field_name}: value '{raw_value}' must contain only integers. "
                    f"Examples: '2020' (single), '2010,2020' (range), ['2010','2015','2020'] (discrete values)"
                )
                logger.error(
                    f"Validate:: field={field_name} | ERROR converting '{raw_value}' to int: {error_msg}"
                )
                raise ValueError(error_msg)

            # Validate range is ascending
            if len(nums) == 2:
                if nums[0] > nums[1]:
                    raise ValueError(
                        f"{field_name}: range must be ascending (start <= end). "
                        f"Got '{raw_value}' where {nums[0]} > {nums[1]}"
                    )
                if nums[0] == nums[1]:
                    raise ValueError(
                        f"{field_name}: range start and end cannot be the same. "
                        f"Got '{raw_value}'. Use a single value '{nums[0]}' instead"
                    )

            # Validate bounds based on field type
            for n in nums:
                if field_name == "month":
                    if not (1 <= n <= 12):
                        raise ValueError(
                            f"{field_name}: months must be between 1 and 12. Got {n} in '{raw_value}'"
                        )
                elif field_name == "day":
                    if not (1 <= n <= 31):
                        raise ValueError(
                            f"{field_name}: days must be between 1 and 31. Got {n} in '{raw_value}'"
                        )
                elif field_name == "year":
                    current_year = datetime.now().year
                    if not (0 <= n <= current_year):
                        raise ValueError(
                            f"{field_name}: years must be between 0 and {current_year}. Got {n} in '{raw_value}'"
                        )

            parsed_items.append((raw_value, nums))

        # Check for mixing ranges with discrete values
        has_range = any(len(nums) == 2 for _, nums in parsed_items)
        has_discrete = any(len(nums) == 1 for _, nums in parsed_items)

        if has_range and has_discrete:
            range_vals = [orig for orig, nums in parsed_items if len(nums) == 2]
            discrete_vals = [orig for orig, nums in parsed_items if len(nums) == 1]
            raise ValueError(
                f"{field_name}: cannot mix range queries with discrete values. "
                f"Found range(s): {range_vals} and discrete value(s): {discrete_vals}. "
                f"Use either a range OR discrete values, not both"
            )

        return values


class RecordIdentifiers(ProductionBaseModel):
    """Filters for occurrences by record identifiers (gbifId, occurrenceId, catalogNumber, recordNumber, etc.)."""

    occurrenceId: list[str] | None = Field(
        None,
        description="A globally unique identifier for the occurrence record as provided by the publisher",
        examples=[["URN:catalog:UWBM:Bird:126493"], ["2005380410", "9876543210"]]
    )

    gbifId: str | None = Field(
        None,
        description="The unique GBIF key for a single occurrence record"
    )

    catalogNumber: list[str] | None = Field(
        None,
        description="An identifier of any form assigned by the source within a physical collection or digital dataset for the record which may not be unique, but should be fairly unique in combination with the institution and collection code",
        examples=[["K001275042"], ["12345", "67890"]]
    )

    recordNumber: list[str] | None = Field(
        None,
        description="An identifier given to the record at the time it was recorded in the field; often links field notes to the event",
        examples=[["1"], ["23", "234543"]]
    )

    otherCatalogNumbers: list[str] | None = Field(
        None,
        description="Previous or alternate fully qualified catalog numbers. Parameter may be repeated",
        examples=[["ABC123"]]
    )

    fieldNumber: list[str] | None = Field(
        None,
        description="An identifier given to the event in the field. Often serves as a link between field notes and the event. Parameter may be repeated",
        examples=[["RV Sol 87-03-08"]]
    )


class DatasetCollectionFilters(ProductionBaseModel):
    """Filters for occurrences by dataset, institution, collection, or publishing organization."""

    datasetKey: list[UUID] | None = Field(
        None,
        description="The occurrence dataset key (a UUID)",
        examples=[
            ["13b70480-bd69-11dd-b15f-b8a03c50a862"],
            ["e2e717bf-551a-4917-bdc9-4fa0f342c530"],
        ]
    )

    datasetId: list[str] | None = Field(
        None,
        description="An identifier for the set of data. May be a global unique identifier or an identifier specific to a collection or institution. externalDocs: https://rs.tdwg.org/dwc/terms/datasetID",
        examples=[["https://doi.org/10.1594/PANGAEA.315492"]]
    )

    datasetName: str | None = Field(
        None,
        description="The name identifying the data set from which the record was derived",
        examples=["eBird"]
    )

    collectionCode: list[str] | None = Field(
        None,
        description="An identifier of any form assigned by the source to identify the physical collection or digital dataset uniquely within the context of an institution",
        examples=[["F"], ["BIRD", "MAMMAL"]]
    )

    collectionKey: list[UUID] | None = Field(
        None,
        description="A key (UUID) for a collection registered in the Global Registry of Scientific Collections",
        examples=[["dceb8d52-094c-4c2c-8960-75e0097c6861"]]
    )

    institutionCode: list[str] | None = Field(
        None,
        description="An identifier of any form assigned by the source to identify the institution the record belongs to. Not guaranteed to be unique",
        examples=[["K"], ["USNM", "BMNH"]]
    )

    institutionKey: list[UUID] | None = Field(
        None,
        description="A key (UUID) for an institution registered in the Global Registry of Scientific Collections. Parameter may be repeated",
        examples=[["fa252605-26f6-426c-9892-94d071c2c77f"]]
    )

    publishingOrg: list[UUID] | None = Field(
        None,
        description="The publishing organization's GBIF key (a UUID). Parameter may be repeated"
    )

    publishingCountry: list[CountryEnum] | None = Field(
        None,
        description="The 2-letter country code (as per ISO-3166-1) of the owning organization's country"
    )

    publishedByGbifRegion: list[GbifRegionEnum] | None = Field(
        None,
        description="GBIF region based on the owning organization's country. Parameter may be repeated"
    )

    hostingOrganizationKey: list[UUID] | None = Field(
        None,
        description="The key (UUID) of the publishing organization whose installation (server) hosts the original dataset. (This is of little interest to most data users.) Parameter may be repeated"
    )

    installationKey: list[UUID] | None = Field(
        None,
        description="The occurrence installation key (a UUID). (This is of little interest to most data users. It is the identifier for the server that provided the data to GBIF.) Parameter may be repeated"
    )

    networkKey: list[UUID] | None = Field(
        None,
        description="The network's GBIF key (a UUID). Parameter may be repeated"
    )

    crawlId: list[str] | None = Field(
        None,
        description="Crawl attempt that harvested this record. Parameter may be repeated",
        examples=[["1"]]
    )

    protocol: list[str] | None = Field(
        None,
        description="Protocol or mechanism used to provide the occurrence record. Parameter may be repeated",
        examples=[["DWC_ARCHIVE"]]
    )


class OrganismSpecimenFilters(ProductionBaseModel):
    """Filters for occurrences by organism/specimen characteristics (basisOfRecord, sex, lifeStage, typeStatus, etc.)."""

    basisOfRecord: list[BasisOfRecordEnum] | None = Field(
        None,
        description="Basis of record, as defined in our BasisOfRecord vocabulary. The values of the Darwin Core term Basis of Record which can apply to occurrences"
    )

    occurrenceStatus: OccurrenceStatusEnum | None = Field(
        None,
        description="Either PRESENT or ABSENT; the presence or absence of the occurrence. A statement about the presence or absence of a Taxon at a Location"
    )

    sex: list[str] | None = Field(
        None,
        description="The sex of the biological individual(s) represented in the occurrence",
        examples=[["MALE"]]
    )

    lifeStage: list[str] | None = Field(
        None,
        description="The age class or life stage of an organism at the time the occurrence was recorded, as defined in the GBIF LifeStage vocabulary](https://registry.gbif.org/vocabulary/LifeStage/concepts)",
        examples=[["JUVENILE"]]
    )

    typeStatus: list[TypeStatusEnum] | None = Field(
        None,
        description="Nomenclatural type (type status, typified scientific name, publication) applied to the subject"
    )

    preparations: list[str] | None = Field(
        None,
        description="Preparation or preservation method for a specimen",
        examples=[["pinned"]]
    )

    previousIdentifications: list[str] | None = Field(
        None,
        description="Previous assignment of name to the organism",
        examples=[["Chalepidae"]]
    )

    organismId: list[str] | None = Field(
        None,
        description="An identifier for the organism instance (as opposed to a particular digital record of the organism). May be a globally unique identifier or an identifier specific to the data set. Parameter may be repeated",
        examples=[["ORG123"]]
    )

    organismQuantity: list[str] | None = Field(
        None,
        description="A number or enumeration value for the quantity of organisms. Parameter may be repeated",
        examples=[["1"]]
    )

    organismQuantityType: list[str] | None = Field(
        None,
        description="The type of quantification system used for the quantity of organisms. Note this term is not aligned to a vocabulary. Parameter may be repeated",
        examples=[["individuals"]]
    )

    relativeOrganismQuantity: list[str] | None = Field(
        None,
        description="The relative measurement of the quantity of the organism (i.e. without absolute units). Parameter may be repeated",
        examples=[["abundant"]]
    )

    sampleSizeUnit: list[str] | None = Field(
        None,
        description="The unit of measurement of the size (time duration, length, area, or volume) of a sample in a sampling event. Parameter may be repeated",
        examples=[["hectares"]]
    )

    sampleSizeValue: list[float] | None = Field(
        None,
        description="A numeric value for a measurement of the size (time duration, length, area, or volume) of a sample in a sampling event. Parameter may be repeated",
        examples=[[50.5]]
    )

    samplingProtocol: list[str] | None = Field(
        None,
        description="The name of, reference to, or description of the method or protocol used during a sampling event. Parameter may be repeated",
        examples=[["malaise trap"]]
    )


class MediaSequenceFilters(ProductionBaseModel):
    """Filters for occurrences by associated media (images, videos) and genetic sequences."""

    mediaType: list[MediaObjectTypeEnum] | None = Field(
        None,
        description="The kind of multimedia associated with an occurrence as defined in our MediaType enumeration"
    )

    isSequenced: bool | None = Field(
        None,
        description="Flag occurrence when associated sequences exists"
    )

    associatedSequences: list[str] | None = Field(
        None,
        description="A list (concatenated and separated) of identifiers (publication, global unique identifier, URI) of genetic sequence information associated with the material entity",
        examples=[["http://www.ncbi.nlm.nih.gov/nuccore/U34853.1"]]
    )


class IdentificationFilters(ProductionBaseModel):
    """Filters for occurrences by who identified or recorded them (identifiedBy, recordedBy, and their IDs)."""

    identifiedBy: list[str] | None = Field(
        None,
        description="The person who provided the taxonomic identification of the occurrence"
    )

    identifiedByID: list[str] | None = Field(
        None,
        description="Identifier (e.g. ORCID) for the person who provided the taxonomic identification of the occurrence"
    )

    recordedBy: list[str] | None = Field(
        None,
        description="The person who recorded the occurrence",
        examples=[["MiljoStyrelsen"], ["John Smith", "Jane Doe"]]
    )

    recordedByID: list[str] | None = Field(
        None,
        description="Identifier (e.g. ORCID) for the person who recorded the occurrence. Parameter may be repeated"
    )


class GeologicalFilters(ProductionBaseModel):
    """Filters for occurrences by geological time periods and stratigraphic information (eons, eras, periods, etc.)."""

    earliestEonOrLowestEonothem: list[str] | None = Field(
        None,
        description="The full name of the earliest possible geochronologic era or lowest chronostratigraphic erathem attributable to the stratigraphic horizon from which the material entity was collected. Parameter may be repeated",
        examples=[["Mesozoic"]]
    )

    earliestEraOrLowestErathem: list[str] | None = Field(
        None,
        description='The full name of the latest possible geochronologic eon or highest chrono-stratigraphic eonothem or the informal name ("Precambrian") attributable to the stratigraphic horizon from which the material entity was collected. Parameter may be repeated',
        examples=[["Proterozoic"]]
    )

    earliestPeriodOrLowestSystem: list[str] | None = Field(
        None,
        description="The full name of the earliest possible geochronologic period or lowest chronostratigraphic system attributable to the stratigraphic horizon from which the material entity was collected. Parameter may be repeated",
        examples=[["Neogene"]]
    )

    earliestEpochOrLowestSeries: list[str] | None = Field(
        None,
        description="The full name of the earliest possible geochronologic epoch or lowest chronostratigraphic series attributable to the stratigraphic horizon from which the material entity was collected. Parameter may be repeated",
        examples=[["Holocene"]]
    )

    earliestAgeOrLowestStage: list[str] | None = Field(
        None,
        description="The full name of the earliest possible geochronologic age or lowest chronostratigraphic stage attributable to the stratigraphic horizon from which the material entity was collected. Parameter may be repeated",
        examples=[["Skullrockian"]]
    )

    latestEonOrHighestEonothem: list[str] | None = Field(
        None,
        description='The full name of the latest possible geochronologic eon or highest chrono-stratigraphic eonothem or the informal name ("Precambrian") attributable to the stratigraphic horizon from which the material entity was collected. Parameter may be repeated',
        examples=[["Proterozoic"]]
    )

    latestEraOrHighestErathem: list[str] | None = Field(
        None,
        description="The full name of the latest possible geochronologic era or highest chronostratigraphic erathem attributable to the stratigraphic horizon from which the material entity was collected. Parameter may be repeated",
        examples=[["Cenozoic"]]
    )

    latestPeriodOrHighestSystem: list[str] | None = Field(
        None,
        description="The full name of the latest possible geochronologic period or highest chronostratigraphic system attributable to the stratigraphic horizon from which the material entity was collected. Parameter may be repeated",
        examples=[["Neogene"]]
    )

    latestEpochOrHighestSeries: list[str] | None = Field(
        None,
        description="The full name of the latest possible geochronologic epoch or highest chronostratigraphic series attributable to the stratigraphic horizon from which the material entity was collected. Parameter may be repeated",
        examples=[["Pleistocene"]]
    )

    latestAgeOrHighestStage: list[str] | None = Field(
        None,
        description="The full name of the latest possible geochronologic age or highest chronostratigraphic stage attributable to the stratigraphic horizon from which the material entity was collected. Parameter may be repeated",
        examples=[["Boreal"]]
    )

    highestBiostratigraphicZone: list[str] | None = Field(
        None,
        description="The full name of the highest possible geological biostratigraphic zone of the stratigraphic horizon from which the material entity was collected. Parameter may be repeated",
        examples=[["Blancan"]]
    )

    lowestBiostratigraphicZone: list[str] | None = Field(
        None,
        description="The full name of the lowest possible geological biostratigraphic zone of the stratigraphic horizon from which the material entity was collected. Parameter may be repeated",
        examples=[["Maastrichtian"]]
    )

    formation: list[str] | None = Field(
        None,
        description="The full name of the lithostratigraphic formation from which the material entity was collected. Parameter may be repeated",
        examples=[["Notch Peak Formation"]]
    )

    group: list[str] | None = Field(
        None,
        description="The full name of the lithostratigraphic group from which the material entity was collected. Parameter may be repeated",
        examples=[["Bathurst"]]
    )

    member: list[str] | None = Field(
        None,
        description="The full name of the lithostratigraphic member from which the material entity was collected. Parameter may be repeated",
        examples=[["Lava Dam Member"]]
    )

    bed: list[str] | None = Field(
        None,
        description="The full name of the lithostratigraphic bed from which the material entity was collected. Parameter may be repeated",
        examples=[["Harlem coal"]]
    )


class InvasiveSpeciesFilters(ProductionBaseModel):
    """Filters for occurrences by invasive species information (establishment means, degree of establishment, pathway)."""

    degreeOfEstablishment: list[str] | None = Field(
        None,
        description="The degree to which an organism survives, reproduces and expands its range at the given place and time, as defined in the GBIF DegreeOfEstablishment vocabulary. Parameter may be repeated",
        examples=[["Invasive"]]
    )

    establishmentMeans: list[str] | None = Field(
        None,
        description="Whether an organism or organisms have been introduced to a given place and time through the direct or indirect activity of modern humans, as defined in the GBIF EstablishmentMeans vocabulary. Parameter may be repeated",
        examples=[["Native"]]
    )

    pathway: list[str] | None = Field(
        None,
        description="The process by which an organism came to be in a given place at a given time, as defined in the GBIF Pathway vocabulary. Parameter may be repeated",
        examples=[["Agriculture"]]
    )


class ConservationFilters(ProductionBaseModel):
    """Filters for occurrences by IUCN Red list conservation category."""

    iucnRedListCategory: list[str] | None = Field(
        None,
        description="A threat status category from the IUCN Red list. The two-letter code for the status should be used. Parameter may be repeated",
        examples=[["EX"], ["CR", "EN"]]
    )


class QualityFilters(ProductionBaseModel):
    """Filters for occurrences by data quality issues, clustering, or repatriation status."""

    issue: list[str] | None = Field(
        None,
        description="A specific interpretation issue as defined in our OccurrenceIssue enumeration. Parameter may be repeated",
        examples=[["COUNTRY_COORDINATE_MISMATCH"]]
    )

    taxonomicIssue: list[str] | None = Field(
        None,
        description="Experimental. A specific taxonomic interpretation issue as defined in our OccurrenceIssue enumeration. Parameter may be repeated",
        examples=[["TAXON_CONCEPT_ID_NOT_FOUND"]]
    )

    isInCluster: bool | None = Field(
        None,
        description="Experimental. Searches for records which are part of a cluster. See the documentation on clustering"
    )

    repatriated: bool | None = Field(
        None,
        description="Searches for records whose publishing country is different to the country in which the record was recorded"
    )


class ProjectProgrammeFilters(ProductionBaseModel):
    """Filters for occurrences by associated projects or programmes (e.g., GBIF BID programme)."""

    programme: list[str] | None = Field(
        None,
        description="A group of activities, often associated with a specific funding stream, such as the GBIF BID programme. Parameter may be repeated",
        examples=[["BID"]]
    )

    projectId: list[str] | None = Field(
        None,
        description="The identifier for a project, which is often assigned by a funded programme. Parameter may be repeated",
        examples=[["bid-af2020-039-reg"]]
    )


class SearchFilters(ProductionBaseModel):
    """Filters for occurrences by full-text search (q parameter), license, or Darwin Core extensions."""

    q: str | None = Field(
        None,
        description="Simple full-text search parameter. The value for this parameter can be a simple word or a phrase. Wildcards are not supported",
        examples=["mammal", "Quercus robur"]
    )

    license: list[LicenseEnum] | None = Field(
        None,
        description="The licence applied to the dataset or record by the publisher"
    )

    dwcaExtension: list[str] | None = Field(
        None,
        description="A known Darwin Core Archive extension RowType. Limits the search to occurrences which have this extension, although they will not necessarily have any useful data recorded using the extension. Parameter may be repeated",
        examples=[["http://rs.tdwg.org/ac/terms/Multimedia"]]
    )


class ExperimentalFilters(ProductionBaseModel):
    """Experimental filters for occurrences (case-sensitive search, random shuffling, highlighting)."""

    matchCase: bool | None = Field(
        None,
        description="Experimental. Indicates if the search has to be case sensitive"
    )

    shuffle: str | None = Field(
        None,
        description="Experimental. Seed to sort the results randomly",
        examples=["abcdefgh"]
    )

    hl: bool | None = Field(
        None,
        description="Set hl=true to highlight terms matching the query when in full-text search fields. The highlight will be an emphasis tag of class gbifH1. Full-text search fields include: title, keyword, country, publishing country, publishing organization title, hosting organization title, and description"
    )


class HighLevelSearchFilters(ProductionBaseModel):
    """High-level composite filters for occurrences by geological time, lithostratigraphy, or biostratigraphy."""

    geologicalTime: str | None = Field(
        None,
        description="The geological time of an occurrence that is present in the chronostratigraphy terms. Parameter may be repeated or a range",
        examples=["Mesozoic"]
    )

    lithostratigraphy: str | None = Field(
        None,
        description="The lithostratigraphy of an occurrence that is present in the group, formation, member and bed terms",
        examples=["Wayne Fm"]
    )

    biostratigraphy: str | None = Field(
        None,
        description="The biostratigraphy of an occurrence that is present in the lowest and highest biostratigraphy terms",
        examples=["Rhynchonella cuvieri Zone"]
    )

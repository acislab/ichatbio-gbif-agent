from util_types import ParameterEnum


class BasisOfRecordEnum(str, ParameterEnum):
    """
    The values of the Darwin Core term Basis of Record which can apply to occurrences.
    See GBIF's Darwin Core Type Vocabulary for definitions.
    """

    PRESERVED_SPECIMEN = "PRESERVED_SPECIMEN"
    FOSSIL_SPECIMEN = "FOSSIL_SPECIMEN"
    LIVING_SPECIMEN = "LIVING_SPECIMEN"
    OBSERVATION = "OBSERVATION"
    HUMAN_OBSERVATION = "HUMAN_OBSERVATION"
    MACHINE_OBSERVATION = "MACHINE_OBSERVATION"
    MATERIAL_SAMPLE = "MATERIAL_SAMPLE"
    LITERATURE = "LITERATURE"
    MATERIAL_CITATION = "MATERIAL_CITATION"
    OCCURRENCE = "OCCURRENCE"
    UNKNOWN = "UNKNOWN"

    def __str__(self):
        return self.value


class OccurrenceStatusEnum(str, ParameterEnum):
    """
    A statement about the presence or absence of a Taxon at a Location.
    For definitions, see the GBIF occurrence status vocabulary.
    """

    PRESENT = "PRESENT"
    ABSENT = "ABSENT"

    def __str__(self):
        return self.value

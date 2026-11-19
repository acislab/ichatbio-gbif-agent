"""Test"""
import asyncio

from ichatbio.agent_response import ResponseContext
from src.agent import GBIFAgent


class SimpleInMemoryContext(ResponseContext):
    """Simple in-memory context to collect messages"""

    def __init__(self):
        self.messages = []
        self.replies = []

    async def reply(self, message: str):
        self.replies.append(message)
        print(f"Reply: {message}")

    def begin_process(self, title: str):
        return SimpleProcess(title, self.messages)


class SimpleProcess:
    """Simple process to collect logs and artifacts"""

    def __init__(self, title: str, messages: list):
        self.title = title
        self.messages = messages
        print(f"Starting process: {title}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            print(f"Process failed: {exc_val}")
        else:
            print(f"Process completed: {self.title}")

    async def log(self, message: str, data=None):
        log_entry = {"message": message, "data": data}
        self.messages.append(log_entry)

    async def create_artifact(self, mimetype: str, description: str, uris=None, metadata=None):
        artifact = {
            "type": "artifact",
            "mimetype": mimetype,
            "description": description,
            "uris": uris,
            "metadata": metadata
        }
        self.messages.append(artifact)


Q1 = 'Who collected the oldest plant record in Palm Springs, California?'
Q2 = "Find the records of Apis mellifera colleceted after 2020 by human observation"
Q3 = 'Count the number of birds collected in the United States in 2024'
Q4 = "Count the records of Apis mellifera colleceted between yearly 2020 and 2024 in California state"
# ---- species queries ----
Q5 = "what is oak and tell me about its related taxa"
Q6 = "I am concerned about endangered cat species. can you tell me their rank, status and threat level"
Q7 = "Count endangered cat species by rank, status and threat level"
# ---- taxonomic information queries ----
Q8 = "Get more information for species of lion"
Q9 = "Retrieve children species of taxon-id 2476674"
Q10 = "Show me the taxonomic hierarchy and species profiles for Quercus robur"
Q11 = "what is total record count for Rattus rattus, Acer saccharum, Agapostemon texanus, Apis mellifera, Ursus maritimus, and Bromus tectorum?"
Q12 = "Find the records of rattus rattus"
Q13 = "I am searching for specimens of the genus Trichilia, collected by Herbert H. Smith in Colombia. The collector number is 447. Please search using all variations of the collector name, including H.H. Smith, H. H. Smith, Herbert Smith"
Q14 = "Find Apis mellifera records collected between 2000–2024 in the US or Canada, within a bounding polygon around the Great Lakes, excluding fossil and living specimens, with coordinates present, images available, and issues absent; return 2 records starting at offset 0, ordered by eventDate descending"
Q15 = "i am looking for person who collected honey bee and bumblebees in North America on 15 Aug 2015, only human observations or museum specimens"
Q16 = "what about occurrence record 2430266710"
Q17 = "Find datasets about Rattus rattus"
Q18 = "can you summarize the travel and collecting history of Herbert H. Smith (including name variants like H.H. Smith, H. H. Smith, Herbert Smith) through the specimens he collected that are in GBIF?"
Q19 = "please generate a timeline of Herbert H. Smith travels from collected data."
Q20 = "Count the number of rattus species in canada."


async def test_find_datasets():
    context = SimpleInMemoryContext()
    agent = GBIFAgent()
    await agent.run(
        context=context, request=Q19, params=None, entrypoint="find_datasets"
    )


async def test_find_occurrence_by_id():
    context = SimpleInMemoryContext()
    agent = GBIFAgent()
    await agent.run(
        context=context, request=Q16, params=None, entrypoint="find_occurrence_by_id"
    )


async def test_count_occurrence_records():
    context = SimpleInMemoryContext()
    agent = GBIFAgent()
    await agent.run(
        context=context, request=Q4, params=None, entrypoint="count_occurrence_records"
    )


async def test_find_occurrence_records():
    context = SimpleInMemoryContext()
    agent = GBIFAgent()
    await agent.run(
        context=context, request=Q15, params=None, entrypoint="find_occurrence_records"
    )


async def test_count_species_records():
    context = SimpleInMemoryContext()
    agent = GBIFAgent()
    await agent.run(
        context=context, request=Q20, params=None, entrypoint="count_species_records"
    )


async def test_find_species_records():
    context = SimpleInMemoryContext()
    agent = GBIFAgent()
    await agent.run(
        context=context, request=Q18, params=None, entrypoint="find_species_records"
    )


async def test_species_taxonomic_information():
    context = SimpleInMemoryContext()
    agent = GBIFAgent()
    await agent.run(
        context=context,
        request=Q8,
        params=None,
        entrypoint="species_taxonomic_information"
    )


async def run_all_tests():
    try:
        # await test_find_occurrence_records()
        # await test_find_occurrence_by_id()
        # await test_find_datasets()
        await test_find_species_records()
        # await test_species_taxonomic_information()
        # await test_count_occurrence_records()
        # await test_count_species_records()

    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())

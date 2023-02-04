"""Load html from files, clean up, split, ingest into Weaviate."""
import os
from pathlib import Path

import weaviate
from bs4 import BeautifulSoup
from langchain.text_splitter import CharacterTextSplitter
import logging

logging.basicConfig(level=logging.INFO)

def clean_data(data):
    soup = BeautifulSoup(data)
    # The Language Chain documentation uses a <main> tag with id "main-content" to
    # identify the main text of the page
    # This is described in the blog post
    # https://blog.langchain.dev/langchain-chat/
    main_sections = soup.find_all("main", {"id": "main-content"})
    if main_sections:
        text = main_sections[0].get_text()        
    else:
        # Fallback to just getting all the text.
        # This is probably not ideal since it will include the navigation and other repetitive things
        text = soup.get_text()

    return "\n".join([t for t in text.split("\n") if t])

class Ingester:
    def __init__(self, weaviate_url=None, openai_api_key=None):
        if weaviate_url is None:
            weaviate_url = os.environ["WEAVIATE_URL"]
        
        self.weviate_url = weaviate_url
    
        if openai_api_key is None:
            openenai_api_key = os.environ["OPENAI_API_KEY"]
        self.openai_api_key = openai_api_key

    def ingest_docs(self, docs_dir):
        """Ingest all the documents in a directory into Weaviate."""
        docs = []
        metadatas = []
        for p in Path(docs_dir).rglob("*"):
            if p.is_dir():
                continue
            with open(p) as f:
                try:
                    contents = f.read()
                except UnicodeDecodeError as e:
                    logging.error("Skipping %s; UnicodeDecodeError %s", p, e)
                    continue
                docs.append(clean_data(contents))
                metadatas.append({"source": p})


        text_splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

        documents = text_splitter.create_documents(docs, metadatas=metadatas)
    
        client = weaviate.Client(
            url=self.weaviate_url,
            additional_headers={"X-OpenAI-Api-Key": self.openai_api_key},
        )

        client.schema.get()
        schema = {
            "classes": [
                {
                    "class": "Paragraph",
                    "description": "A written paragraph",
                    "vectorizer": "text2vec-openai",
                    "moduleConfig": {
                        "text2vec-openai": {
                            "model": "ada",
                            "modelVersion": "002",
                            "type": "text",
                        }
                    },
                    "properties": [
                        {
                            "dataType": ["text"],
                            "description": "The content of the paragraph",
                            "moduleConfig": {
                                "text2vec-openai": {
                                    "skip": False,
                                    "vectorizePropertyName": False,
                                }
                            },
                            "name": "content",
                        },
                        {
                            "dataType": ["text"],
                            "description": "The link",
                            "moduleConfig": {
                                "text2vec-openai": {
                                    "skip": True,
                                    "vectorizePropertyName": False,
                                }
                            },
                            "name": "source",
                        },
                    ],
                },
            ]
        }

        client.schema.create(schema)

        with client.batch as batch:
            for text in documents:
                batch.add_data_object(
                    {"content": text.page_content, "source": str(text.metadata["source"])},
                    "Paragraph",
                )

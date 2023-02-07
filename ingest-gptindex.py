import datetime
import logging
import os
from urllib.parse import urlparse
import subprocess
import ingest


def fetch_site(s):
    # Get the hostname from the URL
    hostname = urlparse(s).hostname
    # Create a directory for the hostname
    if os.path.exists(f"data/{hostname}"):
      logging.info(f"Directory for {hostname} already exists.")
      return
    logging.info("Fetching documents from %s", s)
    subprocess.check_call(["wget", "-r", "--directory-prefix=data", "-A.html", s])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    data_dir = "data"
    if not os.path.exists(data_dir):
      os.makedirs(data_dir)

    sites = [
      "https://gpt-index.readthedocs.io/en/latest/",
      "https://langchain.readthedocs.io/en/latest/",
    ]
    for s in sites:
      fetch_site(s)
      hostname = urlparse(s).hostname
      # Use a sentinel file to indicate that the site has been indexed
      sentinel = os.path.join(data_dir, f"{hostname}.indexed")

      if os.path.exists(sentinel):
        logging.info("Site %s already indexed", s)
        continue

      logging.info("Indexing site %s", s)
      ingester = ingest.Ingester()
      ingester.ingest_docs(os.path.join(data_dir, hostname))

      with open(sentinel, "w") as f:
        f.write("Indexed on " + datetime.datetime.now().isoformat())

      logging.info("Done indexing site %s", s)
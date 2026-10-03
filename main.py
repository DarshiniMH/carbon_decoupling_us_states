import datetime
import requests
from fastapi import FastAPI
from google.cloud import storage
from google.oauth2 import service_account
from user_definition import *

app = FastAPI()

# three EIA "ranked by state" CO2 woorkbooks.
eia_co2_files = {
    "co2_total": "https://www.eia.gov/state/seds/sep_sum/html/xls/CO2_total.xlsx",
    "co2_source": "https://www.eia.gov/state/seds/sep_sum/html/xls/CO2_source.xlsx",
    "co2_sector": "https://www.eia.gov/state/seds/sep_sum/html/xls/CO2_sector.xlsx",
}

def upload_to_gcs(service_account_key, project_id, bucket_name, file_name, data):
    """Upload data to the bucket as file_name."""
    credentials = service_account.Credentials.from_service_account_file\
        (service_account_key)
    client = storage.Client(project=project_id, credentials=credentials)
    bucket = client.bucket(bucket_name)
    file = bucket.blob(file_name)
    file.upload_from_string(data)

@app.post("/ingest/eia_co2")
def ingest_eia_co2():
    """Download each EIA CO2 workbook and save it to GCS one folder per month."""
    month = datetime.date.today().strftime("%Y-%m")
    stored = []

    for url in eia_co2_files.values():
        # download the workbook through API call to EIA
        response = requests.get(url)
        response.raise_for_status()

        original_file_name = url.split("/")[-1]
        file_name = f"{file_name_prefix}/{month}/{original_file_name}"
        upload_to_gcs(service_account_key, project_id, bucket_name,
                      file_name, response.content)
        stored.append(file_name)

    return {"month": month, "files_stored":stored}

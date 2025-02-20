import time
import pandas as pd
import string
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials


CHEFDB_BASE_URL = "https://www.chefdb.com/people/"
CHROME_DRIVER_PATH = "/Users/ligia/Downloads/chromedriver" 

GOOGLE_SHEET_ID = "your_google_sheet_id_here"
SHEET_NAME = "Chef Leads"
def authenticate_google_sheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('your_service_account_credentials.json', scope)
    return build('sheets', 'v4', credentials=creds)


def setup_driver():
    options = Options()
    options.headless = True  # Run in headless mode
    service = Service(CHROME_DRIVER_PATH)
    return webdriver.Chrome(service=service, options=options)



def fetch_chefs_from_chefdb():
    driver = setup_driver()
    chefs = []

    for letter in string.ascii_uppercase:  # Loop through A-Z
        url = f"{CHEFDB_BASE_URL}{letter}"
        print(f"Scraping: {url}")
        driver.get(url)
        time.sleep(3)  # Allow JavaScript content to load

        soup = BeautifulSoup(driver.page_source, "html.parser")

        for chef in soup.find_all("div", class_="chef-entry"):
            name = chef.find("h2").text.strip()
            restaurant = chef.find("div", class_="restaurant").text.strip(
            ) if chef.find("div", class_="restaurant") else ""
            location = chef.find("div", class_="location").text.strip(
            ) if chef.find("div", class_="location") else ""
            profile_link = chef.find("a", href=True)[
                "href"] if chef.find("a", href=True) else ""
            chefs.append({
                "name": name,
                "restaurant": restaurant,
                "location": location,
                "profile_link": f"https://www.chefdb.com{profile_link}"
            })

    driver.quit()  # Close browser session
    return pd.DataFrame(chefs)



def update_google_sheets(df):
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "google_credentials.json", scope)
    client = build("sheets", "v4", credentials=creds)
    sheet = client.spreadsheets()

    values = [df.columns.tolist()] + df.values.tolist()
    request_body = {"values": values}
    sheet.values().update(
        spreadsheetId=GOOGLE_SHEET_ID,
        range=f"{SHEET_NAME}!A1",
        valueInputOption="RAW",
        body=request_body
    ).execute()
    print("Google Sheet updated successfully!")



def main():
    print("Scraping chef leads from ChefDB...")
    leads_df = fetch_chefs_from_chefdb()
    if not leads_df.empty:
        print("Updating Google Sheets...")
        update_google_sheets(leads_df)
        print("Pipeline completed successfully!")
    else:
        print("No data fetched. Exiting.")


if __name__ == "__main__":
    main()

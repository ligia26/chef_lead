import time
import pandas as pd
import string
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
import requests


CHEFDB_BASE_URL = "https://www.chefdb.com/people/"
CHROME_DRIVER_PATH = "./chromedriver" 
GOOGLE_SHEET_ID = "sheet_id_here"  
SHEET_NAME = "Chef Leads"
HUNTER_API_KEY = "hunter_io_api_key"  
GOOGLE_PLACES_API_KEY = "your_google_places_api_key"  # For restaurant details


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
            restaurant = chef.find("div", class_="restaurant").text.strip() if chef.find("div", class_="restaurant") else ""
            location = chef.find("div", class_="location").text.strip() if chef.find("div", class_="location") else ""
            profile_link = chef.find("a", href=True)["href"] if chef.find("a", href=True) else ""
            chefs.append({
                "name": name,
                "restaurant": restaurant,
                "location": location,
                "profile_link": f"https://www.chefdb.com{profile_link}",
                "email": f"{name.replace(' ', '.')}@example.com"  # Placeholder for enrichment
            })

    driver.quit()  # Close browser session
    return pd.DataFrame(chefs)

def validate_email(email):
    url = f"https://api.hunter.io/v2/email-verifier?email={email}&api_key={HUNTER_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("data", {}).get("status", "invalid")
    return "invalid"

def clean_and_validate(df):
    df.drop_duplicates(subset=["name"], inplace=True)
    df["email_status"] = df["email"].apply(validate_email)
    df = df[df["email_status"] == "valid"]  # Keep only valid emails
    return df


def enrich_restaurant_info(df):
    for index, row in df.iterrows():
        restaurant_name = row["restaurant"]
        url = f"https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input={restaurant_name}&inputtype=textquery&fields=name,formatted_address,website&key={GOOGLE_PLACES_API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            result = response.json()["candidates"]
            if result:
                df.at[index, "restaurant_address"] = result[0].get("formatted_address", "")
                df.at[index, "restaurant_website"] = result[0].get("website", "")
        time.sleep(1)  # Prevent API rate limiting
    return df

def update_google_sheets(df):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("google_credentials.json", scope)
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
        print("Cleaning and validating emails...")
        leads_df = clean_and_validate(leads_df)
        print("Enriching restaurant information...")
        leads_df = enrich_restaurant_info(leads_df)
        print("Updating Google Sheets...")
        update_google_sheets(leads_df)
        print("Pipeline completed successfully!")
    else:
        print("No data fetched. Exiting.")

if __name__ == "__main__":
    main()

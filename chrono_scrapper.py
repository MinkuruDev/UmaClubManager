import sys

from typing import Optional
from cloakbrowser import launch

def download_csv(club_id: str) -> Optional[str]:
    """
    Download a CSV file reprenting the fan data of a Umamusume club from Chronogenesis.net.
    The function launches a headless browser, navigates to the specified URL, 
    and executes a JavaScript code to trigger the download of the CSV file. 
    The downloaded file is saved in the "Downloads" directory with its suggested filename.
    Args:
        club_id (str): The ID of the club for which to download fan data.
    Returns:
        Optional[str]: The path to the downloaded CSV file if successful, otherwise None.
    """
    url = f"https://chronogenesis.net/club_profile?circle_id={club_id}"
    try:
        browser = launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        with open("downloadcsv.js", "r") as f:
            js_code = f.read()
        with page.expect_download() as download_info:
            page.evaluate(f"async () => {{ {js_code} }}")
        download = download_info.value

        # Wait for the download process to complete and save the downloaded file somewhere
        download.save_as("./Downloads/" + download.suggested_filename)
        return "./Downloads/" + download.suggested_filename
    except Exception as e:
        print(f"Error occurred while downloading CSV: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        club_id = sys.argv[1]
    else:
        print(f"Usage: python {sys.argv[0]} <club_id>")
        sys.exit(1)

    downloaded_path = download_csv(club_id)
    if downloaded_path:
        print(f"CSV file downloaded successfully: {downloaded_path}")
    else:
        print("Failed to download the CSV file.")

import os
import time
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.schemas import CaseSearchConfig
from src.search import search_for_cases
from src.utils import (
    expand_date_range,
    load_records,
    prompt_for_date_range,
    write_json_atomic,
)

# environment variables
load_dotenv()

website_url = os.getenv("WEBSITE_URL")
data_dir_path = os.getenv("DATA_DIR")

# config
timeout = 5

start_date, end_date = prompt_for_date_range()

main_search_config = CaseSearchConfig(
    court_departments=["Housing Court"],
    court_divisions=["Northeast Housing Court"],
    court_locations=["Northeast Housing Court"],
    results_per_page="75",
    start_date=start_date,
    end_date=end_date,
    case_types=["Housing Court Summary Process"],
    cities=["All Cities"],
    statuses=["Active", "Closed"],
    party_types=["Plaintiff"],
    min_sleep=1,
    max_sleep=2,
)
search_config_dict = main_search_config.to_dict()

dates_to_search = expand_date_range(
    main_search_config.start_date, main_search_config.end_date
)

# create a record of verbose runs
data_dir = Path(data_dir_path or "data")
data_dir.mkdir(parents=True, exist_ok=True)

verbose_path = data_dir / "verbose.json"

# load existing records (overlapping dates will be overwritten)
results = load_records(verbose_path)

# configure the webdriver and access the website
options = webdriver.ChromeOptions()
options.add_argument("--incognito")
driver = webdriver.Chrome(options=options)
driver.get(website_url)

print("Please prove that you're not a robot")
try:
    # wait for user to complete recaptcha
    WebDriverWait(driver, 180).until(EC.url_contains("search.page"))
    print("Human verification completed successfully")
except TimeoutException:
    print("Human verification was not completed within the tme limit")
    driver.close()

try:
    for search_date in dates_to_search:
        # single day search
        start_date = search_date
        end_date = search_date

        # initialize a dated record
        dated_data = {
            "counts": {
                "found": 0,
                "skipped": 0,
            },
            "cases": {},
        }

        # create a new search config that spans only a single day
        temp_search_config = main_search_config.copy(
            start_date=search_date,
            end_date=search_date,
        )
        try:
            # search for the cases
            search_for_cases(driver, temp_search_config)
            time.sleep(3)
        except Exception as e:
            print(
                f"Unable to configure search for {search_date}, due to the exception {e}"
            )
            continue

        keep_alive = True
        while keep_alive:
            try:
                # parse search results
                results_table = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.ID, "grid"))
                )
                table_body = results_table.find_element(By.TAG_NAME, "tbody")
                cards = table_body.find_elements(By.TAG_NAME, "tr")
            except (TimeoutException, NoSuchElementException):
                print(f"No results found for date {search_date}")
                continue  # leave iteration, no results found

            # go over the card components
            case_list: List[Tuple[str, str]] = []
            case_numbers = []
            for card in cards:
                # assumes we've found some form of result
                dated_data["counts"]["found"] += 1
                try:
                    card_components = card.find_elements(By.TAG_NAME, "td")
                    # case links are stored in 3rd column, listed as "Case Number"
                    case_link = card_components[3]
                    case_url = case_link.find_element(By.TAG_NAME, "a").get_attribute(
                        "href"
                    )
                    case_number = case_link.text.strip()
                except (IndexError, TimeoutException, NoSuchElementException):
                    # result does not match format, skip
                    dated_data["counts"]["skipped"] += 1
                    continue

                if case_number in case_numbers:
                    # we've seen it before on this date, skip
                    dated_data["counts"]["skipped"] += 1
                    continue

                case_numbers.append(case_number)
                case_list.append((case_number, case_url))

            for case_num, fresh_url in case_list:
                # default to an empty string
                html_str = ""
                try:
                    driver.get(fresh_url)
                    html_str = driver.page_source
                    time.sleep(1.5)
                except Exception:
                    pass
                finally:
                    # always record
                    dated_data["cases"][case_num] = html_str

            # attempt to access more results
            try:
                driver.find_element(By.XPATH, "//a[@title='Search Results']").click()
                time.sleep(3)
                driver.find_element(By.XPATH, "//a[@title='Go to next page']").click()
                time.sleep(3)
            except (TimeoutException, Exception):
                print("Results exhausted.")
                keep_alive = False
                break

        # record dated results
        results[search_date] = dated_data
        print(f"Successfully recorded the results for {search_date}")

        # go back home to start the next search
        WebDriverWait(driver, timeout).until(
            # using link text
            EC.element_to_be_clickable((By.LINK_TEXT, "Home"))
        ).click()

        # click the search button to begin a fresh search
        WebDriverWait(driver, timeout).until(
            # using link text
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "a.anchorButton.welcome-section")
            )
        ).click()
        time.sleep(1.5)
except Exception as e:
    print(f"Run failed due to the exception: {e}")
finally:
    try:
        try:
            # shutdown the driver (if it exists)
            driver.close()
        except Exception:
            pass

        # safe write of the results
        write_json_atomic(verbose_path, results)
        print(f'Records saved to "{verbose_path}"')

    except Exception as e:
        print(f"Failed to save the run due to the exception: {e}")

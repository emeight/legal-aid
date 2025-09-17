import os

import regex as re

from collections import Counter
from dataclasses import replace
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.export import export_run_to_excel
from src.schemas import CaseSearchConfig, CourtCase
from src.search import build_search_ranges, get_search_coverage, search_for_cases
from src.utils import (
    prompt_for_date_range,
    parse_init_action,
    extract_span_texts,
    load_records,
    lookup_court_case,
    sleepy_click,
    write_json_atomic,
)


# environment variables
load_dotenv()

website_url = os.getenv("WEBSITE_URL")
jitter_factor = os.getenv("JITTER_FACTOR")

data_dir_path = os.getenv("DATA_DIR")

results_per_page = os.getenv("RESULTS_PER_PAGE")

# allow for update_seen to be unset
update_seen = os.getenv("UPDATE_SEEN", "")

try:
    # format the jitter factor
    jitter_factor = float(jitter_factor)
except (TypeError, ValueError):
    # defaults to 1.0
    print("Defaulting jitter factor to 1.0")
    jitter_factor = 1.0

if jitter_factor < 0:
    print(f"Negatives are not allowed, assuming a jitter factor of {abs(jitter_factor)}")
    jitter_factor = abs(jitter_factor)

# config
timeout = 15  # seconds
fast_timeout = 5  # seconds
min_sleep = 3  # seconds
max_sleep = min_sleep + (min_sleep * jitter_factor)

date_input_format = "%m/%d/%Y"
start_date, end_date = prompt_for_date_range()

try:
    update_seen = update_seen.strip().lower() in {"true", "yes", "y"}
except Exception:
    update_seen = False

# load records
data_dir = Path(data_dir_path or "data")
data_dir.mkdir(parents=True, exist_ok=True)

records_path = data_dir / "records.json"

runs_dir = data_dir / "runs"
runs_dir.mkdir(parents=True, exist_ok=True)

run_time_format = "%m-%d-%Y %H:%M:%S"
safe_time_format = "%m-%d-%Y_%H-%M-%S"

tz_info = ZoneInfo("America/New_York")
run_start_time = datetime.now(tz_info)
run_name = run_start_time.strftime(safe_time_format)
run_path = runs_dir / f"{run_name}.json"

# prefer env var OUTPUTS_DIR; if empty/missing, default to /outputs
raw = os.getenv("OUTPUTS_DIR", "").strip()
if raw:
    # expand ~ and $VARS; make relative paths resolve under data_dir
    candidate = Path(os.path.expandvars(raw)).expanduser()
    outputs_dir = candidate if candidate.is_absolute() else (data_dir / candidate)
else:
    outputs_dir = data_dir / "outputs"

outputs_dir.mkdir(parents=True, exist_ok=True)
output_path = outputs_dir / f"{run_name}.xlsx"

# load existing records
case_records = load_records(records_path)
print(f"Loaded {len(list(case_records.keys()))} existing case records")
if update_seen:
    print("Previously seen cases will be update (if possible)")
else:
    print("Previously seen cases will not be updated")

# run-specific metadata setup
run_data = {
    "started_at": run_start_time.strftime(run_time_format),
    "ended_at": "",
    "time_elapsed": 0.0,
    "counts": {
        "viewed": 0,
        "updated": 0,
        "skipped": 0,
    },
    "coverage": {},  # keyed by search_start_date (str)
    "results": {},  # mapping: case_number (str) -> result fields for this run
}

# access the website
driver = webdriver.Chrome()
driver.get(website_url)

# rely on user to complete recaptcha
print("Please prove that you're not a robot")
try:
    WebDriverWait(driver, 180).until(
        EC.url_contains("search.page")
    )
    print("Human verification completed successfully")
except TimeoutException:
    print("Human verification was not completed within the tme limit")
    driver.close()

# primary search configuration
main_search_config = CaseSearchConfig(
    court_departments = ["Housing Court"],
    court_divisions=["Northeast Housing Court"],
    court_locations=["Northeast Housing Court"],
    results_per_page=results_per_page,
    start_date=start_date,
    end_date=end_date,
    case_types=["Housing Court Summary Process"],
    cities=["All Cities"],
    statuses=["Active"],
    party_types=["Defendant"],
    min_sleep=min_sleep,
    max_sleep=max_sleep,
)
search_config_dict = main_search_config.to_dict()

# printing search configurations
exclude_from_print = {"results_per_page", "min_sleep", "max_sleep"}
defer_print = {"start_date", "end_date"}

print("Search Configurations:")

# print all except excluded + deferred
for key, value in search_config_dict.items():
    if key in exclude_from_print or key in defer_print:
        continue
    title = key.replace("_", " ").title()
    if isinstance(value, list):
        value = ", ".join(value)
    print(f"    {title}: {value}")

# print start_date and end_date at the end
for key in ("start_date", "end_date"):
    if key in search_config_dict:
        title = key.replace("_", " ").title()
        value = search_config_dict[key]
        if isinstance(value, list):
            value = ", ".join(value)
        print(f"    {title}: {value}")

search_for_cases(driver, main_search_config, timeout)

# ensure we maximize the number of cases we can extract from the search
coverage = get_search_coverage(driver, timeout)
print(f"{coverage:.2%} of resulting cases from the query are accessible.")

search_date_ranges = build_search_ranges(start_date, end_date, coverage)

if len(search_date_ranges) > 1:
    print("The following dates will be queried indvidually to maximize coverage:")
    for start_date, _ in search_date_ranges:
        print(f"    {start_date}")

for search_start_date, search_end_date in search_date_ranges:
    # only cycle through search if the date range was expanded, otherwise keep current search
    if len(search_date_ranges) > 1:
        # we need to search again, go back to home
        home_link = WebDriverWait(driver, timeout).until(
            # using link text
            EC.element_to_be_clickable((By.LINK_TEXT, "Home"))
        )
        sleepy_click(home_link, min_sleep, max_sleep)

        # click the search button to begin a fresh search
        search_button = WebDriverWait(driver, timeout).until(
            # using link text
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.anchorButton.welcome-section"))
        )
        sleepy_click(search_button, min_sleep, max_sleep)

        # update search config with 
        search_config = replace(main_search_config, start_date=search_start_date, end_date=search_end_date)
        search_for_cases(driver, search_config, timeout)

    # log the coverage
    run_data["coverage"][search_start_date] = {
        "factor": get_search_coverage(driver, timeout),
        "start_date": search_start_date,
        "end_date": search_end_date,
    }

    keep_alive = True
    while keep_alive:
        try:
            # parse search results
            results_table = WebDriverWait(driver, fast_timeout).until(
                EC.presence_of_element_located((By.ID, "grid"))
            )
            table_body = results_table.find_element(By.TAG_NAME, "tbody")
            cards = table_body.find_elements(By.TAG_NAME, "tr")
        except (TimeoutException, NoSuchElementException):
            keep_alive = False
            print(f"No results found for date range {search_start_date} to {search_end_date}")
            break  # leave loop, no results found

        case_list: List[Tuple[CourtCase, str]] = []
        for card in cards:
            card_components = card.find_elements(By.TAG_NAME, "td")
            try:
                # case link store in 3rd column, listed as "Case Number"
                case_link = card_components[3]
                case_url = case_link.find_element(By.TAG_NAME, "a").get_attribute("href")
                case_number = case_link.text.strip()

                # creation time
                time_now = datetime.now(tz_info).strftime(run_time_format)

                # check if we've seen this case before
                if lookup_court_case(case_records, case_number):
                    # create an instance of the case
                    seen_case = CourtCase(**case_records[case_number])
                    # update parameters
                    seen_case.status = "seen"
                    seen_case.updated_at = time_now
                    # add to case_list if we want to update
                    if update_seen:
                        case_list.append((seen_case, case_url))
                    # skip to next card
                    continue

                # create a CourtCase instance and add it to the list
                case_obj = CourtCase(
                    case_number = case_link.text.strip(),
                    status = "new",
                    file_date = card_components[5].text.strip(),
                    primary_party = card_components[2].text.strip(),
                    defendant = "",
                    plaintiff = "",
                    init_action = parse_init_action(card_components[6].text.strip()),
                    address= None,
                    zipcode=None,
                    created_at=time_now,
                    updated_at=time_now,
                )
                case_list.append((case_obj, case_url))
            except (IndexError, TimeoutException):
                # result does not match format, skip
                continue

        # pull out the CourtCase objects, then count duplicate case_numbers
        duplicate_case_count = len([
            n for n, cnt in Counter([c.case_number for c, _ in case_list]).items()
            if cnt > 1
        ])
        run_data["counts"]["skipped"] += duplicate_case_count

        # to avoid stale links, we grab all the data from the page then cycle over the links
        for court_case, fresh_url in case_list:
            # skip if we've already recorded this case_number in this run
            if court_case.case_number in run_data["results"]:
                continue

            # visit each "Case Detail" page
            driver.get(fresh_url)  # this should always be fresh, not stored

            try:
                # parse out the property address
                address_container = WebDriverWait(driver, fast_timeout).until(
                    EC.presence_of_element_located((By.ID, "addressInfo"))
                )
                address_rows = address_container.find_elements(By.TAG_NAME, "div")

                # need at least two rows to hold street, city, state, and zipcode
                street_parts = extract_span_texts(address_rows[0])  # i.e. ["23", "Prince", "Street", "9"]
                place_parts = extract_span_texts(address_rows[1])  # i.e. ["Danvers", "MA", "01923"]

                # city, state zIP — tolerate missing pieces and stray spacing
                city = place_parts[0] if len(place_parts) >= 1 else ""
                state = place_parts[1] if len(place_parts) >= 2 else ""
                zipc = place_parts[2] if len(place_parts) >= 3 else ""
            
                # combined strings
                line1 = " ".join(street_parts)
                line2 = ", ".join(filter(None, [city, state])) + (f" {zipc}" if zipc else "")
                full_address = f"{line1}, {line2}" if line2 else line1

                # update address
                court_case.address = full_address
                court_case.zipcode = zipc

            except (KeyError, IndexError, TimeoutException, NoSuchElementException):
                # don't update address
                pass

            try:
                # parse out plaintiff and defendant
                party_info_container = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.ID, "ptyContainer"))
                )

                # Only consider DIRECT child rows of #ptyContainer (rowodd/roweven)
                party_blocks = party_info_container.find_elements(
                    By.XPATH, "./div[starts-with(@class,'row')]"
                )

                first_plaintiff: Optional[str] = None
                first_defendant: Optional[str] = None

                for block in party_blocks:
                    try:
                        # name/role live inside the subSectionHeader2 header
                        header = block.find_element(By.CLASS_NAME, "subSectionHeader2")
                        name = header.find_element(By.CLASS_NAME, "ptyInfoLabel").text.strip()
                        role_raw = header.find_element(By.CLASS_NAME, "ptyType").text
                    except NoSuchElementException:
                        continue

                    # normalize role text like " - Plaintiff"
                    role = re.sub(r"\s|-", " ", role_raw).strip().lower()

                    if ("plaintiff" in role) and (first_plaintiff is None):
                        first_plaintiff = name
                    if ("defendant" in role) and (first_defendant is None):
                        first_defendant = name

                    if first_plaintiff and first_defendant:
                        break

                # update the case
                court_case.plaintiff = first_plaintiff
                court_case.defendant = first_defendant

            except (TimeoutException, NoSuchElementException):
                # don't update
                pass

            if update_seen and (court_case.status == "seen"):
                # update metadata for previously seen cases
                court_case.status = "updated"
                court_case.updated_at = datetime.now(tz_info).strftime(run_time_format)

            # record the court case
            case_dict = court_case.to_dict()
            run_data["results"][court_case.case_number] = case_dict
            case_records[court_case.case_number] = case_dict

            # pretty print the case
            max_key_len = max(len(k) for k in case_dict)
            # print "None" for None values
            max_val_len = max(len(str(v) if v is not None else "None") for v in case_dict.values())
            box_width = max_key_len + max_val_len + 5

            print("+" + ("-" * box_width) + "+")
            for k, v in case_dict.items():
                val_str = str(v) if v is not None else "None"
                print(f"| {k:<{max_key_len}} : {val_str:<{max_val_len}} |")
            print("+" + ("-" * box_width) + "+")

            # leave the case detail page
            driver.back()

        # attempt to access more results
        try:
            # wait until the "next page" button is clickable
            next_page_btn = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, "//a[@title='Go to next page']"))
            )
            sleepy_click(next_page_btn, min_sleep, max_sleep)
        except TimeoutException:
            print("Results exhausted.")
            keep_alive = False
            break

# shutdown the driver
driver.close()

# save the run
run_end_time = datetime.now(tz_info)
elapsed_time = run_end_time - run_start_time
elapsed_time_rounded = round(elapsed_time.total_seconds(), 2)

print(f"Run complete in {elapsed_time_rounded} seconds")

run_data["ended_at"] = run_end_time.strftime(run_time_format)
run_data["time_elapsed"] = elapsed_time_rounded

# count statuses
status_counts = Counter(
    r["status"].lower()
    for r in run_data["results"].values()
    if r.get("status")
)

# update run data
run_data["counts"] = {
    "new":    status_counts.get("new", 0),
    "updated": status_counts.get("updated", 0),
    # already computed "skipped"
    "skipped": run_data["counts"]["skipped"],
}

print("Summary by Status:")
for status, count in run_data["counts"].items():
    print(f'  "{status}": {count}')

# notify user if any search had a coverage factor < 1.0
for date_key, cov in run_data.get("coverage", {}).items():
    if cov.get("factor", 1.0) < 1.0:
        print(
            f"Warning: Coverage incomplete for "
            f"{cov['start_date']}-{cov['end_date']} "
            f"({cov['factor'] * 100:.2f}%)"
        )

# safe write of the run
write_json_atomic(run_path, run_data)
print(f'Run saved to "{run_path}"')

# safe rewrite of the results
write_json_atomic(records_path, case_records)
print(f'Records saved to "{records_path}"')

# export
export_run_to_excel(run_data, output_path)
print(f'Output saved to "{output_path}"')
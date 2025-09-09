# main.py

import os

from dataclasses import dataclass
from datetime import datetime, timedelta
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import List, Optional, Tuple, Union

from src.utils import sleep_randomly

# load environment variables
load_dotenv()

MAIN_URL = os.getenv("MAIN_URL")

# setup the web driver
driver: WebDriver = webdriver.Chrome()

# access the website
driver.get(MAIN_URL)

# prove that you're not a robot (rely on user)
print("Please prove that you're not a robot, then navigate to the search page.")

try:
    # rely on user to navigate to the search page
    WebDriverWait(driver, 60).until(
        EC.url_contains("search.page")
    )
    print("Great, they don't think you're a robot!")
except TimeoutException:
    print("You were unable to prove that you're not a robot.")
    driver.close()


# set up the search

def dropdown_select_visible_text(driver: WebDriver, name: str, selection: str, max_wait: int = 15) -> None:
    """Identify a dropdown by name and make a selection by visible text.

    Parameters
    ----------

    Raises
    ------
    TimeoutException
        Raised if max_wait time is met without the presence of the object.

    NoSuchElementException
        Raised if the selection is not found.
    
    """
    # wait until the element is present
    dropdown = WebDriverWait(driver, max_wait).until(
        EC.presence_of_element_located((By.NAME, name))
    )
    # make a selection by visible text
    sel = Select(dropdown)
    sel.select_by_visible_text(selection)
    # sleep randomly
    sleep_randomly(2, 4)

dropdown_select_visible_text(driver, "sdeptCd", "Housing Court")
print('Narrowed search to court departments of type "Housing Court".')

dropdown_select_visible_text(driver, "sdivCd", "Northeast Housing Court")
print('Narrowed search to court divisions within the "Northeast Housing Court".')

dropdown_select_visible_text(driver, "slocCd", "Northeast Housing Court")
print('Narrowed search to court locations within the "Northeast Housing Court".')

dropdown_select_visible_text(driver, "pageSize", "75")
print('Search results will contain up to 75 results per page.')


def select_case_type_tab(driver: WebDriver, max_wait: int = 15) -> None:
    """Ensure the "Case Type" tab is active without using XPath (or unstable IDs).

    Raises
    ------
    TimeoutException
        If required elements never become visible/clickable within `max_wait`.
    """
    # wait for the tab row to be visible
    tab_row = WebDriverWait(driver, max_wait).until(
        EC.visibility_of_element_located((By.CLASS_NAME, "tab-row"))
    )

    # get the text of the currently selected tab (no XPath/CSS)
    def _selected_tab_text() -> str:
        for li in tab_row.find_elements(By.TAG_NAME, "li"):
            cls = li.get_attribute("class") or ""
            if "selected" in cls.split():
                try:
                    return li.find_element(By.TAG_NAME, "a").text.strip()
                except Exception:
                    return ""
        return ""

    # click "Case Type" if not already selected
    if _selected_tab_text() != "Case Type":
        # Use LINK_TEXT to find the tab anchor
        case_type_link = WebDriverWait(driver, max_wait).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Case Type"))
        )
        case_type_link.click()

    # confirm we're on the Case Type tab by waiting for date-range inputs.
    WebDriverWait(driver, max_wait).until(
        EC.visibility_of_element_located((By.NAME, "fileDateRange:dateInputBegin"))
    )
    WebDriverWait(driver, max_wait).until(
        EC.visibility_of_element_located((By.NAME, "fileDateRange:dateInputEnd"))
    )

    sleep_randomly(5, 7)

select_case_type_tab(driver)

def input_case_date_span(driver: WebDriver, start_date: datetime, end_date: datetime, max_wait: int = 15) -> None:
    """Refine the search to a range of dates.

    Parameters
    ----------
    
    """
    start_date_formatted = start_date.strftime("%m/%d/%Y")
    end_date_formatted = end_date.strftime("%m/%d/%Y")

    # wait for the inputs to appear
    begin_input = WebDriverWait(driver, max_wait).until(
        EC.presence_of_element_located((By.NAME, "fileDateRange:dateInputBegin"))
    )
    end_input = WebDriverWait(driver, max_wait).until(
        EC.presence_of_element_located((By.NAME, "fileDateRange:dateInputEnd"))
    )

    # clear inputs and type date
    begin_input.clear()
    begin_input.send_keys(start_date_formatted, Keys.TAB)  # TAB triggers onchange
    end_input.clear()
    end_input.send_keys(end_date_formatted, Keys.TAB)

    # sleep randomly
    sleep_randomly(2, 4)


input_case_date_span(driver, datetime.now() - timedelta(days=10), datetime.now() - timedelta(days=5))


def dropdown_select_visible_text(
    driver: WebDriver, 
    name: str, 
    selections: Union[str, list[str]], 
    max_wait: int = 15
) -> None:
    """Identify a dropdown by name, clear existing selections if multi-select,
    and make a selection by visible text.

    Parameters
    ----------
    driver : WebDriver
        Selenium webdriver instance.

    name : str
        The `name` attribute of the <select> element.

    selections : str | list[str]
        One or more visible option texts to select.

    max_wait : int, default=15
        Maximum seconds to wait for the dropdown to be present.

    Raises
    ------
    TimeoutException
        If the dropdown does not appear within max_wait.

    NoSuchElementException
        If any of the requested selections are not found.
    """
    # wait until the element is present
    dropdown = WebDriverWait(driver, max_wait).until(
        EC.presence_of_element_located((By.NAME, name))
    )
    sel = Select(dropdown)

    # normalize to list
    if isinstance(selections, str):
        selections = [selections]

    # clear if multi-select
    if sel.is_multiple:
        sel.deselect_all()

    # make selections
    for s in selections:
        sel.select_by_visible_text(s)

    # optional pause to look human
    sleep_randomly(2, 4)

# multiple selections
dropdown_select_visible_text(driver, "caseCd", "Housing Court Summary Process")
dropdown_select_visible_text(driver, "cityCd", "All Cities")
dropdown_select_visible_text(driver, "statCd", "Active")
dropdown_select_visible_text(driver, "ptyCd", "Defendant")

search_btn = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.NAME, "submitLink"))
)
search_btn.click()


@dataclass(frozen=True)
class CaseRow:
    """Parsed row from the MassCourts results table.

    Attributes
    ----------
    name : str
        Party/Company display name (e.g., "Bourgeois, John").

    case_number : str
        Case number (e.g., "25H77SP004332").

    file_date : str
        File date exactly as shown in the UI (e.g., "09/02/2025").

    init_action : str
        Reason for case.

    address : str
        Property address (if listed).

    plaintiff : str
        plaintiff of the case.

    """
    name: Optional[str]
    case_number: Optional[str]
    file_date: Optional[str]
    init_action: Optional[str]
    address: Optional[str]
    plaintiff: Optional[str]
    defendant: Optional[str]

def get_property_address(driver: WebDriver, timeout: int = 10) -> Optional[str]:
    """Return (line1, line2, full) for the Property Address, or None if not found."""
    # wait for the address container
    container = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.ID, "addressInfo"))
    )

    # first two rows hold street line and city/state/zip
    rows = container.find_elements(By.TAG_NAME, "div")
    if len(rows) < 2:
        return None

    def spans_text(div_el):
        # collect non-empty trimmed span texts
        return [s.text.strip() for s in div_el.find_elements(By.TAG_NAME, "span") if s.text.strip()]

    street_parts = spans_text(rows[0])  # e.g. ["23", "Prince", "Street", "9"]
    place_parts  = spans_text(rows[1])  # e.g. ["Danvers", "MA", "01923"]

    if not street_parts or not place_parts:
        return None

    # if the last token is a pure unit number, format as "Unit N"
    unit = ""
    if street_parts and street_parts[-1].isdigit():
        unit = street_parts.pop()  # remove trailing unit number

    line1 = " ".join(street_parts)
    if unit:
        line1 = f"{line1}, Unit {unit}"

    # City, State ZIP — tolerate missing pieces and stray spacing
    city = place_parts[0] if len(place_parts) >= 1 else ""
    state = place_parts[1] if len(place_parts) >= 2 else ""
    zipc = place_parts[2] if len(place_parts) >= 3 else ""

    line2 = ", ".join(filter(None, [city, state])) + (f" {zipc}" if zipc else "")

    full = f"{line1}, {line2}" if line2 else line1
    return full

def get_first_plaintiff_and_defendant(driver: WebDriver, timeout: int = 15) -> Tuple[Optional[str], Optional[str]]:
    # Wait for the Party Information container
    container = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.ID, "ptyContainer"))
    )

    # Each party block is one of the row* divs under #ptyContainer
    rows = container.find_elements(By.XPATH, "./div[starts-with(@class,'row')]")

    first_plaintiff = None
    first_defendant = None

    for row in rows:
        try:
            name = row.find_element(By.CLASS_NAME, "ptyInfoLabel").text.strip()
            role = row.find_element(By.CLASS_NAME, "ptyType").text.strip()
        except Exception:
            continue

        # role strings look like " - Plaintiff" / " - Defendant" (with spaces)
        if "Plaintiff" in role and first_plaintiff is None:
            first_plaintiff = name
        elif "Defendant" in role and first_defendant is None:
            first_defendant = name

        if first_plaintiff and first_defendant:
            break

    return first_plaintiff, first_defendant

def parse_search_results(driver: WebDriver, max_wait: int = 15) -> List[CaseRow]:
    # collect case data and hrefs first
    table = WebDriverWait(driver, max_wait).until(
        EC.presence_of_element_located((By.ID, "grid"))
    )
    tbody = table.find_element(By.TAG_NAME, "tbody")
    rows = tbody.find_elements(By.TAG_NAME, "tr")

    rows_data = []
    for r in rows:
        cells = r.find_elements(By.TAG_NAME, "td")
        if len(cells) < 6:
            continue
        name = cells[2].text.strip()
        case_number = cells[3].text.strip()
        file_date = cells[5].text.strip()
        init_action = cells[6].text.strip()
        href = cells[3].find_element(By.TAG_NAME, "a").get_attribute("href")
        rows_data.append((name, case_number, file_date, init_action, href))

    # visit each case detail page
    out: List[CaseRow] = []
    for name, case_number, file_date, init_action, href in rows_data:
        driver.get(href)

        try:
            address = get_property_address(driver, timeout=5)  # short timeout
            plaintiff, defendant = get_first_plaintiff_and_defendant(driver)
        except TimeoutException:
            address = None
        sleep_randomly(2, 4)


        case_row = CaseRow(name, case_number, file_date, init_action, address, plaintiff, defendant)
        out.append(CaseRow(name, case_number, file_date, init_action, address, plaintiff, defendant))

        # go back to results and re-wait for the table
        driver.back()
        WebDriverWait(driver, max_wait).until(
            EC.presence_of_element_located((By.ID, "grid"))
        )

        # --------------------------
        # Pretty bordered printout
        # --------------------------
        fields = {
            "Name": case_row.name,
            "Case #": case_row.case_number,
            "File Date": case_row.file_date,
            "Init Action": case_row.init_action,
            "Address": case_row.address or "N/A",
            "Plaintiff": case_row.plaintiff or "N/A",
            "Defendant": case_row.defendant or "N/A",
        }

        max_key_len = max(len(k) for k in fields)
        max_val_len = max(len(str(v)) for v in fields.values())
        box_width = max_key_len + max_val_len + 5

        print("+" + ("-" * box_width) + "+")
        for k, v in fields.items():
            print(f"| {k:<{max_key_len}} : {v:<{max_val_len}} |")
        print("+" + ("-" * box_width) + "+")

    return out

sleep_randomly(5, 10)

results = parse_search_results(driver)

sleep_randomly(10, 30)

driver.close()
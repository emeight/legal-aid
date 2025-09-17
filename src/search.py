import regex as re

from math import isclose
from typing import List, Tuple

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.schemas import CaseSearchConfig
from src.utils import expand_date_range, sleepy_click, sleepy_select_visible_text, sleepy_send_keys


def search_for_cases(
        driver: WebDriver,
        config: CaseSearchConfig,
        timeout: int = 15,
    ) -> None:
    """Search for court cases.

    Parameters
    ----------
    driver : WebDriver
        Selenium webdriver.

    config : CaseSearchConfig
        Case search configurations.
    
    timeout : int
        Max seconds to wait for element to load.
        Defaults to 15.
    
    """
    # sleep
    min_sleep = config.min_sleep
    max_sleep = config.max_sleep

    # search setup
    court_department_selections = config.court_departments
    court_department_dropdown = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.NAME, "sdeptCd"))
    )
    sleepy_select_visible_text(court_department_dropdown, court_department_selections, min_sleep, max_sleep)

    court_division_selections = config.court_divisions
    court_division_dropdown = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.NAME, "sdivCd"))
    )
    sleepy_select_visible_text(court_division_dropdown, court_division_selections, min_sleep, max_sleep, before=False)

    court_location_selections = config.court_locations
    court_location_dropdown = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.NAME, "slocCd"))
    )
    sleepy_select_visible_text(court_location_dropdown, court_location_selections, min_sleep, max_sleep, before=False)

    results_per_page = config.results_per_page
    page_size_dropdown = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.NAME, "pageSize"))
    )
    sleepy_select_visible_text(page_size_dropdown, [results_per_page], min_sleep, max_sleep, before=False)

    # navigate to search by case type
    tab_row = WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.CLASS_NAME, "tab-row"))
    )

    selected_tab_text = ""
    for li in tab_row.find_elements(By.TAG_NAME, "li"):
        cls = li.get_attribute("class") or ""
        if "selected" in cls.split():
            try:
                selected_tab_text = li.find_element(By.TAG_NAME, "a").text.strip()
            except NoSuchElementException:
                selected_tab_text = ""

    if selected_tab_text != "Case Type":
        # use LINK_TEXT to find the tab anchor
        case_type_link = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Case Type"))
            )
        sleepy_click(case_type_link, min_sleep, max_sleep)

    start_date = config.start_date
    end_date = config.end_date

    # date-range inputs
    date_begin_input = WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.NAME, "fileDateRange:dateInputBegin"))
    )
    sleepy_send_keys(date_begin_input, start_date, min_sleep, max_sleep, before=False, tab=True)

    date_end_input = WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.NAME, "fileDateRange:dateInputEnd"))
    )
    sleepy_send_keys(date_end_input, end_date, min_sleep, max_sleep, before=False, tab=True)

    # advanced search setup
    case_type_selections = config.case_types
    case_type_select = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.NAME, "caseCd"))
    )
    sleepy_select_visible_text(case_type_select, case_type_selections, min_sleep, max_sleep, before=False)

    city_selections = config.cities
    city_select = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.NAME, "cityCd"))
    )
    sleepy_select_visible_text(city_select, city_selections, min_sleep, max_sleep, before=False)

    case_status_selections = config.statuses
    case_status_select = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.NAME, "statCd"))
    )
    sleepy_select_visible_text(case_status_select, case_status_selections, min_sleep, max_sleep, before=False)

    party_type_selections = config.party_types
    party_type_select = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.NAME, "ptyCd"))
    )
    sleepy_select_visible_text(party_type_select, party_type_selections, min_sleep, max_sleep, before=False)

    search_btn = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.NAME, "submitLink"))
    )
    sleepy_click(search_btn, min_sleep, max_sleep)


def get_search_coverage(driver: WebDriver, timeout: int = 15) -> float:
    """Attempt to find the fraction of results accessible by the query.

    Parameters
    ----------
    driver : WebDriver
        Selenium webdriver.

    timeout : int
        Max seconds to wait for element.

    Returns
    -------
    float
        Fraction of results accessible.
        Defaults to 1.0 if error.

    """
    try:
        # wait until the div is present
        notice_el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "srchResultNotice"))
        )

        # i.e. "Returning 100 of 150 records."
        text = notice_el.text.strip()

        # extract numbers with regex
        nums = re.findall(r"\d+", text)

        nums = re.findall(r"\d+", text)
        if len(nums) >= 2:
            returned, total = map(int, nums[:2])
            return returned / total if total else 1.0
        return 1.0
    except (ValueError, IndexError, NoSuchElementException, TimeoutException, ZeroDivisionError):
        return 1.0
    

def build_search_ranges(
    start_date: str,
    end_date: str,
    coverage: float,
    *,
    threshold: float = 0.999,  # tolerate tiny float error
) -> List[Tuple[str, str]]:
    """Return [(start,end)] if coverage is good enough, else [(d,d) ...]."""
    if coverage >= threshold or isclose(coverage, 1.0, rel_tol=0, abs_tol=1e-9):
        return [(start_date, end_date)]
    return [(d, d) for d in expand_date_range(start_date, end_date)]
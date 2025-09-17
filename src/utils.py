import json
import os
import random
import tempfile
import time

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import Select


def prompt_for_date_range() -> Tuple[str, str]:
    """Prompt user for a start and end date (mm/dd/yyyy), allowing two tries.

    Returns
    -------
    tuple[str, str]
        Valid (start_date, end_date) strings in mm/dd/yyyy format.

    Raises
    ------
    ValueError
        If both attempts fail or the date range is invalid.
    """
    for attempt in range(2):
        start_input = input("Start date (mm/dd/yyyy): ").strip()
        end_input = input("End date   (mm/dd/yyyy): ").strip()
        try:
            start_dt = datetime.strptime(start_input, "%m/%d/%Y")
            end_dt = datetime.strptime(end_input, "%m/%d/%Y")

            if end_dt < start_dt:
                raise ValueError("Start date must on or before end date")

            return start_input, end_input

        except ValueError as e:
            print(f"Invalid input: {e}. Please try again. ({1 - attempt} attempt(s) left)")

    raise ValueError("Failed to provide a valid date range after 2 attempts.")


def load_records(path: Path) -> Dict[str, Dict[str, Any]]:
    """Return a plain dict of records keyed by case number (case_number : str).
    
    Parameters
    ----------
    path : Path
        Path object to the records file.

    Returns
    -------
    Dict[str, Dict[str, Any]]
        Plain dict of records keyed by case_number (str).

    """
    if not path.exists():
        return {}
    
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, ValueError, OSError):
        return {}


def lookup_court_case(records: Dict[str, Dict[str, Any]], case_number: str) -> bool:
    """Lookup a court case in the records dictionary (keyed by case_number (str)).

    Parameters
    ----------
    records : Dict[str, Dict[str, Any]]
        Court case records dictionary keyed by case_number (str).
    
    case_number : str
        Case number corresponding to the CourtCase instance to lookup.

    Returns
    -------
    bool
        Whether or not the case is present in the records dict.

    """

    try:
        records[case_number]
        return True

    except KeyError:
        return False


def sleep_randomly(min_time: Union[int, float] = 0, max_time: Union[int, float] = 0) -> None:
    """Sleep for a random amount of time.

    Parameters
    ----------
    min_time : Union[int, float]
        Minimum number of seconds to sleep for.
    
    max_time : Union[int, float]
        Maximum number of seconds to sleep for.

    """
    time.sleep(random.uniform(*map(float, sorted((min_time, max_time)))))


def sleepy_click(web_element: WebElement, min_time: Union[int, float] = 0, max_time: Union[int, float] = 0, before: bool = True, after: bool = True) -> None:
    """Sleep for a random amount of time before and after clicking a web element.
    
    Parameters
    ----------
    web_element : WebElement
        Selenium WebElement to click.

    min_time : Union[int, float]
        Minimum number of seconds to sleep for.
    
    max_time : Union[int, float]
        Maximum number of seconds to sleep for.

    before : bool
        Whether or not to sleep before.
        Defaults to True.

    after : bool
        Whether or not to sleep after.
        Defaults to True.

    """
    if before:
        sleep_randomly(min_time, max_time)
    web_element.click()
    if after:
        sleep_randomly(min_time, max_time)


def sleepy_select_visible_text(web_element: WebElement, selections: list[str], min_time: Union[int, float] = 0, max_time: Union[int, float] = 0, before: bool = True, after: bool = True) -> None:
    """Sleep for a random amount of time before and after selecting one or more from a web element.

    Parameters
    ----------
    web_element : WebElement
        Selenium WebElement to select.

    selection : list[str]
        One or more visible option texts to select.

    min_time : Union[int, float]
        Minimum number of seconds to sleep for.
    
    max_time : Union[int, float]
        Maximum number of seconds to sleep for.

    before : bool
        Whether or not to sleep before.
        Defaults to True.

    after : bool
        Whether or not to sleep after.
        Defaults to True.

    """
    # wrap the web_element in a selenium select object
    select = Select(web_element)

    # deselect all
    if select.is_multiple:
        select.deselect_all()

    if before:
        sleep_randomly(min_time, max_time)

    for selection in selections:
        select.select_by_visible_text(selection)

    if after:
        sleep_randomly(min_time, max_time)


def sleepy_send_keys(
        web_element: WebElement,
        keys: str,
        min_time: Union[int, float] = 0,
        max_time: Union[int, float] = 0,
        before: bool = True,
        after: bool = True,
        tab: bool = False,
    ) -> None:
    """Sleep for a random amount of time before and after sending keys to a web element.

    Parameters
    ----------
    web_element : WebElement
        Selenium WebElement to click.

    keys : str
        Text to send to the web_element.

    min_time : Union[int, float]
        Minimum number of seconds to sleep for.
    
    max_time : Union[int, float]
        Maximum number of seconds to sleep for.

    before : bool
        Whether or not to sleep before.
        Defaults to True.

    after : bool
        Whether or not to sleep after.
        Defaults to True.

    tab : bool
        Whether or not to press tab after sending keys.
        Defaults to False.

    """
    web_element.clear()
    if before:
        sleep_randomly(min_time, max_time)
    web_element.send_keys(keys, Keys.TAB) if tab else web_element.send_keys(keys)
    if after:
        sleep_randomly(min_time, max_time)


def parse_init_action(text: str) -> str:
    """Return the substring after the first dash separator if present.

    Parameters
    ----------
    text : str
        Input string (e.g., "Efiled SP Summons and Complaint - Non-payment of Rent" 
        or "SP Transfer- No Cause").

    Returns
    -------
    str
        Substring after the first dash separator (e.g., "Non-payment of Rent" or "No Cause"),
        or the full string if no dash separator is found.

    """
    # try splitting on " - " first (space-dash-space)
    parts = text.split(" - ", 1)
    if len(parts) == 2:
        return parts[1]
    
    # if that didn't work, try splitting on "- " (dash-space)
    parts = text.split("- ", 1)
    if len(parts) == 2:
        return parts[1]
    
    # if no separator found, return the original text
    return text


def expand_date_range(start_date: str, end_date: str, date_format: str = "%m/%d/%Y") -> List[str]:
    """Expand a range of date strings into a list of day strings.
    
    Note: Both input and output date strings are to be formatted in accordance with the `date_format` parameter. 

    Parameters
    ----------
    start_date : str
        Range start date string.

    end_date : str
        Range end date string.

    date_format : str
        Date string format.
        Defaults to "%m/%d/%Y".

    Returns
    -------
    List[str]

    Example
    -------
    expand_date_range("09/01/2025", "09/03/2025")
    -> ["09/01/2025", "09/02/2025", "09/03/2025"]
    """
    start = datetime.strptime(start_date, date_format).date()
    end = datetime.strptime(end_date, date_format).date()

    days = []
    current = start
    while current <= end:
        days.append(current.strftime(date_format))
        current += timedelta(days=1)
    return days


def extract_span_texts(web_element: WebElement) -> List[str]:
    """Extract a list of non-empty text values from all <span> elements in a div.

    Parameters
    ----------
    web_element : WebElement
        The parent web lement to search within.

    Returns
    -------
    List[str]
        A list of strings, each the trimmed text content of a <span> element.
        Empty or whitespace-only spans are excluded.
    """
    return [s.text.strip() for s in web_element.find_elements(By.TAG_NAME, "span") if s.text.strip()]


def write_json_atomic(path: Path, data: Dict[int, Dict[str, Any]]) -> None:
    """Atomically write JSON to `path` (safe on POSIX/NTFS)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as tmp:
        json.dump(data, tmp, indent=2)
        tmp.flush()           # ensure bytes hit disk
        os.fsync(tmp.fileno())  # extra safety on crashes
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)  # atomic replace
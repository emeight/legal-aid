# src/cmds/impl/surf.py

from selenium.webdriver.remote.webdriver import WebDriver

from selenium.common.exceptions import InvalidArgumentException, WebDriverException

def access_url(driver: WebDriver, url: str) -> None:
    """Attempt to access a url via a selenium webdriver.

    Note: Selenium requires a fully qualified URL (i.e., "https://google.com").

    Parameters
    ----------
    driver: WebDriver
        Selenium webdriver.
    
    url : str
        Webpage to access.
    
    Raises
    ------
    InvalidArgumentException
        Raised when the provided url is invalid.  

    """
    # add https:// if the scheme is missing
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        driver.get(url)
    except (InvalidArgumentException, WebDriverException) as e:
        # log or re-raise with context
        raise InvalidArgumentException(f"Bad URL for driver.get: {url}") from e
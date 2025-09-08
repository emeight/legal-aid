# main.py

import os

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver

from src.utils import sleep_randomly

# load environment variables
load_dotenv()

MAIN_URL = os.getenv("MAIN_URL")

# setup the web driver
driver: WebDriver = webdriver.Chrome()

# access the website
driver.get(MAIN_URL)

sleep_randomly(5, 10)

driver.close()
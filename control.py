# control.py

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver

from src.cmds.core import dispatch_command


# load environment variables
load_dotenv()

# setup the web driver
driver: WebDriver = webdriver.Chrome()

keep_alive: bool = True
invalid_cmd_ctr: int = 0


while keep_alive:
    # prompt user for command
    cmd = input("Command: ")

    if cmd.upper == "EXIT" or "CLOSE" or "BREAK":
        # shutdown script
        keep_alive = False
        driver.quit()
        break

    try:
        dispatch_command(driver, cmd)
        # command successful, reset invalid count
        invalid_cmd_ctr = 0
    except KeyError:
        invalid_cmd_ctr += 1

        # if more than two commands
        if invalid_cmd_ctr > 2:
            print("Invalid command, shutting down.")
            # shutdown script
            keep_alive = False
            driver.quit()
            break
        else:
            # continue to next loop
            print("Invalid command, please retry...")
            continue

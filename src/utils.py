# src/utils.py

import random
import time

from typing import Union


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

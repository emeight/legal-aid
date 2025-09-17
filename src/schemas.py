from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Literal, Optional


@dataclass
class CaseSearchConfig:
    # initial
    court_departments : List[str]
    court_divisions : List[str]
    court_locations : List[str]
    results_per_page : Literal["25", "50", "75"]
    # dates
    start_date : str
    end_date : str
    # advanced
    case_types : List[str]
    cities : List[str]
    statuses : List[str]
    party_types : List[str]
    # sleep range (seconds)
    min_sleep: int
    max_sleep: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert the CaseSearchConfig instance into a plain dictionary.

        Returns
        -------
        Dict[str, Any]
            Dictionary containing all dataclass fields and values.
        """
        return asdict(self)


@dataclass
class CourtCase:
    # unique identifier
    case_number : str
    status : str
    # link to "Case Details" page
    file_date : str
    primary_party : str
    # advanced case data
    defendant : Optional[str]
    plaintiff : Optional[str]
    init_action : Optional[str]
    address : Optional[str]
    zipcode : Optional[str]
    # time data
    created_at : str 
    updated_at : str

    def to_dict(self) -> Dict[str, Any]:
        """Convert the CourtCase instance into a plain dictionary.

        Returns
        -------
        Dict[str, Any]
            Dictionary containing all dataclass fields and values.
        """
        return asdict(self)

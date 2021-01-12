This file contains the code and functions to parse and modify the testorder file.
"""


from typing import NamedTuple

class TestorderEntry(NamedTuple):
    test_status: str
    test_type: str
    test_name: str
    version: str
    permanent: bool=False
    nulltest: bool=False
    comment: bool= False
    path: str=""
    remark: str=""
    





class Testorder(list):
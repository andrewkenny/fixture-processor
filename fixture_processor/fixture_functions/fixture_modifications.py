"""
This script contains all of the functions used for
adding / removing wires, and
adding / modifying inserts.
"""

from tkinter import messagebox as mb
import csv
import logging
import re

from ..options_lib import fixture_processing_options
from ..helper_functions import error_message_header

from . import fixture_maths as fm
from . import extract_wires as ew

from typing import NamedTuple, Optional


fp_logger = logging.getLogger('fixture_processing.fixture_modifications')

COLUMN_ERROR = """\
    Error when parsing CSV line in {filename}:
    {line_num}: '{raw_line}'.
    Wrong number of values ({value_count}).\
"""




NO_WIRE_ERROR = """\
    The following line in 'remove_wires.csv'
    did not match any wires in this project.
    {0}:     '{1}'.
    Please ensure no mistake has been made.
"""




NO_INSERT_ERROR = """\
    token {0} on line {1}
    of "add_wires.csv"
    {1}:    '{2}'.
    Does not match any Inserts.
"""

EXTRA_INSERTS_ERROR = """\
    token {0} on line {1}
    of "add_wires.csv"
    {1}:    '{2}'.
    Matches more than one insert ({3} in total)
"""

BOTH_INSERTS_ERROR = """\
    The following line in 'add_wires.csv'
    {0}:    '{1}'.
    attempted to add a wire from the top
    to the bottom of the fixture.
    (Unable to add wire)
"""

TOP_AND_BOTTOM_ERROR = """\
    The following line in 'add_wires.csv'
    {0}:    '{1}'.
    is attempting to add a wire to the top
    AND bottom of the fixture.
    Please check 'fixture.o" for errors.
"""



NO_MATCH_ERR = """\
    Error in the {2} token
    on line {0} of '{3}'
    {0}:    '{1}'.
    Check syntax rules and edit.
"""

MULTIPLE_MATCH_ERR = """\
    Error in the {2} token
    on line {0}
    {0}:    '{1}'.
    token incorrectly applies to more than one rule.
    Check syntax rules and edit.
"""


MULTIPLE_MOD_ERROR = """\
    The following line in 'modify_inserts.csv'
    {0}:    '{1}'.
    is describing an insert, described previously.
    An insert can only be modified (offset) once.
"""

NO_INSERT_MOD_ERROR = """\
    The following line in 'modify_inserts.csv'
    {0}:    '{1}'.
    does not match any inserts in the fixture.
    Please check and modify.
"""

MOD_INSERT_METHOD_ERROR = """\
    The following line in 'modify_inserts.csv'
    {line_num}:    '{raw_line}'.
    does not describe a valid insert mod. ({method})
    Allowed mods: 
    {allowed_methods_str}
"""

MOD_INSERT_WRONG_UNITS = """\
    The following line in 'modify_inserts.csv'
    {line_num}:    '{raw_line}'.
    does not describe a valid coordinate unit. ({units})
    Allowed mods: 
    {allowed_units_str}
"""

MOD_INSERT_TESTJET_NAME = """\
    The following line in 'modify_inserts.csv'
    {line_num}:    '{raw_line}'.
    specifically '{insert_name}'
    is not an integer describing a 3070 module.
    (0, 1, 2, 3)
"""

MOD_INSERT_INVALID_COORD = """\
    The following line in 'modify_inserts.csv'
    {line_num}:    '{raw_line}'.
    The  {axis} location / {axis} offset 
    must contain decimal number. ({value}).
"""

MOD_EXISTING_COORD = """\
    The following line in 'modify_inserts.csv'
    {line_num}:    '{raw_line}'.
    Is trying to add / move an insert to where an
    insert already exists.
"""


WILDCARD_DESCRIPTION = """\
! The wildcard '*' matches all pins and transfers,
! but not terminals.
! Do not place a wildcard in the from and to column.
!\
"""

EXPLICIT_DESCRIPTION = """\
! A pin / brc. e.g. 'brc 20101' or 'brc205123'
! A Probe. e.g. 'P123'
! A Transfer. e.g. 'T123'
!\
"""

EXPLICIT_PS_DESCRIPTION = """\
! A power supply plus function, e.g.
! PS1+force1
! PS2-force2
! PS16-sense
! PS5+f1
!\
"""

GENERAL_PS_DESCRIPTION = """\
! A power supply + or - e.g.
! PS1+
! PS2-
! PS16-
! PS5+
!\
"""

CUSTOM_DESCRIPTION = """\
! A custom transfer described in "modify_inserts.csv" e.g.
! #%board_detect_1
! #gate_closed1
!
! A testjet transfer described in "modify_inserts.csv" e.g.
! TJ0_2
! TJ1_4
! TJ2_5
! TJ3_6
! 
"""

COMPLEX_DESCRIPTION = """\
! A {name} at a node. e.g. '{keyword}{{+5V}}' or '{keyword}{{1%TDI}}'
!     or '{keyword}{{1:TDO}}'
! A {name} at a node for any board number;
!     e.g. '{keyword}<#>{{+5V}}' or '{keyword}<#>{{TMS}}'
! A {name} at a node across a range of board numbers
!     e.g. '{keyword}<1-5>{{+5V}}' or '{keyword}<1-5>{{TCK}}'
!\
"""

POWER_SUPPLY_DESCRIPTION = """\
! A Power supply(PS). e.g. 'PS1+', 'PS3-'
! also allowed: 'PS1+F' (for force)
! also allowed: 'PS1+S' (for sense)!
!\
"""

TARGET_FLAGS_DESCRIPTION = """\
! target_flags can be: 
! blank, removal is applied to all targets, e.g. wiring machine and verifier. 
! 'W' or 'w', wires are only removing from the wiring machine target
! 'V' or 'v', wires are only removing from the verifier target
! 'T' or 't', wires are only removing from the verifier top target (RFU)
! Targets can be mixed, eg 'WV' or 'wt'. 
!\
"""


# todo - implement the pin, probe, transfer removal rules.
#        define rules for GP only, GND only, ASRU_GND only,
#                         TESTPIN only.

# a namedtuple defining the pins of a power supply.
class PowerSupply(NamedTuple):
    force1: fm.PinID
    force2: fm.PinID
    sense: fm.PinID

    @property
    def f1(self):
        return self.force1

    @property
    def f2(self):
        return self.force2

    @property
    def s(self):
        return self.sense


def power_supply(force1: str, force2: str, sense: str):
    """
    Converts string args into
    the PinID type from fixture_maths.
    """

    return PowerSupply(fm.PinID(force1), fm.PinID(force2), fm.PinID(sense))


IMP_PS_PATTERN = \
    r"""
    (?P<power_supply>
        ps             # ps indicates a power supply comparison
        \d{1,2}        # 1 or 2 decimal numbers (ps5 or ps12)
        [+-]           # must be followed by a + or -
    )
    (?P<pin>
       force1|f1|  # these options describe
       force2|f2|  # which pin to be
       sense|s     # matched.
    )
"""


class WireModFlags(NamedTuple):
    remove: bool = True
    colour: Optional[str] = None
    gauge: Optional[str] = None

    def validate_remove(self, raw_data):
        if raw_data not in ["True", "False"]:
            msg = \
            f"    The following line in 'remove_wires.csv'\n" \
            f"    has in incorrect 'remove' value.\n"         \
            f"    {line_num}:     '{line}'.\n"                \
            f"    The value after 'remove=' must be\n"        \
            f"    'True' or 'False'\n"
            mb.showerror("ERROR", msg)

        return eval(raw_data)

    def validate_colour(self, raw_data):
        return raw_data

    def validate_gauge(self, raw_data):
        return raw_data


class WireAddFlags(NamedTuple):
    colour: str = "Blue"
    gauge: str = "28"

    def validate_colour(self, raw_data):
        return raw_data

    def validate_gauge(self, raw_data):
        return raw_data

    def _to_WireInfo(self, length):

        return ew.WireInfo(length, self.gauge, self.colour)


class InsertModFlag(NamedTuple):
    method: str
    coord: ew.CoordTuple

    # only valid when adding new transfer.
    # ignored when applying offsets to inserts/
    # moving inserts
    top: bool
    bottom: bool
    
    # only valid when adding blocks of transfer.
    length: int=None
    direction: str=None


def define_power_supplies():
    """
    This function returns a dict containing
    brc lookups of power supplies.
    """

    power_supply_dict = {}

    # Bank 2, Module 3
    power_supply_dict["PS1-"] = power_supply("21301", "21302", "21305")
    power_supply_dict["PS1+"] = power_supply("21303", "21304", "21306")
    power_supply_dict["PS2-"] = power_supply("21307", "21308", "21311")
    power_supply_dict["PS2+"] = power_supply("21309", "21310", "21312")
    power_supply_dict["PS3-"] = power_supply("21313", "21314", "21317")
    power_supply_dict["PS3+"] = power_supply("21315", "21316", "21318")
    power_supply_dict["PS4-"] = power_supply("21319", "21320", "21323")
    power_supply_dict["PS4+"] = power_supply("21321", "21322", "21324")

    # Bank 2, Module 2
    power_supply_dict["PS5-"] = power_supply("20101", "20102", "20105")
    power_supply_dict["PS5+"] = power_supply("20103", "20104", "20106")
    power_supply_dict["PS6-"] = power_supply("20107", "20108", "20111")
    power_supply_dict["PS6+"] = power_supply("20109", "20110", "20112")
    power_supply_dict["PS7-"] = power_supply("20113", "20114", "20117")
    power_supply_dict["PS7+"] = power_supply("20115", "20116", "20118")
    power_supply_dict["PS8-"] = power_supply("20119", "20120", "20123")
    power_supply_dict["PS8+"] = power_supply("20121", "20122", "20124")

    # Bank 1, Module 1
    power_supply_dict["PS9-"] = power_supply("12378", "12377", "12374")
    power_supply_dict["PS9+"] = power_supply("12376", "12375", "12373")
    power_supply_dict["PS10-"] = power_supply("12372", "12371", "12368")
    power_supply_dict["PS10+"] = power_supply("12370", "12369", "12367")
    power_supply_dict["PS11-"] = power_supply("12366", "12365", "12362")
    power_supply_dict["PS11+"] = power_supply("12364", "12363", "12361")
    power_supply_dict["PS12-"] = power_supply("12360", "12359", "12356")
    power_supply_dict["PS12+"] = power_supply("12358", "12357", "12355")

    # Bank 1, Module 0
    power_supply_dict["PS13-"] = power_supply("11178", "11177", "11174")
    power_supply_dict["PS13+"] = power_supply("11176", "11175", "11173")
    power_supply_dict["PS14-"] = power_supply("11172", "11171", "11168")
    power_supply_dict["PS14+"] = power_supply("11170", "11169", "11167")
    power_supply_dict["PS15-"] = power_supply("11166", "11165", "11162")
    power_supply_dict["PS15+"] = power_supply("11164", "11163", "11161")
    power_supply_dict["PS16-"] = power_supply("11160", "11159", "11156")
    power_supply_dict["PS16+"] = power_supply("11158", "11157", "11155")

    # Bank 2, Module 3
    power_supply_dict["PS17-"] = power_supply("21343", "21344", "21347")
    power_supply_dict["PS17+"] = power_supply("21345", "21346", "21348")
    power_supply_dict["PS18-"] = power_supply("21353", "21354", "21357")
    power_supply_dict["PS18+"] = power_supply("21355", "21356", "21358")

    # Bank 2, Module 2
    power_supply_dict["PS19-"] = power_supply("20143", "20144", "20147")
    power_supply_dict["PS19+"] = power_supply("20145", "20146", "20148")
    power_supply_dict["PS20-"] = power_supply("20153", "20154", "20157")
    power_supply_dict["PS20+"] = power_supply("20155", "20156", "20158")

    # Bank 1, Module 1
    power_supply_dict["PS21-"] = power_supply("12336", "12335", "12332")
    power_supply_dict["PS21+"] = power_supply("12334", "12333", "12331")
    power_supply_dict["PS22-"] = power_supply("12326", "12325", "12322")
    power_supply_dict["PS22+"] = power_supply("12324", "12323", "12358")

    # Bank 1, Module 0
    power_supply_dict["PS23-"] = power_supply("11136", "11135", "11132")
    power_supply_dict["PS23+"] = power_supply("11134", "11133", "11131")
    power_supply_dict["PS24-"] = power_supply("11126", "11125", "11122")
    power_supply_dict["PS24+"] = power_supply("11124", "11123", "11158")
    return power_supply_dict


def get_wire_removal_instructions() -> str:

    # pin_description = COMPLEX_DESCRIPTION.format(name="pin", keyword="pin")
    # transfer_description += COMPLEX_DESCRIPTION.format(name="Transfer", keyword="T")
    # probe_description += COMPLEX_DESCRIPTION.format(name="Probe", keyword="P")

    instructions = f"""\
! List the wires you want the wiring operator to skip
! When wiring the fixture.
!
! Format: 
! From, To[, target=target_flags]
! Note, all lines and nodes will be made lower case.
! Note, all white space will be removed.
! Note, a from pin/brc/probe, to pin/brc/probe entry can be in any order.
!
! The following can go in To or From:
!
{WILDCARD_DESCRIPTION}
{EXPLICIT_DESCRIPTION}
{EXPLICIT_PS_DESCRIPTION}
{GENERAL_PS_DESCRIPTION}
!
! Target_flags is only required when you want to restrict the wire removal
! to a particular target, ie wiring machine (The flag is w), verifier (The flag is v)
! As future targets are created this text file will reflect the flags.
!
! If the wire to be removed cannot be found in the wires file,
! The program will report an error.
"""

    return instructions


def get_inserts_modifier_instructions() -> str:
    """
    When the user opens the 'modify_inserts.csv' file, it needs to contain
    instructions informing the operator how to describe the inserts they
    want to modify.

    full features will be:
    offset insert,
    new insert

    but the user will only be told about the currently implented features.
    """

    instructions = """\
! List all of the inserts you wish to modify.
! These modifications will apply to the wires and inserts
! files using for wiring and verifiying the fixture.
!
! Note that brc modifications are not applied to the verifier target.
!
! Format:
!     offset, insert_name, units, x_offset, y_offset[, target]
!     move, insert_name, units, x_location, y_location[, target]
!
!     transfer, insert_name, units, x_location, y_location[, target]
!     top_transfer, insert_name, units, x_location, y_locatation[, target]
!     bottom_transfer, insert_name, units, x_location, y_locatation[, target]
!
!     testjet, module, units, x_location, y_location[, target]
!
!     single_row, direction, length, insert_name, units, x_location, y_locatation[, target]
!     double_row, direction, length, insert_name, units, x_location, y_locatation[, target]
!
! offset tells the program that you wish to offset an insert (by x_offset, y_offset)
! move tells the program that you wish to move an insert to a new location. (x_location, y_location)
!
! for offset and move, insert_name should be replaced by the name 
!                of the insert you wish to apply the offset to;
!                eg T123, or P123, or brc20501
!
! for transfer, insert_name will be the name of the transfer as described in the fixture plot,
! and as refered to when adding custom wires.
!
! testjet is an advanced form of bottom_transfer. By providing the module,  and the location
! of pin 1, bottom transfer are generated by the software, accounting for pin offsets
!
! single_row and double_row are helpers for creating rows of transfer.
!     The direction can be h[orizontal] or v[ertical],
!     The length must be an integer number
!     And Insert name will precede the pin number, eg r_feasa_1
!
!
! units will be either mils (10 thousands of an inch) or mm (milimetres)
!
! x_offset, x_location, y_offset, y_locatation have to be base 10 integers / floats.
! when defining offsets, or coordinates;
! x would increase if the new insert / offset insert was moving right.
! x would decrease if the new insert / offset insert was moving left.
! y would increase if the new insert / offset insert was moving upwards.
! y would decrease if the new insert / offset insert was moving downwards.
!                   
!
"""

    return instructions


def get_wire_addition_instructions() -> str:
    """
    When the user opens "add_wires.csv" it needs to
    contain instructions telling them how to
    describe the wires they want to add.
    """

    instructions = f"""\
! List the extra wires you want the wiring operator to 
! add to the fixture.
!
! Format:
! From, To, colour[, target=target_flags][, gauge=gauge]
! Note, all lines and nodes will made lower case.
! Note, all whitespace will be removed.
! Note, It is strongly recomended that the from and to follow a logical order,
! That is:
! From BRC - To BRC
! From BRC - To Probe / Transfer Probe
! From Transfer Probe - to Top Probe.
!
! deviating from the above may cause problems with automatic wiring machines.
!
! The following can go in To or From:
!
{EXPLICIT_DESCRIPTION}
{EXPLICIT_PS_DESCRIPTION}
{CUSTOM_DESCRIPTION}
!
!
! To describe the colour, the format is:
!  'colour=XX' where XX is the required colour, eg red, blue, black.
!
!
! Target_flags is only required when you want to restrict the wire additions
! to a particular target, ie wiring machine (The flag is w), verifier (The flag is v)
! As future targets are created this text file will reflect the flags.
!
! If the wire can not be added to the fixture,
! The program will report an error.
!
!
! To describe the gauge, the format is:
! 'gauge=XX' Where XX is the required gauge, eg: 30, 28, 26.
!
! If gauge is not provided, the wire gauge will be assumed to be 28awg
!
! Future updates of this program may have smarter methods 
! of automatically calculating the gauge.
!

"""
    return instructions


def validate_remove_flags(raw_remove_flags, line_num, line):
    """
    Ensures that the remove flags the operator has provided
    are legal and relevent.
    returns True if flags are valid, returns False if flags are invalid.
    """

    legal_flags = ["w", "v", "t", "g"]

    # flags are case insenstive
    # spaces are allowed but not required.
    remove_flags = raw_remove_flags.lower().replace(" ", "")

    # more than one flag
    for flag in legal_flags:
        flag_count = remove_flags.count(flag)

        if flag_count > 1:
            msg = \
                f"The target flag: '{flag}' occurs more than once on line {line_num}" \
                f"of 'remove_wires.csv'" \
                f"{line_num}:     '{line}'." \
                f"Only one target flag of each type is required."

            mb.showerror("ERROR", msg)
            return False

        # remove the tested flag, so string can be checked for
        # disallowed characters.
        remove_flags.replace(flag, "")

    return True


def generate_explicit_power_supply_comparison(argument):
    """
    an explicit power supply has to refer
    to the power supply pin by fuction, eg
    PS1+sense
    PS5-force1
    """

    token = argument.strip()

    # ensure the token is indeed
    # describing a power supply
    if not token.startswith("ps"):
        return None

    token_match = re.fullmatch(IMP_PS_PATTERN, token, re.VERBOSE)
    if token_match is None:
        err_msg = \
            f"    invalid power supply description.\n" \
            f"    '{token}'\n" \
            f"    Check syntax rules and edit."
        raise ValueError(err_msg)


    power_supply_lookup = token_match.group("power_supply")
    pin_lookup = token_match.group("pin")

    power_supply_dict = define_power_supplies()

    try:
        power_supply_tuple = power_supply_dict[power_supply_lookup.upper()]
    except LookupError:
        err_msg = \
            f"    {power_supply_lookup} / {power_supply_lookup.upper()}\n" \
            f"    is not a valid power supply.\n"
        raise ValueError(err_msg)

    # get the brc of the power supply.
    power_supply_pin = getattr(power_supply_tuple, pin_lookup)

    def brc_checker(insert):
        """
        returns True if the given brc given by the user config
        matches the brc given in the inserts data structure.

        outer arguments:
            token

        """

        # insert is None for terminal inserts.
        if insert is None:
            return False

        # return false if insert is not a pin / insert
        if insert.insert_type not in ["Pin", "Offset"]:
            return False

        # The brc name (as described in the fixture file (and wirelist)
        # is stored in fix_id.
        fix_id = insert.fix_id

        # a fix_id that is a string means there was a lookup error.
        if isinstance(fix_id, str):
            return False

        return fix_id.brc == power_supply_pin

    return brc_checker


def generate_general_power_supply_comparison(argument):
    """
    Only for use when removing wires, from the fixture,
    this function allows the whole power supply wires
    to be removed.
    """

    token = argument.strip()

    # ensure the token is indeed describing a
    # power supply
    if not token.startswith("ps"):
        return None

    # if engineer describes explicit location, use
    # explicit function.
    if re.fullmatch(IMP_PS_PATTERN, token, re.VERBOSE):
        return generate_explicit_power_supply_comparison(argument)

    power_supply_dict = define_power_supplies()
    try:
        power_supply_tuple = power_supply_dict[token.upper()]
    except LookupError:
        err_msg = \
            f"    {power_supply_lookup} / {power_supply_lookup.upper()}\n" \
            f"    is not a valid power supply.\n"
        raise ValueError(err_msg)

    def brc_checker(insert):
        """
        returns True if one of the BRCs described by the power supply
        statement match the current insert.
        """

        # insert is None for terminal inserts.
        if insert is None:
            return False

        # return false if insert is not a pin / insert
        if insert.insert_type not in ["Pin", "Offset"]:
            return False

        # The brc name (as described in the fixture file (and wirelist)
        # is stored in fix_id.
        fix_id = insert.fix_id

        # a fix_id that is a string means there was a lookup error.
        if isinstance(fix_id, str):
            return False

        return any(fix_id.brc == power_supply_pin
                   for power_supply_pin
                   in power_supply_tuple)

    return brc_checker


def generate_wildcard_comparison(argument):
    # A wildcard entry means that the checker matches
    # all insert entries, except for terminals.

    # ensure that whitespaces does not affect parsing.
    token = argument.strip()

    all_but_terminals = "*"
    all_and_terminals = "*t"

    if token not in [all_but_terminals, all_and_terminals]:
        return None

    if token == all_and_terminals:
        return lambda insert, brc: True
    else:
        return lambda insert: insert is not None


def generate_brc_comparison(argument):
    """
    if the argument is a brc pin,
    that is:
    starts with brc,
    has a 5-6 length number sequence
    which begins with a 1 or a 2.
    """

    # ensure the argument does indeed start with brc:
    # none means that this rule is invalid.
    if not argument.startswith("brc"):
        return None

    # if it does, remove the brc text leaving the rest of the data
    token = fm.PinID(argument.replace("brc", "", 1))


    # ensure the user inputted brc token is correct, with no errors.
    for method_name, err_msg in token.validation_checks:

        # the method name is the method used to validate
        # part of the token. The err_message should be
        # displayed if the method returns False.
        if not getattr(token, method_name):

            raise(err_msg)

    def brc_checker(insert):
        """
        returns True if the given brc given by the user config
        matches the brc given in the inserts data structure.

        outer arguments:
            token

        """

        # insert is None for terminal inserts.
        if insert is None:
            return False

        # return false if insert is not a pin / insert
        if insert.insert_type not in ["Pin", "Offset"]:
            return False

        # The brc name (as described in the fixture file (and wirelist)
        # is stored in fix_id.
        fix_id = insert.fix_id

        # a fix_id that is a string means there was a lookup error.
        if isinstance(fix_id, str):
            return False

        return fix_id.brc == token

    return brc_checker


def generate_probe_comparison(argument):
    """
    If the argument is a probe name,
    That is T123 or P123,
    """

    # ensure the argument starts with p or 4 (argument is made lower case for easier parsing.
    if not argument.startswith(("t", "p")):
        return None

    # ensure the argument is an explicit probe / transfer.
    probe_match = re.fullmatch(r"(p|t)\d+", argument)

    if probe_match is None:
        return None

    token = argument.upper()


    def probe_checker(insert):
        """
        returns True if the probe described in the user config
        matches the probe name in the insert data structure

        outer arguments:
            token

        """

        # insert is None for terminal inserts.
        if insert is None:
            return False

        # extract the fixture id
        # (The name of the insert in the fixture file)
        fix_id = insert.fix_id

        # only strings are accepted.
        if not isinstance(fix_id, str):
            return False

        return fix_id == token

    return probe_checker


def generate_custom_transfer_comparison(argument):
    """
    If the argument is a custom transfer,
    eg custom1%gnd
    """

    # ensure the argument starts with p or 4 (argument is made lower case for easier parsing.
    if not argument.startswith(("$", "tj", "#")):
        return None

    token = argument



    def custom_transfer_checker(insert):
        """
        returns True if the probe described in the user config
        matches the probe name in the insert data structure

        outer arguments:
            token

        """

        # insert is None for terminal inserts.
        if insert is None:
            return False

        # extract the fixture id
        # (The name of the insert in the fixture file)
        fix_id = insert.fix_id

        # only strings are accepted.
        if not isinstance(fix_id, str):
            return False

        return fix_id.lower() == token

    return custom_transfer_checker


def join_token_functions(token_functions):

    from_checker, to_checker = token_functions

    def check_wire(from_insert, to_insert):
        """
        Check inserts in both directions to account for:
        PS1+, pin{+5V}
        but for some reason the +5V BRC is in the *from* section.
        """
        original_match = from_checker(from_insert) and to_checker(to_insert)
        if original_match:
            return True

        return from_checker(to_insert) and to_checker(from_insert)

    return check_wire


def process_flags(csv_flags, flags, filename, line_num, raw_line, target):
    """
    This function looks through the user provided flags
    in the csv file, performs validation, and updates the
    flags namedtuple.
    """

    continue_flag = False
    break_flag = False

    # a list of all the possible fields that may appear
    flag_fields = list(flags._fields) + ["target"]

    # a dict to make a note of the found flags.
    encounted_flags = {name: False for name in flag_fields}

    for raw_item in csv_flags:
        item = raw_item.lower()
        # This flag is set to True if the element
        # is expected and handled.
        # An error is raised if this is still False,
        # due to unexpected element.
        item_handled = False

        for flag_name in flag_fields:

            flag_condition = f"{flag_name}="
            validation_method = f"validate_{flag_name}"
            if item.startswith(flag_condition):
                item_handled = True
                # ensure this hasnt happened before.
                if encounted_flags[flag_name]:
                    err_msg = \
                        f"    The flag: '{flag_name}' occurs more than once\n" \
                        f"    Only one target flag of each type is required.\n"
                    raise ValueError(err_msg)
                else:
                    encounted_flags[flag_name] = True

                if flag_name == "target":
                    target_flags = item.replace("target=", "", 1).lower()

                    # validate the flags.
                    if not validate_remove_flags(target_flags, line_num, raw_line):
                        return None

                    # the first char is used to compare
                    flag_check = target[0].lower()
                    if flag_check not in target_flags:
                        continue_flag = True
                        break_flag = True
                        break

                else:
                    # get the data from the csv element.
                    raw_data = item.replace(
                        flag_condition, "", 1).strip().strip("\"'").title()
                    data = getattr(flags, validation_method)(raw_data)
                    kwargs = {flag_name: data}
                    flags = flags._replace(**kwargs)
                break
        else:
            # if this is reached, invalid flag.
            err_msg = \
                f"    '{flag_name}' of is not a valid flag\n" \
                f"    Double check instructions."
            raise ValueError(err_msg)

        if break_flag:
            break

    # Only performed on wire modification / removal
    if hasattr(flags, "remove"):
        modification_flags = [value for key, value in encounted_flags.items()
                              if key != "remove"]

        # if replace is true, no other flags can be set. (except target)
        # if replace is false, one of othe other flags must be set. (except target)
        if flags.remove and any(modification_flags):
            err_msg = "    Attempted to remove a wire, and modify it.\n" \
                      "    If attempting to modify wire, ensure statement\n" \
                      "    contains 'remove=False'"
            raise ValueError(err_msg)

        # if replace is false, one of othe other flags must be set. (except target)
        if not flags.remove and not any(modification_flags):
            err_msg = "    Has not been flagged for removal or\n" \
                      "    modification. Double check.\n"
            raise ValueError(err_msg)

    return flags, continue_flag

def get_custom_functions(fixture_dir, target, filename, 
                         description, generate_functions):
    """
    This function opens the specified csv,
    performs validation on the inputs,
    
    Then returns a matching function
    """
    

    csv_path = fixture_dir / filename
    

    if not csv_path.exists():
        err_msg = f"    Cannot find '{filename}'\n"\
                  f"    '{filename}' is required for\n"\
                  f"    '{description}'. "

        raise ValueError(err_message)
        
    # get the contents of the csv, and store it to list of lines.
    with csv_path.open(newline="") as remove_wires:

        # ensure every line is lower case.
        line_list = [line.lower() for line in remove_wires.readlines()]
        
    # remove all spaces from the lines prior to csv processing.
    csv_line_list = list(csv.reader(line.replace(" ", "") for line in line_list))

    # convert the csv entries into a dict of functions,
    # and also get a flag which gets us to skip a target.
    try:
        return_value = generate_functions(
            csv_line_list, line_list, target, filename)
    except ValueError as err:
        raise ValueError(str(err))
        
    if return_value is None:
        return None
    
    function_dict, skip_target = return_value

    # give warning if function_dict is empty
    if function_dict == dict() and not skip_target:
        err_msg = f"    '{filename}' does not contain\n"\
                  f"    Any wire descriptions.\n" \
                  f"    Uncheck '{description}', or \n"\
                  f"    Add valid entries."
        raise ValueError(err_message)

    return function_dict




def generate_remove_wire_functions(csv_line_list, line_list, target, filename):
    """
    This function is intended to perform basic validation
    on a removal argument. It will not check whether or not
    the node/transfer/probe/brc_pin/power supply is present.
    """

    # a list containing the wire checking functions.
    # each function will see if the wire matches
    function_dict = {}

    from_list = [generate_wildcard_comparison,
                 generate_brc_comparison, generate_probe_comparison,
                 generate_general_power_supply_comparison]

    to_list = from_list.copy()


    error_header_func = error_message_header(filename)

    # this flag goes True if there are entries,
    # but due to target selection, they have been skipped.
    skip_target = False

    for line_num, (row, raw_line) in enumerate(zip(csv_line_list, line_list), 1):
        error_header = error_header_func(line_num, raw_line)


        line = raw_line.strip()
        raw_line = raw_line.rstrip()
        # skip blank lines, and comments
        if not line or line.startswith("!"):
            continue

        # create a flags variable.
        flags = WireModFlags()
        value_count = len(row)
        value_range = range(2, 4 + len(flags))

        # skip lines with too many or too fiew values
        if value_count not in value_range:
            err_msg = error_header + f"Wrong number of values ({value_count})."
            raise ValueError(err_msg)

        # extract the from and to token, stripping them of l and r
        # whitespace.
        from_token, to_token = [value.strip() for value in row[:2]]
        csv_flags = [value.strip() for value in row[2:]]
        
        try:
            processed_flags_return = process_flags(
                csv_flags, flags, filename, line_num, raw_line, target)
        except ValueError as err:
            raise ValueError(error_header + str(err))
            
        flags, continue_flag = processed_flags_return

        if continue_flag:
            skip_target = True
            continue

        # is the to and from token wilcard *,
        if (from_token.rstrip("T"), to_token.rstrip("T")) == ("*", "*"):
            err_msg = error_header + \
                f"    Wildcard can only appear once per line. \n"\
                f"    (A Wildcard for both 'From' and 'To' would match all wires!)"
            raise ValueError(err_msg)

        loop_vars = (["from", "to"],
                     [from_token, to_token],
                     [from_list, to_list])

        token_functions = []
        for name, token, func_list in zip(*loop_vars):

            # now generate function matcher.
            checker_list = []
            for func in func_list:
                try:
                    result = func(token)
                except ValueError as err:
                    err_msg = error_header + str(err)
                    raise ValueError(err_msg)
                else:
                    if result is None:
                        continue
                
                    if checker_list:
                        err_msg = \
                            f"    The {name} token matched more than one matching function!\n"\
                            f"    Check syntax rules and edit."
                        raise ValueError(error_header + err_msg)
                
                    checker_list.append(result)


            # a blank checker_list means a problem with the token.
            if not checker_list:
                err_msg = error_header + \
                    f"    The {name} token did not generate any matching functions\n"\
                    f"        Check syntax rules and edit."
                raise ValueError(err_msg)



            # There should be only one function now,
            # stored in a list for future processing.
            token_functions.append(checker_list[0])

        # add the wire checking function to a list.
        function_dict[join_token_functions(
            token_functions), flags] = (line_num, line)

    return function_dict, skip_target




def generate_insert_modification_functions(csv_line_list, line_list, target, filename):
    """
    This function is intended to perform basic validation on an
    insert modification argument. It will not check whether or not
    the insert is present.
    """

    # a list containing the insert checking functions.
    # each function will see if the insert matches
    function_dict = {}

    insert_match_list = [generate_brc_comparison, generate_probe_comparison]


    error_header_func = error_message_header(filename)

    # This flag goes True if there are entries,
    # but due to target selection, they have been skipped.
    skip_target = False


    acceptable_directions = ["h", "v", "horizontal", "vertical"]

    limited_transfer_methods = ["top_transfer", "bottom_transfer", "testjet"]
    block_transfer_methods = ["single_row", "double_row"]
    transfer_methods = ["transfer"] + limited_transfer_methods + block_transfer_methods

    for line_num, (row, raw_line) in enumerate(zip(csv_line_list, line_list), 1):
        error_header = error_header_func(line_num, raw_line)


        line = raw_line.strip()
        raw_line = raw_line.rstrip()
        top, bottom = True, True
        length, direction = 0, None
        
        # if True, the location will be provided later.
        future_location = False
        

        # skip iblank lines and comments
        if not line or line.startswith("!"):
            continue

        # how does the user wish to modify an insert?
        method = row[0]
        allowed_methods = ["offset", "move", "new"] + transfer_methods


        if method not in allowed_methods:
            err_msg = error_header + \
                f"    '{method}' does not describe a valid insert mod\n"\
                f"    Allowed mods: \n"
            line_len = 5    
            for i in range(0, len(allowed_methods), line_len):
                err_msg += f"    ({', '.join(allowed_methods[i:i + line_len])})\n"

            raise ValueError(err_msg)

        if method in ["offset", "move"] + transfer_methods:
            value_count = len(row)
            
            if method in block_transfer_methods:
                value_range = range(7, 9)
            else:
                value_range = range(5, 7)

            if value_count not in value_range:
                err_msg = error_header + f"Wrong number of values ({value_count})."
                raise ValueError(err_msg)

            if method in block_transfer_methods:
                # extract the mandatory data.
                method, direction, length, insert_name, units, x_value, y_value = [
                    value.strip() for value in row[:7]]
                target_flags = [value.strip() for value in row[7:]]
                

                if not length.isdigit():
                    err_msg = error_header + \
                              f"    The length:  '{length}'\n" \
                              f"    is not an integer." 
                    raise ValueError(err_msg)
                    
                if direction not in acceptable_directions:
                    err_msg = error_header + \
                              f"    The direction: '{direction}'\n" \
                              f"    is not h[orizontal] or v[ertical]" 
                    raise ValueError(err_msg)
                    
                
                
            else:
                # extract the mandatory data.
                method, insert_name, units, x_value, y_value = [
                    value.strip() for value in row[:6]]
                target_flags = [value.strip() for value in row[6:]]
            

            
            if method == "testjet":
                if not insert_name.isdigit() or int(insert_name) not in range(4):
                    err_msg = error_header + \
                        f"    The insert name: '{insert_name}'\n" \
                        f"    is not an integer describing a 3070 module.\n"\
                        f"    (0, 1, 2, 3)"
                    raise ValueError(err_msg)
                    
            

            if method in limited_transfer_methods:
                if method == "top_transfer":
                    bottom = False
                if method in ["bottom_transfer", "testjet"]:
                    top = False
                
                if method != "testjet":
                    method = "transfer"

            if target_flags:
                target_flags = target_flags[0]
                if not validate_remove_flags(target_flags, line_num, raw_line):
                    return None

                flag_check = target[0].lower()
                if flag_check not in target_flags:
                    skip_target = True
                    continue

            try:
                coord = ew.CoordTuple.from_str(x_value, y_value, units)
            except ValueError as err:
                err_msg = error_header + str(err)
                raise ValueError(err_msg)      


            
            mod_flags = InsertModFlag(method, coord, top, bottom, int(length), direction)
            
            # for a transfer statement, a checker function is not generated.
            if method in ["transfer", "testjet"] + block_transfer_methods:
                function_dict[(insert_name, mod_flags)] = (line_num, raw_line)
                continue

            # now generate function matcher.
            checker_list = []
            for func in insert_match_list:
                try:
                    result = func(insert_name)
                except ValueError as err:
                    err_msg = error_header + str(err)
                    raise ValueError(err_msg)
                else:
                    if result is None:
                        continue
                
                    if checker_list:
                        err_msg = \
                            f"    The {name} token matched more than one matching function!\n"\
                            f"    Check syntax rules and edit."
                        raise ValueError(error_header + err_msg)
                
                    checker_list.append(result)
            
            

            # a blank checker_list means a problem with the token.
            if not checker_list:
                err_msg = \
                    f"    The {method} token did not generate any matching functions\n"\
                    f"        Check syntax rules and edit."
                raise ValueError(error_header + err_msg)



            # there should only be one function now.
            function_dict[(checker_list[0], mod_flags)] = (line_num, raw_line)
            continue

    return function_dict, skip_target




def validate_modify_inserts_functions(fixture_dir, bottom_inserts, top_inserts, target):
    """
    This function examines "modify_inserts.csv, converts the
    descriptions into insert matching functions, and processes the flags.
    """

    # get a dictionary of the functions, which will check the
    # to and from inserts. also get functional flags.
    insert_editing_options = fixture_processing_options.INSERTS_MODIFIER_OPTIONS
    
    filename = insert_editing_options["filename"]
    description = insert_editing_options["modify_inserts"].description
    
    try:
        function_dict = get_custom_functions(
            fixture_dir, 
            target,
            filename, description,
            generate_insert_modification_functions)
    except ValueError as err:
        mb.showerror("ERROR", str(err))
        return None



    # all functions which match an insert are stored here.
    found_functions = set()

    # make sure that no inserts are matched more than once.
    # (we don't want to offset an insert more than once, that is likely an error).
    # Also make sure the functions match an insert.
    for inserts in [bottom_inserts, top_inserts]:

        matched_inserts = {}
        for (function, mod_flags), (line_num, line) in function_dict.items():

            # only check offset  move functions
            if mod_flags.method in ["new", "transfer", "testjet", "single_row", "double_row"]:
                continue

            for coord, insert in inserts.items():

                if function(insert):

                    found_functions.add(function)
                    if coord in matched_inserts:

                        err = MULTIPLE_MOD_ERROR.format(line_num, line)
                        mb.showerror("ERROR", err)
                        return None
                    else:
                        matched_inserts[coord] = function

    # make sure all functions have found a set.
    for (function, mod_flags), (line_num, line) in function_dict.items():
        if mod_flags.method in ["new", "transfer", "testjet", "single_row", "double_row"]:
            continue

        if function not in found_functions:
            err = NO_INSERT_MOD_ERROR.format(line_num, line)
            mb.showerror("ERROR", err)
            return None

    return function_dict


def generate_addition_wire_functions(csv_line_list, line_list, target, filename):
    """
    This function is intended to perform basic validation
    on a wire addition argument. It will not check whether or not
    the node/transfer/probe/brc_pin/power supply is present.
    """

    # a list containing the wire checking functions.
    # each function will see if the insert matches
    function_dict = {}

    from_list = [generate_brc_comparison, generate_probe_comparison,
                 generate_custom_transfer_comparison,
                 generate_explicit_power_supply_comparison]

    to_list = from_list.copy()

    error_header_func = error_message_header(filename)
    
    # this flag goes True if there are entries,
    # but due to target selection, they have been skipped.
    skip_target = False

    for line_num, (row, raw_line) in enumerate(zip(csv_line_list, line_list), 1):
        error_header = error_header_func(line_num, raw_line)
        
        line = raw_line.strip()

        # skip blank lines, and comments
        if not line or line.startswith("!"):
            continue

        flags = WireAddFlags()
        value_count = len(row)

        if value_count not in range(3, 5 + len(flags)):
            err_msg = error_header + f"Wrong number of values ({value_count})."
            mb.showerror("ERROR", err_msg)
            return None

        # extract the from and to token, stripping them of l and r
        # whitespace.
        from_token, to_token = [value.strip() for value in row[:2]]
        csv_flags = row[2:]
        
        try:
            processed_flags_return = process_flags(
                csv_flags, flags, filename, line_num, raw_line, target)
        except ValueError as err:
            raise ValueError(error_header + str(err))
            

        flags, continue_flag = processed_flags_return

        if continue_flag:
            skip_target = True
            continue

        loop_vars = (["from", "to"],
                     [from_token, to_token],
                     [from_list, to_list])

        token_functions = []

        for name, token, func_list in zip(*loop_vars):

            checker_list = []
            for func in func_list:
                try:
                    result = func(token)
                except ValueError as err:
                    err_msg = error_header + str(err)
                    raise ValueError(err_msg)
                else:
                    if result is None:
                        continue
                
                    if checker_list:
                        err_msg = \
                            f"    The {name} token matched more than one matching function!\n"\
                            f"    Check syntax rules and edit."
                        raise ValueError(error_header + err_msg)
                
                    checker_list.append(result)
                        

            # a blank checker_list means a problem with the token.
            if not checker_list:
                err_msg = \
                    f"    The {name} token did not generate any matching functions\n"\
                    f"        Check syntax rules and edit."
                mb.showerror("ERROR", error_header + err_msg)
                return None


            # There should be only one function now,
            # stored in a list for future processing.
            token_functions.append(checker_list[0])

        from_function, to_function = token_functions
        key = from_function, to_function, flags

        # add the wire checking function to a list.
        function_dict[key] = (line_num, line)

    return function_dict,  skip_target



def validate_add_token(function, bottom_inserts, top_inserts):
    """
    This function sees which set of inserts the function matches.
    if top_inserts, returns "TOP"
    if in bottom_inserts returns "BOTTOM"
    if in both returns "BOTH"
    if in neither returns ""
    """

    filtered_bottom = {coord: insert for coord, insert in
                       bottom_inserts.items()
                       if function(insert)}

    filtered_top = {coord: insert for coord, insert in
                    top_inserts.items()
                    if function(insert)}

    if filtered_top and filtered_bottom:
        return "BOTH"

    if filtered_top:
        return "TOP"

    if filtered_bottom:
        return "BOTTOM"

    return ""


def validate_add_wires_functions(fixture_dir, bottom_inserts, top_inserts, target):
    """
    This function looks at the user defined add wire token functions,
    and checks them against the inserts, raising an error if one is found.
    """

    # get a dictionary of the functions which check the
    # to and from inserts. If the to function and the from
    # function match one insert each (on the same side of the fixture)
    # and the matching to and from insert are not the same,
    # a wire will be added.
    
    wire_addition_options = fixture_processing_options.NEW_WIRE_OPTIONS
    filename = wire_addition_options["filename"]
    description = wire_addition_options["add_custom_wires"].description
    
    try:
        function_dict = get_custom_functions(fixture_dir, 
                                             target, 
                                             filename, description,
                                             generate_addition_wire_functions)
    except ValueError as err:
        mb.showerror("ERROR", str(err))
        return None


    bottom_functions, top_functions = {}, {}

    # find out whether the functions apply to the top or the
    # bottom of the fixture.
    for (from_function, to_function, addition_flags), (line_num, line) in function_dict.items():

        validation_results = set()
        for function, token_name in zip([from_function, to_function], ["from", "to"]):

            side = validate_add_token(function, bottom_inserts, top_inserts)

            # if side is "", then the function doesn't match the top
            # or bottom.
            if side == "":
                err = NO_INSERT_ERROR.format(token_name, line_num, line)
                mb.showerror("ERROR", err)
                return None

            validation_results.add(side)

        # ensure that the from and to don't match on the top AND the bottom.
        if validation_results == {"BOTH"}:
            err = TOP_AND_BOTTOM_ERROR.format(token_name, line_num, line)
            mb.showerror("ERROR", err)
            return None

        # remove 'BOTH' from the side set.
        validation_results.discard("BOTH")

        # a side set of length 2 means it contains a TOP and a BOTTOM element.
        if len(validation_results) == 2:
            err = BOTH_INSERTS_ERROR.format(line_num, line)
            mb.showerror("ERROR", err)
            return None

        if validation_results == {"TOP"}:
            top_functions[(from_function, to_function, addition_flags)] = (
                line_num, line)
        elif validation_results == {"BOTTOM"}:
            bottom_functions[(from_function, to_function, addition_flags)] = (
                line_num, line)

    return bottom_functions, top_functions

"""
This script will contain all of the transform functions which modify the
wires and inserts data.

all of the transforms will be collected into a data structure containing:

 - The calling flag name (ie if the flag is True, then this function is called.)

 - A collection of output targets the function is intended to transform.

 - a function which accepts and returns wires and inserts data.
   def <<func_name>>(wires_tuple, inserts_tuple):
       <<arbitrary code>>

       return wires_tuple, inserts_tuple

 note that wires and inserts data consists of a tuple of inserts & inserts_top /
 wires & wires_top.
"""


from collections import namedtuple, OrderedDict, defaultdict
from itertools import product
from tkinter import messagebox as mb
import logging


from ..options_lib import fixture_processing_options

from . import fixture_maths as fm
from . import fixture_modifications as fmod
from . import extract_wires as ew


fp_logger = logging.getLogger('fixture_processing.fixture_processing')


def remove_user_defined_wires(fixture_dir, fixture_data, flags, target):
    """
    This function looks in a file describing wires to
    be removed and stores them in a list


    Then the function goes through the bottom and top wires removing
    those which match the provided list. 
    """

    bottom_wires, top_wires = fixture_data._wires
    bottom_inserts, top_inserts = fixture_data._inserts

    new_bottom_wires, new_top_wires = [], []

    # get a dictionary of functions which check each wire.
    # if any of these functions return True, then the
    # wire should be removed.
    # The line which generated the function is the value
    wire_removal_options = fixture_processing_options.WIRE_REMOVAL_OPTIONS
    
    file_name = wire_removal_options["filename"]
    description = wire_removal_options["remove_custom_wires"].description
    
    function_dict = fmod.get_custom_functions(fixture_dir, target,
        file_name, description, fmod.generate_remove_wire_functions)

    # we must keep track of the functions which are used.
    # a function which applies to no wires often means
    # the writer of remove_wires.csv has made a mistake.
    used_functions = set()

    if function_dict is None:
        return None

    loop_vars = ([bottom_wires, top_wires],
                 [new_bottom_wires, new_top_wires],
                 [bottom_inserts, top_inserts])

    for wires, new_wires, inserts in zip(*loop_vars):

        for wire_data in wires:

            # as long as this flag is false, the wire is not removed.
            remove_flag = False

            # terminals have no corresponding insert,
            # so the insert is set to None.
            if wire_data._from_is_terminal:
                from_insert = None
            else:
                from_insert = inserts[wire_data.from_xy]

            if wire_data._to_is_terminal:
                to_insert = None
            else:
                to_insert = inserts[wire_data.to_xy]

            for wire_match_function, mod_flags in function_dict.keys():

                if wire_match_function(from_insert, to_insert):
                    used_functions.add(wire_match_function)
                    # if the wire is being removed:
                    if mod_flags.remove:
                        remove_flag = True
                    else:
                        remove_flag = False
                        wire_info = wire_data.wire_info

                        if mod_flags.gauge is not None:
                            wire_info = wire_info._replace(
                                gauge=mod_flags.gauge)
                        if mod_flags.colour is not None:
                            wire_info = wire_info._replace(
                                colour=mod_flags.colour)

                        wire_data = wire_data._replace(
                            wire_info=wire_info, custom_wire=True)
                        break

            if not remove_flag:
                new_wires.append(wire_data)

    # don't bother checking if told to ignore.
    if not flags.ignore_missing_wires:
        # ensure each removal function was used
        for (wire_match_function, _), (line_num, line) in function_dict.items():
            if wire_match_function not in used_functions:
                err = fmod.NO_WIRE_ERROR.format(line_num, line.strip())
                mb.showerror("ERROR", err)
                return None

    return fixture_data._replace(bottom_wires=new_bottom_wires, top_wires=new_top_wires)


def remove_terminal_wires(fixture_dir, fixture_data, flags, target):
    """
    This function looks through the wires and the top wires
    list and removes all wires to a terminal.

    wires to a terminal cause problems with the wiring machine
    and verifier as the terminals tend to be fixture electronics
    and so do not have am X, Y location.

    the wires is a data structure consisting of a list of tuples.
    each tuple contains the following information:

    (length, gauge, colour), from_brc, to_brc, from_xy, to_xy

    """

    remove_count = 0

    new_bottom_wires = []

    for wire in fixture_data.bottom_wires:
        if not wire._is_terminal_wire:
            new_bottom_wires.append(wire)
        else:
            remove_count += 1

    fp_logger.info(
        "%d terminal related wires have been removed from the fixture.", remove_count)

    return fixture_data._replace(bottom_wires=new_bottom_wires)


def remove_testjet_wires(fixture_dir, fixture_data, flags, target):
    """
    When producing fixtures, testjet/ vtep transfer tend to be
    assigned by the fixture designer. But the sofware also assigns
    default transfer.
    This function searches for and removes this transfer.
    """

    remove_count = 0

    # get the bottom wires and inserts
    wires, inserts = fixture_data._bottom

    new_wires = []

    for wire_data in wires:

        # a to or from terminal is unlikely to be a testjet wire.
        if wire_data._is_terminal_wire:
            new_wires.append(wire_data)
            continue

        # get the fixture id (as defined in the pins section.
        from_insert = inserts[wire_data.from_xy]
        from_brc = from_insert.fix_id.brc

        # if not asru or control, skip.
        if not from_brc.is_testjet:
            new_wires.append(wire_data)
            continue

        to_insert = inserts[wire_data.to_xy]
        if to_insert.insert_type in ["Pin", "Offset"]:
            new_wires.append(wire_data)
            continue

        remove_count = remove_count + 1
        fp_logger.debug(
            "  from_brc=%s, to_brc=%s has been removed from the wires file. Unnecessary testjet wire.",
            wire_data.from_brc,
            wire_data.to_brc)

    fp_logger.info(
        "%d testjet related wires have been removed from the fixture.", remove_count)
    return fixture_data._replace(bottom_wires=new_wires)


def remove_ground_wires(fixture_dir, fixture_data, flags, target):
    """
    With a ground plane fixture, all of the hybrid grounds are soldered
    together. This means that there is no need to add a wire between
    2 soldered BRCs. This function is intended to remove all
    ground to bround BRCs.
    """

    remove_count = 0
    # get the bottom wires and inserts
    wires, inserts = fixture_data._bottom

    new_wires = []

    # are asru switched grounds considerered grounds?
    include_asru = flags.gplane_include_asru

    # first, filter the wires list, so that
    # only ground wires are present.
    for wire_data in wires:

        # a wire to or from a terminal is not going to be a ground wire.
        if wire_data._is_terminal_wire:
            new_wires.append(wire_data)
            continue

        from_insert = inserts[wire_data.from_xy]
        from_brc = from_insert.fix_id.brc

        if not from_brc.is_fixture_ground(include_asru=include_asru):
            new_wires.append(wire_data)
            continue

        to_insert = inserts[wire_data.to_xy]
        to_fix_id = to_insert.fix_id

        if to_insert._is_fixture_ground(include_asru=include_asru):

            remove_count = remove_count + 1
            fp_logger.debug(
                "  from_brc=%s, to_brc=%s has been removed from the wires file. Unnecessary ground wire.",
                wire_data.from_brc,
                wire_data.to_brc)
            continue

        new_wires.append(wire_data)

    fp_logger.info(
        "%d ground related wires have been removed from the fixture.", remove_count)
    return fixture_data._replace(bottom_wires=new_wires)

def calculate_TJ_Mux_pins(flags, pin1_coord):
    """
    For each of the 10 pins of the mux card,
    calculates the location of pins 2 - 10.
    (pin 1 was provided by the user)
    note the offsets are also provided
    by the user.
    """
    
    try:
        pin2_offset = fm.CoordTuple.from_mils_str(flags.pin2_offset)
    except ValueError as err:
        msg = f"    error found in pin2 offset: \n" \
              f"    {err}\n" \
              f"    format should be (X, Y), where\n" \
              f"    X and Y are integer numbers"
        mb.showerror("ERROR", msg)
        return None
              
    try:
        pin6_offset = fm.CoordTuple.from_mils_str(flags.pin6_offset)
    except ValueError as err:
        msg = f"    error found in pin2 offset: \n" \
              f"    {err}\n" \
              f"    format should be (X, Y), where\n" \
              f"    X and Y are integer numbers"
        mb.showerror("ERROR", msg)
        return None
    
    new_coords = []
    
    modified_coord = pin1_coord
    
    # for pins 1 to 5
    for i in range(1, 6):
        new_coords.append((modified_coord, i))
        modified_coord = modified_coord + pin2_offset
    
    # calculate pin 6 coord
    modified_coord = pin1_coord + pin6_offset
    
    # for pins 1 to 5
    for i in range(6, 11):
        new_coords.append((modified_coord, i))
        modified_coord = modified_coord + pin2_offset

    return new_coords


def new_transfer(inserts, brc, new_coord, fix_id):
    """
    taking the location and a name, adds an insert
    to the inserts dict.
    """
    
    insert_type = "Transfer"
    spring = ""
    node = "OTHER"
    device = ""
    
    insert = ew.InsertTuple(
        brc, insert_type, spring, node, device, fix_id, new_coord)
    inserts[new_coord] = insert

def custom_transfer_name(mod_flags, insert_name, pin):
    """
    a custom insert is simply called
        f"custom{insert_name}"
    
    but a testjet transfers name
    depends on its module and pin.
    """
    
    if mod_flags.method == "testjet":
        return f"TJ{insert_name}_{pin}"
    else:
        return f"custom{insert_name}"

def modify_user_defined_inserts(fixture_dir, fixture_data, flags, target):
    """
    for verious reasons when designing a fixture, it becomes necessary
    to modify the location of an insert. for example:

     - moving an transfer as it is too close to a fixture feature,
     - moving a brc, because it is too close to a fixture feature,
     - moving a probe, because it is possible to upgrade the probe to a larger size.
    """

    bottom_inserts, top_inserts = fixture_data._inserts
    bottom_inserts, top_inserts = bottom_inserts.copy(), top_inserts.copy()
    fixture_size = fixture_data.fixture_size

    # get the insert offset matching functions and details.
    function_dict = fmod.validate_modify_inserts_functions(
        fixture_dir, bottom_inserts, top_inserts, target)
    if function_dict is None:
        return None

    # we must keep a track of the functions which are used.
    # a function which applies to no inserts often
    # means the writer of "modify_inserts.csv" has made a mistake.
    used_functions = set()

    loop_var = ([bottom_inserts, top_inserts], ["bottom", "top"])

    # apply insert offsets.
    for inserts, label in zip(*loop_var):

        for coord, insert in inserts.copy().items():

            for insert_match_function, mod_flags in function_dict.keys():

                if mod_flags.method in ["new", "transfer", "testjet"]:
                    continue

                # ensure function matches insert.
                if not insert_match_function(insert):
                    continue

                flips = 0
                if insert._is_pin:
                    flips += 1

                if label == "top":
                    flips += 1

                if insert._is_pin or (insert._is_transfer and label == "top"):
                    round_brackets = True
                else:
                    round_brackets = False

                custom_coord = mod_flags.coord.flip_coord(flips)

                if mod_flags.method == "offset":
                    offset_coord = custom_coord

                    # add the offset to the coordinate.
                    new_coord = insert.coord + offset_coord
                    brc = new_coord.flip_coord(flips).to_brc_str(
                        fixture_size, round_brackets)

                    if new_coord in inserts:
                        err = fmod.MOD_EXISTING_COORD.format(**locals())
                        mb.showerror("ERROR", err)
                        return None

                    inserts[coord] = insert._replace(coord=new_coord)
                elif mod_flags.method == "move":
                    new_coord = custom_coord
                    if new_coord in inserts:
                        err = fmod.MOD_EXISTING_COORD.format(**locals())
                        mb.showerror("ERROR", err)
                        return None

                    brc = new_coord.flip_coord(flips).to_brc_str(
                        fixture_size, round_brackets)
                    inserts[coord] = insert._replace(coord=new_coord, brc=brc)

    # add new inserts to fixture_data
    for (insert_name, mod_flags), (line_num, raw_line) in function_dict.items():

        if mod_flags.method not in ["transfer", "testjet"]:
            continue
            

        for inserts, label in zip(*loop_var):

            # if the transfer is only for the top,
            # skip bottom. & visa versa.
            if label == "top" and not mod_flags.top:
                continue

            if label == "bottom" and not mod_flags.bottom:
                continue

            flips = 0
            if label == "top":
                flips += 1
                round_brackets = True
            else:
                round_brackets = False

            new_coord = mod_flags.coord.flip_coord(flips)
            
            if mod_flags.method == "testjet":
                coords_list = calculate_TJ_Mux_pins(flags, new_coord)
                if coords_list is None:
                    return None
            else:
                coords_list = [(new_coord, 1)]
            
            # add an transfer for each coord.
            # normal transfer only adds one.
            for new_coord, pin in coords_list:
                if new_coord in inserts:
                    err = fmod.MOD_EXISTING_COORD.format(**locals())
                    mb.showerror("ERROR", err)
                    print(new_coord)
                    return None
                
                brc = mod_flags.coord.to_brc_str(
                    fixture_size, round_brackets=round_brackets)
                
                
                fix_id = custom_transfer_name(mod_flags, insert_name, pin)
                
                new_transfer(inserts, brc, new_coord, fix_id)

    return fixture_data._replace(bottom_inserts=bottom_inserts, top_inserts=top_inserts)


def correct_offset_pins(fixture_dir, fixture_data, flags, target):
    """
    This function alters the wires and inserts data
    to remove all offset data. This will only be applied
    to the verifier target to prevent spurious node problems.
    """

    # get the bottom wires and inserts
    wires, inserts = fixture_data._bottom

    # as only pins will be changed, the top will be ignored.
    new_inserts = OrderedDict()
    new_wires = []

    for coord, data in inserts.items():

        # skip entries which are not pins or offsets
        if not data._is_pin:
            new_inserts[coord] = data

        # no offset means no change necessary
        elif data.fix_id.offset == (0, 0):
            new_inserts[coord] = data
        else:
            brc = data.brc
            fix_id = data.fix_id
            x, y = data.coord
            x_offset, y_offset = fix_id.offset

            new_brc = fm.create_brc_loc(fix_id.brc)

            new_x = x - x_offset
            new_y = y + y_offset

            new_data = data._replace(
                brc=new_brc, insert_type="Pin", coord=(
                    new_x, new_y))

            log_str = "brc %s with offset   (%-6s %6d) will be corrected to %s (%-8s %8d)"
            fp_logger.debug(
                log_str,
                brc,
                str(x_offset) + ",",
                y_offset,
                new_brc,
                str(new_x) + ",",
                new_y)
            new_inserts[coord] = new_data

    return fixture_data._replace(bottom_inserts=new_inserts)


def add_user_defined_wires(fixture_dir, fixture_data, flags, target):
    """
    This function looks in a file describing wires to be added, 
    and stores them in a list.

    Then the function goes through the top and bottom inserts, ensuring
    it is possible to add the wire, and adds it.
    """

    bottom_wires, top_wires = fixture_data._wires
    bottom_inserts, top_inserts = fixture_data._inserts

    # we must keep track of the functions which are used.
    # a function which applies to fewer than 2 inserts often
    # means that the writer of 'add_wires.csv' has made a mistake.
    used_functions_top = set()
    used_functions_bottom = set()
    print("Must add unused add wires check.")

    functions_tuple = fmod.validate_add_wires_functions(
        fixture_dir, bottom_inserts, top_inserts, target)
    if functions_tuple is None:
        return None

    bottom_functions, top_functions = functions_tuple

    loop_var = [bottom_wires, top_wires], [bottom_inserts,
                                           top_inserts], [bottom_functions, top_functions]

    for wires, inserts, functions in zip(*loop_var):

        # store the matches to this dict
        matched_inserts_lookup = defaultdict(list)

        for (from_func, to_func, _), (coord, insert) in product(functions.keys(), inserts.items()):
            for func in [from_func, to_func]:
                # store the matching inserts in a dictionary for later reference
                if func(insert):
                        matched_inserts_lookup[func].append(coord)

        for (from_func, to_func, addition_flags), (line_num, raw_line) in functions.items():
            raw_line = raw_line.rstrip()

            # make sure the func only matched one insert.
            for func, name in zip([from_func, to_func], ["from", "to"]):
                matched_inserts = len(matched_inserts_lookup)
                if matched_inserts < 1:
                    err = EXTRA_INSERTS_ERROR.format(
                        name, line_num, raw_line, matched_inserts)

            from_coord = matched_inserts_lookup[from_func][0]
            from_insert = inserts[from_coord]

            to_coord = matched_inserts_lookup[to_func][0]
            to_insert = inserts[to_coord]

            wire_length = fm.get_wire_length(from_insert, to_insert)

            wire_info = addition_flags._to_WireInfo(wire_length)

            wires.append(ew.WireTuple(wire_info, from_insert.brc,
                                      to_insert.brc, from_coord, to_coord, True))

    #
    #
    # loop_var = []

    return fixture_data


# def match_wires(fixture_data, target_folder):
#     """
#     Throughout the fixture processing, offsets will be applied to
#     the inserts. The new coordinates will eventually be applied to the
#     coord attribute of the insert.
#
#     However - the wires are not updated to allow the insert lookup
#     to work as expected.
#
#     so this function is called last to create a set of wires which do match.
#     """
#
#     bottom_inserts, top_inserts = fixture_data._inserts
#
#     bottom_wires, top_wires = fixture_data._wires
#
#     new_bottom_wires = []
#     new_top_wires = []
#
#     loop_var = zip([bottom_wires, top_wires],
#                    [bottom_inserts, top_inserts],
#                    ["bottom", "top"])
#
#     for wires, inserts, side in loop_var:
#
#         for wire_data in wires:
#
#             # the dict used to replace wire entries.
#             replace_dict = {}
#
#             meta_data, from_brc, to_brc, from_xy, to_xy, custom_wire = wire_data
#
#             iter_tuple = (("from", from_brc, from_xy),
#                           ("to", to_brc, to_xy))
#
#             for direction, brc, xy_coord in iter_tuple:
#
#                 # skip terminals.
#                 if xy_coord == (0, 0):
#                     continue
#
#                 insert_data = inserts[xy_coord]
#
#
#                 # if the xy_coord matches the insert coord,
#                 # no change is needed
#                 if xy_coord == insert_data.coord:
#                     continue
#
#
#
#                 replace_dict[direction + "_brc"] = insert_data.brc
#                 replace_dict[direction + "_xy"] = insert_data.coord
#
#             if replace_dict:
#                 wire_data = wire_data._replace(**replace_dict)
#
#
#             if side == "top":
#                 new_top_wires.append(wire_data)
#             else:
#                 new_bottom_wires.append(wire_data)
#
#     return fixture_data._replace(bottom_wires=new_bottom_wires, top_wires=new_top_wires)

def get_transforms():
    """
    This function collates the functions, and adds them
    to the data structure along with the flags and targets
    """

    transforms = OrderedDict()

    # The user can choose to remove wires from the wires file.
    # "remove_wires.csv" contains the list of wires to be removed.
    # All targets are included because the user can choose which
    # target this applies to.
    name = "remove_user_defined_wires"
    targets = ("wiring_machine", "verifier", "verifier_top")

    # This transform is only to be used when the user selects
    # the "remove user defined wires" option on the GUI.
    # def ruw_rule(flags): return flags.remove_user_defined_wires
    def ruw_rule(flags): return flags.remove_custom_wires

    transforms[(name, ruw_rule, targets)] = remove_user_defined_wires

    # terminal wires can cause problems with the verifier
    # and the wiring machine. This transform removes all
    # of the terminals fromt the wires file.
    # also removes terminals from the experimental verifier
    # top target.
    name = "remove_terminal_wires"
    targets = ("wiring_machine", "verifier", "verifier_top")

    # This tranform is only to be ran when the user selects
    # the "remove terminal wires" option on the GUI.
    def rtw_rule(flags): return flags.remove_terminal_wires

    transforms[(name, rtw_rule, targets)] = remove_terminal_wires

    # wires from testjet BRCs to default transfers
    # are unnecessary. The following function removes them.
    name = "remove_testjet_wires"
    targets = ("wiring_machine", "verifier", "verifier_top")

    # this transform is only to be run when the user selects
    # the "remove testjet transfer wires" option in the GUI.
    def rtj_rule(flags): return flags.remove_tj_transfers
    transforms[(name, rtj_rule, targets)] = remove_testjet_wires

    # wires from soldered brc to soldered brc are not required on
    # ground plane fixtures. This removes them on the wiring machine.
    name = "remove_ground_wires"
    targets = ("wiring_machine")

    # this is only to be run when the ground plane pin is
    # selected.
    def rgw_rule(flags): return flags.fixture_gplane
    transforms[(name, rgw_rule, targets)] = remove_ground_wires

    # By making it possible to modify inserts, by moving them, offsetting them,
    # or by adding entirely new ones, the wiring operator will be able to
    # add the wires affected by the inserts moved by the CAD engineer.
    # prevously a missing one would have been awkward.
    name = "modify_inserts"
    targets = ("wiring_machine", "verifier", "verifier_top")

    # This transform is only to be ran when the user selects.
    # "Modify user defined inserts" on the gui.
    def mudi_rule(flags): return flags.modify_inserts
    transforms[(name, mudi_rule, targets)] = modify_user_defined_inserts

    # offset pins can cause problems with the verifier software.
    # by removing the offset from the wires and inserts, the
    # electrical connections will still be correct, but the verifier
    # will not get confused.
    name = "correct_offset_pins"
    targets = ("verifier", "verifier_top")

    # This transform is only to be ran when the user selects
    # the "correct offset pin" option on the gui.
    def cop_rule(flags): return flags.pin_offset_fix

    transforms[(name, cop_rule, targets)] = correct_offset_pins

    # In this transform, the user can add wires to the fixture.
    # they do this by describing the wires they want to add
    # in the add_wires.csv file. The function then validates the
    # input and then adds the wires.
    name = "add_user_defined_wires"
    targets = ("wiring_machine", "verifier", "verifier_top")

    # This transform is only to be ran when the user selects.
    # 'Add user defined wires'
    def audw_rule(flags): return flags.add_custom_wires
    transforms[(name, audw_rule, targets)] = add_user_defined_wires

    return transforms

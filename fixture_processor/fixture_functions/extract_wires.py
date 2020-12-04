"""
This folder contains the code used for processing the wires files.

for future compatability, 2 alternate wires and inserts files will
be created, one for the wiring machine, and one for the verifier.

The Aim behind generating a seperate set of files for the verifier is:

 - reduce false fails due to:
     * offset BRCs confusing the verifier.
       (We think the verifier looks for 2 01.00 01.00,
       and if it can't find it (as it has been offset)
       that it produces a spurious results failure.
       (Due to calculation complexity, this will be ignored for now)

     * ground plane soldered BRCs.
       due to some parts of the soldered BRCs being isolated.

       extra rows of BRCs added as spare can cause
       soldered BRCS / shorts that the verifier did not expect.

     * it is possible that ground plane wires will be removed
       in the wires for the wiring machine (to reduce the number
       of wires in the fixture, but those wires will still be needed
       for the verifier.

     * possibly add checks on wires which were manually added
       but can not be added via the wiring machine.

     * Allows the creation of a seperate verifier file which
       will probe the backs of the top probes, checking it is
       connected to the BRCs below.

"""

from . import fixture_maths as fm
from . import fixture_input as fi
from . import output_data as od
from . import fixture_processing as fp


from .fixture_output import output_wires_inserts
from .fixture_maths import CoordTuple

from ..options_lib import fixture_processing_options


from pathlib import Path
from collections import namedtuple, OrderedDict

from tkinter import messagebox as mb
from decimal import Decimal
import re
import logging
import typing

fp_logger = logging.getLogger('fixture_processing')


class WireInfo(typing.NamedTuple):
    length: str
    gauge: str
    colour: str


class WireTuple(typing.NamedTuple):
    wire_info: WireInfo
    from_brc: str
    to_brc: str
    from_xy: typing.Tuple[int, int]
    to_xy: typing.Tuple[int, int]
    custom_wire: bool = False

    @property
    def _from_is_terminal(self):
        """
        Returns True if the from 'insert' is a terminal.
        """

        return self.from_xy == (0, 0) and " " not in self.from_brc

    @property
    def _to_is_terminal(self):
        """
        Returns True if the to 'insert' is a terminal.
        """
        return self.to_xy == (0, 0) and " " not in self.to_brc

    @property
    def _is_terminal_wire(self):
        """
        returns True if the wire is going to
        or from a fixture terminal.
        returns False otherwise.
        """

        return self._from_is_terminal or self._to_is_terminal

    @property
    def _get_xy_coords(self):
        """
        Often, only the from_xy and to_xy is required
        from the WireTuple. This returns only that.
        """

        return self.from_xy, self.to_xy
        
    @property
    def _get_brc_data(self):
        """
        Often, only the from_xy and to_xy is required
        from the WireTuple. This returns only that.
        """

        return self.from_brc, self.to_brc
        
    
    def iter_wire(self):
        """
        acts as a generator to return the
        'from' data, then the 'to' data
        """

        yield (self.from_xy, self.from_brc, "from")
        yield (self.to_xy, self.to_brc, "to")       


class InsertTuple(typing.NamedTuple):
    brc: str
    insert_type: str
    spring: str
    node: str
    device: str

    # the name of the insert in the fixture file
    fix_id: typing.Union[str, fi.PinsTuple]

    # used when updating the fixture coordinate
    coord: typing.Tuple[int, int]

    @property
    def _is_pin(self):
        """
        returns True if this insert
        is a pin (or an offsetted pin)
        """
        return self.insert_type in ["Pin", "Offset"]

    @property
    def _is_transfer(self):
        """
        returns True if this insert
        is a pin (or an offsetted pin)
        """
        return self.insert_type == "Transfer"

    def _is_fixture_ground(self, include_asru):

        if self._is_pin:
            return self.fix_id.brc.is_fixture_ground(include_asru=include_asru)
        return False

    @property
    def _wire_coord(self):
        """
        In the inserts file, a Pin has a negative number,
        because it is inserted on the opposite side of the
        G10.
        """

        if self._is_pin:
            coord_x, coord_y = self.coord
            return (coord_x, -coord_y)
        else:
            return self.coord


class FixtureTuple(typing.NamedTuple):
    bottom_wires: list
    top_wires: list
    bottom_inserts: dict
    top_inserts: dict
    fixture_size: str = ""
    ground_nodes: list = []

    @property
    def _wires(self):
        return (self.bottom_wires, self.top_wires)

    @property
    def _inserts(self):
        return (self.bottom_inserts, self.top_inserts)

    @property
    def _bottom(self):
        return (self.bottom_wires, self.bottom_inserts)

    @property
    def _top(self):
        return (self.top_wires, self.top_inserts)


FIXTURE_TARGETS = fixture_processing_options.FIXTURE_TARGETS


def get_settings(file_path):
    """
    The top of each inserts and wires file
    contains settings which are used when
    designing the fixture.
    This function converts them to a dict.
    """
    fixture_type = ""
    fixture_size = ""
    fixture_part_num = ""
    top_probes = ""
    autofile = ""
    units = ""
    wiring_method = ""

    fixture_type_label = "Fixture Type : "
    fixture_size_label = "Fixture Size : "
    fixture_part_num_label = "Fixture Part Number : "
    top_probes_label = "Top Probes Allowed : "
    autofile_label = "Autofile : "
    units_label = "Units : "
    wiring_method_label = "Wiring Method : "

    settings = {}

    with file_path.open() as f_handle:
        for raw_line in f_handle:
            line = raw_line.lstrip()

            if line.startswith(fixture_type_label):
                fixture_type = line.replace(fixture_type_label, "")
                settings["fixture_type"] = fixture_type.rstrip()
                continue

            if line.startswith(fixture_size_label):
                fixture_size = line.replace(fixture_size_label, "")
                settings["fixture_size"] = fixture_size.rstrip()
                continue

            if line.startswith(fixture_part_num_label):
                fixture_part_num = line.replace(fixture_part_num_label, "")
                settings["fixture_part_num"] = fixture_part_num.rstrip()
                continue

            if line.startswith(top_probes_label):
                top_probes = line.replace(top_probes_label, "")
                settings["top_probes"] = top_probes.rstrip()
                continue

            if line.startswith(autofile_label):
                autofile = line.replace(autofile_label, "")
                settings["autofile"] = autofile.rstrip()
                continue

            if line.startswith(units_label):
                units = line.replace(units_label, "")
                settings["units"] = units.rstrip()
                continue

            if line.startswith(wiring_method_label):
                wiring_method = line.replace(wiring_method_label, "")
                settings["wiring_method"] = wiring_method.rstrip()
                continue

            if all((fixture_type, fixture_size, fixture_part_num,
                    top_probes, autofile, units, wiring_method)):
                break

    fp_logger.info("%s settings: ", file_path.name)
    for setting_name, value in settings.items():
        fp_logger.info("    %-20s: %s", setting_name, value)

    return settings


def diff_lookup(pins_lookup, brc_lookup, performance_flag=True):
    """
    This function is used when there is not an exact pin match
    due to rounding errors.

    it works by performing a decimal diff between the
    rows and columns.

    items with no offset are skipped, as they are unlikely
    to have rounding errors.

    due to statistical reasons, performance mode skips the
    slow decimal diff comparisons when either:
    the column is not an exact match or
    the row is not an exact match.
    """

    # performing distance check.
    # slow, compared to simple lookup.
    # intended to be rarely used.
    for key, value in pins_lookup.items():
        if value.offset == (0, 0):
            continue

        fix_bank = key[1]
        ins_bank = brc_lookup[1]
        if fix_bank != ins_bank:
            continue

        fix_row = key[-5:-1]
        ins_row = brc_lookup[-5:-1]

        fix_col = key[3:8]
        ins_col = brc_lookup[3:8]

        row_match = fix_row == ins_row
        col_match = fix_col == ins_col

        if performance_flag and not (row_match or col_match):
            continue

        row_diff = abs(Decimal(fix_row) - Decimal(ins_row))
        col_diff = abs(Decimal(fix_col) - Decimal(ins_col))

        if row_diff <= 0.01 and col_diff < 0.1:
            fp_logger.info(
                "Using %s due to a row diff of %s and a col diff of %s", key, row_diff, col_diff)
            return value

    # if unable to find result, return empty string.
    return ""


def lookup_pin_id(pins_lookup, brc, node):
    """
    This function works out the pin ID of the brc extracted from the inserts file.

    This will be useful for applying filters and offsets in the future.
    """

    # replace the *XXXX* with (XXXX)
    if "*" in brc:
        brc_lookup = brc.replace("*", "(", 1)
        brc_lookup = brc_lookup.replace("*", ")", 1)
    else:
        brc_lookup = brc

    if brc_lookup in pins_lookup:
        x, y = pins_lookup[brc_lookup].offset

        return pins_lookup[brc_lookup]

    if brc == brc_lookup:
        fp_logger.info("not found: %s, node name: %s", brc, node)

    else:
        fp_logger.info(
            "not found: %s (Using: %s), node name: %s ",
            brc,
            brc_lookup,
            node)

    pin_res = diff_lookup(pins_lookup, brc_lookup)

    if pin_res != "":
        return pin_res

    return diff_lookup(pins_lookup, brc_lookup, False)


def inv_coord(coord):
    """
    given a X, Y coordinate,
    returns X, -Y
    """
    coord_x, coord_y = coord
    return (coord_x, -coord_y)


def parse_inserts_line(raw_line, pins_lookup, probe_dict, top_flag):
    """
    This function is a subset of the get_inserts function.
    it is intended to extract the data from a single inserts line.
    """

    # initialise the default data

    inserts_re = r"""
                     (?P<brc>(\(|\[|\*).*?(\)|\]|\*))         # the BRC part () or []
                     [ ]+                               # seperation spacing
                     (?P<x>-?\d+)                       # the X coord
                     [ ]+                               # seperation spacing
                     (?P<y>-?\d+)                       # the Y coord
                     [ ]+                               # seperation spacing
                     (?P<insert_type>Pin[ ]{0,3}|Tooling[ ]?|Transfer|\d{1,3}[ ]mil[ ]|(?P<probe_size>\d{1,3}Mil)Probe|Offset[ ]?)
                  """

    inserts_re = re.compile(inserts_re, re.VERBOSE)

    brc = ""
    coord_x = ""
    coord_y = ""
    insert_type = ""
    spring = ""
    node = ""
    device = ""

    line = raw_line.strip()

    re_lookup = inserts_re.match(line)
    if re_lookup is not None:

        brc = re_lookup.group("brc").strip()
        coord_x = int(re_lookup.group("x"))
        coord_y = int(re_lookup.group("y"))
        coord = CoordTuple(coord_x, coord_y)
        insert_type = re_lookup.group("insert_type").strip()
        
        if insert_type.endswith("Probe"):
           insert_type = re_lookup.group("probe_size").strip().lower().replace("mil", " mil")
        
        rest_of_line = line.replace(re_lookup[0], "", 1).strip()

        if insert_type == "Tooling":
            node = None

        elif rest_of_line in ["Extra"]:
            node = "<Extra>"

        elif rest_of_line in ["AUTOFILE"]:
            node = "<AUTOFILE>"

        elif rest_of_line in ["OTHER"]:
            node = "<OTHER>"

        # normal pins (brcs) and transfers
        elif insert_type in ["Transfer", "Pin", "Offset"]:
            node = rest_of_line

        # only probes left
        else:
            rest_of_line = re.sub(r"(\d{1,2} oz)([^ ])", r"\1 \2",
                                  rest_of_line, count=1)
            split_line = rest_of_line.split()
            if len(split_line) == 4:
                spring, _, node, device = split_line
            else:
                spring, _, node, device = split_line + [""]

        if insert_type in ["Pin", "Offset"]:
            fix_id = lookup_pin_id(pins_lookup, brc, node)
        elif insert_type == "Transfer":
            fix_id = ""
            if node == "<OTHER>":
                probe_list = probe_dict["<Extra>"]
            else:
                probe_list = probe_dict[node]

            # only transfers.
            b_probes = (prb for prb in probe_list if prb.name.startswith("T"))
            if top_flag:
                matched = [prb for prb in probe_list if
                           prb.coord.flip_coord() == coord]
            else:
                matched = [prb for prb in probe_list if prb.coord == coord]

            matched_prb_count = len(matched)

            if matched_prb_count == 1:
                fix_id = matched[0].name

            if fix_id == "":
                fp_logger.info("unable to find probe name for node {} at inserts location: {}, fixture locations: {}".format(
                    node, coord, probe_list))

        elif insert_type.endswith(" mil"):
            fix_id = ""

            probe_list = probe_dict[node]
            # only board probes (not transfer)
            b_probes = (prb for prb in probe_list if prb.name.startswith("P"))
            matched = [prb for prb in probe_list if prb.coord == coord]
            matched_prb_count = len(matched)

            if matched_prb_count == 1:
                fix_id = matched[0].name

            if fix_id == "":
                fp_logger.info("unable to find probe name for node {} at inserts location: {}, fixture locations: {}".format(
                    node, coord, probe_list))

        else:
            fix_id = ""

        return coord, InsertTuple(brc, insert_type,
                                  spring, node, device, fix_id, coord)
    else:
        fp_logger.info("ERROR: parse_inserts_line failed to parse %s", line)


def get_inserts(fixture_path, pins_lookup, probe_dict):
    """
    This function extracts the relevent data from the inserts file.

    the data is returned in a dictionary, of the form {brc: (insert data)}

    note that the brc information is ignored, is it can be regenerated using
    xy_to_brc.
    """

    inserts = OrderedDict()
    top_inserts = OrderedDict()

    inserts_path = fixture_path / "inserts"
    with inserts_path.open() as f_handle:
        top_flag = False
        for raw_line in f_handle:
            line = raw_line.strip()

            if "*+*+* Top *+*+*" in line:
                top_flag = True
                continue

            if not line.startswith(("(", "[", "*")):
                continue

            if line.startswith("(b"):
                continue

            x_y, inserts_data = parse_inserts_line(
                line, pins_lookup, probe_dict, top_flag)

            if top_flag:
                top_inserts[x_y] = inserts_data
            else:
                inserts[x_y] = inserts_data

    inserts_lookup = {}
    for x_y, item in inserts.items():
        brc = item.brc

        if brc not in inserts_lookup:
            inserts_lookup[brc] = x_y
        else:
            fp_logger.info("duplicate brc location found in inserts: %s", brc)

    top_inserts_lookup = {}
    for x_y, item in top_inserts.items():
        brc = item.brc

        if brc not in top_inserts_lookup:
            top_inserts_lookup[brc] = x_y
        else:
            fp_logger.info("duplicate brc location found in inserts: %s", brc)

    fp_logger.info(
        "inserts found; Bottom: %d, Top: %d",
        len(inserts),
        len(top_inserts))

    return inserts, top_inserts, inserts_lookup, top_inserts_lookup


def extract_b_r_c(token_line, automatic=False):
    """
    This function extracts the bank row and column
    accounting for negative rows.
    (which were previously ignored)
    """
    
    # account for negative row.
    if "-" in token_line[0]:
        bank_row, column, _ = \
            token_line[:3]
            
        bank, row = bank_row.split("-")
        row = f"-{row}"
        
        # automatic doesn't have a wrap number
        if automatic:
            token_line = token_line[2:]
        else:
            token_line = token_line[3:]
        
    else:
        # then get the 'from' info
        bank, row, column, _ = \
            token_line[:4]
        
        if automatic:        
            token_line = token_line[3:]
        else:
            token_line = token_line[4:]

    return f"{bank}{row:>6} {column:>6}", token_line
    

def get_manual_line(line, inserts):
    """
    This function converts a manual line
    from the wires file into an Automatic line

    This is important because the Automatic line
    contains X, Y information which is more precise.

    Also note that the terminals are not included
    in the automatic wiring information.

    Any terminal information will have to be
    manually included afterwards.
    """

    # the terminal flag goes True if the "to_brc" is a terminal
    # this allows the X, Y values to be 0, 0
    terminal_flag = False

    # set up default values (for when they are missing)
    device = ""

    # split line into tokens:
    token_line = line.split()

    # first, get the wire info
    length, gauge, colour = \
        token_line[:3]
    token_line = token_line[3:]
    
    f_type = token_line[0]
    token_line = token_line[1:]
    
    from_brc, token_line = extract_b_r_c(token_line)
    

    # finally get the 'to' info.
    to_type = token_line[0]

    token_line = token_line[1:]

    if to_type == "Term":
        to_brc = token_line[0]
        to_number = token_line[1]
        terminal_flag = True

    elif to_type in ["Pin", "Tran"]:
    
   
        to_brc, token_line = extract_b_r_c(token_line)

    elif to_type == "Prob":
        if len(token_line) == 5:
            device = token_line[-1]
            token_line = token_line[:-1]

   
        to_brc, token_line = extract_b_r_c(token_line)

    else:
        fp_logger.info("ERROR: get_manual_line failed to parse %s", line)

    from_xy = inserts[from_brc]
    if terminal_flag:
        to_xy = (0, 0)
    else:
        to_xy = inserts[to_brc]

    return WireTuple(WireInfo(length, gauge, colour),
                     from_brc, to_brc, from_xy, to_xy)


def get_brc_terminal(token_line, inserts):
    """
    This function extracts the terminal / brc from the
    from / to section of an automatic wires file.
    """
    terminal_flag = False

    # get the 'to brc' data, then
    # remove it from the line.
    if token_line[0].startswith(("(", "[", "*")):
        result, token_line = extract_b_r_c(token_line, automatic=True)
    else:
        
        terminal_flag = True
        result = token_line[0]

        token_line = token_line[1:]

    if terminal_flag:
        xy = (0, 0)
    else:
        xy = inserts[result]

    return token_line, result, xy


def get_automatic_line(line, inserts):
    """
    this function extracts the info from an "Automatic" formatted
    line in the wires file. It will also work on a "Wireless" formatted
    line in the wires file.
    """

    terminal_flag = False

    # split line into tokens:
    token_line = line.split()

    # first, get the wire info,
    # then remove the wire info
    # from the line
    length, gauge, colour = \
        token_line[:3]

    token_line = token_line[3:]

    # get the from_brc and update the token line
    # the from_brc could be a pin or a terminal
    token_line, from_brc, from_xy = get_brc_terminal(token_line, inserts)


    # get the to_brc and update the token line
    # the to_brc could be a pin or a terminal
    token_line, to_brc, to_xy = get_brc_terminal(token_line, inserts)

    return WireTuple(WireInfo(length, gauge, colour),
                     from_brc, to_brc, from_xy, to_xy)


def get_wires(fixture_path, all_inserts):
    """
    This function is intended to extract wires from the wires file.

    if the wires file is automatic, then the BRC information is ignored.

    if the wires file is manual, then the inserts file is used to match
    brc addresses, and provide an xy coord.
    """

    wiring_method_label = "Wiring Method : "

    wires_path = fixture_path / "wires"
    wiring_method = ""

    extra_pins_flag = False
    top = False

    inserts, top_inserts = all_inserts

    wires_list = []
    top_wires_list = []

    with open(wires_path) as wires:
        for raw_line in wires:
            line = raw_line.strip()

            if "*+*+* Top *+*+*" in line:
                top = True
                inserts = top_inserts
                continue

            if line.startswith("Extra Pins"):
                extra_pins_flag = True
                continue

            if extra_pins_flag and line.startswith("Length"):
                extra_pins_flag = False
                continue

            if line in ["", "\f"] or \
               line.startswith(("|", "-", "Page ", "|From", "( Pin )", "Length ", "Length|")) or \
               line.endswith(("/wires")) or \
               "FIXTURE WIRING REPORT" in line:
                continue

            if line.startswith(wiring_method_label):
                wiring_method = line.replace(wiring_method_label, "")
                continue

            # skip the settings at the top.
            if " : " in raw_line:
                continue

            if extra_pins_flag:
                continue

            if wiring_method == "Manual":
                data = get_manual_line(line, inserts)
            else:
                data = get_automatic_line(line, inserts)

            if top:
                top_wires_list.append(data)
            else:
                wires_list.append(data)

    fp_logger.info(
        "wires found; Bottom: %d, Top: %d",
        len(wires_list),
        len(top_wires_list))

    return wires_list, top_wires_list


def get_fixture_info(fixture_path):
    """
    This function uses the appropriate wires and inserts function to extract the wires
    and inserts.

    also get list of pins to allow processing to assosiate each pin with
    an assigned BRC (using the offsets)
    """

    # pins_lookup: {"B R.00 C.0": PinsTuple(brc, status, (x_offset, y_offset)}
    # probes_dict: {node_name: probe_tuple(probe_name, fix_coord)}

    pins_lookup, probes_dict, ground_nodes = fi.parse_fix_file(
        fixture_path)

    inserts, top_inserts, inserts_lookup, top_inserts_lookup = get_inserts(
        fixture_path, pins_lookup, probes_dict)

    wires, top_wires = get_wires(
        fixture_path, (inserts_lookup, top_inserts_lookup))

    fixture_data = FixtureTuple(wires, top_wires, inserts, top_inserts, ground_nodes=ground_nodes)

    throughput_multiplier, module_list = fm.throughput_multiplier(
        fixture_data)

    return fixture_data, throughput_multiplier, module_list


def clean_targets(fixture_dir):
    """
    This function is called when there is a processing problem.
    It may also be called manually by the operator.
    """

    def simplify_error(exception_message, old_path, depth):
        """
        a helper function to remove the
        """

        exception_message = str(exception_message).replace("\\\\", "\\")

        new_path = old_path.relative_to(old_path.parents[depth - 1])

        return exception_message.replace(str(old_path), ".\\" + str(new_path))

    success_flag = True
    # todo make clean targets function.
    for folder in FIXTURE_TARGETS:

        folder_path = fixture_dir / folder

        for file in ["wires", "inserts"]:

            file_path = folder_path / file

            if file_path.is_file():
                try:
                    file_path.unlink()
                except PermissionError as e:
                    error_message = simplify_error(str(e), file_path, 2)

                    mb.showerror("ERROR", error_message)
                    success_flag = False
                    break

        if not success_flag:
            break

        if folder_path.is_dir():
            try:
                folder_path.rmdir()
            except OSError as e:
                error_message = simplify_error(str(e), folder_path, 1)
                mb.showerror("ERROR", error_message)
                success_flag = False

    return success_flag


def process_fixture_info(fixture_dir, flags, generation_flags):

    default_levels = ["NOT_SET", "DEBUG", "INFO",
                      "WARNING", "ERROR", "CRITICAL"]

    log_level = flags.log_level.upper()

    if log_level in default_levels:
        fp_logger.setLevel(getattr(logging, log_level))

    original_fixture_data, throughput_multiplier, module_list = get_fixture_info(
        fixture_dir)

    flags = flags._replace(throughput_multiplier=throughput_multiplier)

    wires_settings = get_settings(fixture_dir / "wires")
    inserts_settings = get_settings(fixture_dir / "inserts")

    joint_settings = inserts_settings
    original_fixture_data = original_fixture_data._replace(
        fixture_size=joint_settings["fixture_size"])

    transforms_dict = fp.get_transforms()

    if generation_flags.processing:
        destination_folders = [
            target for target in FIXTURE_TARGETS if getattr(flags, target)]
    elif generation_flags.gplane_plot:
        destination_folders = ["."]

    # break_flag is set to True if there are any problems.
    break_flag = False

    # set to True when processing and output executes correctly.
    success_flag = False

    for target_folder in destination_folders:

        if target_folder == "output_plot":
            target_folder = "."

        output_dir = fixture_dir / target_folder

        output_dir.mkdir(parents=True, exist_ok=True)

        wires_settings["wiring_method"] = "Automatic"
        inserts_settings["wiring_method"] = "Automatic"

        fixture_data = original_fixture_data

        if target_folder == ".":
            fixture_target = "wiring_machine"
        else:
            fixture_target = target_folder

        for (name, rule, targets), transform in transforms_dict.items():
            # has this transform been selected?
            if not rule(flags):
                continue

            # is the transform to be run on this target?
            if fixture_target not in targets:
                continue

            fp_logger.info(
                "applied '%s' transform on '%s' target",
                name,
                target_folder)

            fixture_data = transform(
                fixture_dir, fixture_data, flags, fixture_target)

            # A return of None means a problem in the fixture processing
            if fixture_data is None:

                # None is returned when there is an error.
                # the error message is displayed by the function
                # creating the error, along with the log entry.
                # the already created targets (if any) will now
                # be deleted so that garbage data is not used.
                print("exitted early")
                break_flag = True
                clean_targets(fixture_dir)
                break

        if break_flag:
            break

        success_flag = False
        plot_filename = ""
        # in ground plane mode, only the
        # ground plane data is produced.
        if generation_flags.gplane_plot:
            plot_filename = "ground_brc_plot.dxf"
            flags = flags._replace(output_plot=False)
        elif flags.output_plot:
            plot_filename = "full_fixture_plot.dxf"

        if plot_filename and target_folder == ".":
            success_flag = od.output_fixture_plot(
                output_dir,
                plot_filename,
                joint_settings,
                fixture_data,
                generation_flags,
                module_list,
                flags)

        if generation_flags.processing and target_folder in FIXTURE_TARGETS:

            success_flag1 = output_wires_inserts(
                output_dir,
                fixture_dir,
                wires_settings,
                fixture_data,
                "wires")

            success_flag2 = output_wires_inserts(
                output_dir,
                fixture_dir,
                inserts_settings,
                fixture_data,
                "inserts")

            success_flag = success_flag1 and success_flag2

    if success_flag:
        if generation_flags.gplane_plot:

            info_text = "    Ground plane plot and list generated!\n\n"\
                        #"    Please check 'gplane_plot.dxf' and/or 'ground_brc_list.txt'"
            "    Please check 'ground_brc_list.txt'"
            mb.showinfo("processing complete", info_text)

        if generation_flags.processing:
            info_text = "    New wires and inserts generation complete!\n\n"\
                        "    Please check 'fixture/wiring_machine' or 'fixture/verifier'"

            mb.showinfo("Processing complete", info_text)

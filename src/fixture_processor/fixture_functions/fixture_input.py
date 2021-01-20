import re
import logging
import typing

from dataclasses import dataclass
from collections import namedtuple

from src.fixture_processor.fixture_functions import fixture_maths as fm


fp_logger = logging.getLogger('fixture_processing.fixture_input')

# Handy storage namedtuples.


@dataclass
class Placement:
    offset: fm.CoordTuple = fm.CoordTuple(0, 0)
    rotation: float = 0.0

    def apply(self, point: fm.CoordTuple):
        return point.rotate(self.rotation) + self.offset


DEFAULT_PLACEMENT = Placement()

TOOLING_TUPLE = namedtuple("Tooling", ["point", "diameter"])

# Handy Regex
PLACEMENT_RE = re.compile(
    r"PLACEMENT +(?P<x>-?\d+), +(?P<y>-?\d+) +(?P<rotation>\d+(\.\d+))?;")


class PinsTuple(typing.NamedTuple):
    brc: fm.PinID
    status: str
    offset: typing.Tuple[int, int]


def apply_placement(placement_list=None):
    """
    Generates a function which 
    can apply multiple placement
    offsets and rotations, one after the other.
    """

    if placement_list == None:
        placement_list = []

    elif isinstance(placement_list, Placement):
        placement_list = [placement_list]

    def inner(fixture_location):

        for placement_data in placement_list:
            fixture_location = placement_data.apply(fixture_location)

        return fixture_location
    return inner


def get_outline_info(fixture_path):
    """
    The following function when given a path to a fixture file,
    will extract outlines, tooling information, pins, and where relevent,
    Board numbers.
    """

    # parse flags
    panel_flag = False
    board_flag = False
    outline_flag = False
    tooling_flag = False

    # storage variables.
    board_name = ""
    panel_name = ""

    panel_placement = Placement()
    board_placement = Placement()

    # dictionaries for storing multiple
    # variables.
    outline_list = []
    outlines = {}

    tooling_list = []
    tooling = {}

    fixture_file_path = fixture_path / "fixture.o"

    fp_logger.info(
        "Getting fixture information from '%s'",
        fixture_file_path.as_posix())

    with fixture_file_path.open() as fixture_file:

        for raw_line in fixture_file:
            line = raw_line.strip()
            if not line:
                continue

            # rules for the panel_flag
            if line.startswith("PANEL"):
                panel_flag = True
                panel_re = r'^PANEL +"?([^"\n ]+)"?'
                panel_name = re.sub(panel_re, r"\1", line)
                if not panel_name:
                    fp_logger.debug(
                        "error parsing panel name at line: '%s' using re.sub(%s, r'\1')",
                        line,
                        panel_re)
                panel_placement = DEFAULT_PLACEMENT
                continue

            if panel_flag and line.startswith("END PANEL"):
                panel_flag = False
                continue

            # rules for the board_flag
            if line.startswith("BOARD"):
                board_flag = True

                board_re = r'^BOARD +"?([^"\n ]+)"?'
                board_name = re.sub(board_re, r"\1", line)
                if not board_name:
                    fp_logger.debug(
                        "error parsing board name at line: '%s' using re.sub(%s, r'\1')",
                        line,
                        board_re)

                board_placement = DEFAULT_PLACEMENT
                continue

            if panel_flag and line.startswith("END BOARD"):
                board_flag = False
                continue

            if line.startswith("PLACEMENT"):
                # ensure no comments affect parsing.
                line = line[:line.index("!")].strip()

                placement_data = PLACEMENT_RE.match(line)
                if placement_data is None:
                    fp_logger.debug(
                        "unable to parse placement (line: '%s' using regex: r\"%s\"", line, PLACEMENT_RE)

                x = int(placement_data.group("x"))
                y = int(placement_data.group("y"))
                rotation = float(placement_data.group("rotation"))

                if panel_flag and not board_flag:
                    panel_placement = Placement(fm.CoordTuple(x, y), rotation)

                # applying panel placement to board placement
                # when a board is within a panel
                elif panel_flag and board_flag:

                    # insert the board placement statement at the start of the list.
                    # (as it would be applied first)
                    board_placement = [
                        Placement(fm.CoordTuple(x, y), rotation), panel_placement]

                else:

                    board_placement = Placement(fm.CoordTuple(x, y), rotation)

            # provide local variables depending on the states
            # of board_flag or panel_flag
            if panel_flag and not board_flag:
                local_placement = apply_placement(panel_placement)
                local_name = "P_" + panel_name
            else:
                local_placement = apply_placement(board_placement)
                local_name = "B_" + board_name

            # add the outline rules.
            if line.startswith("OUTLINE"):
                outline_flag = True
                continue

            if outline_flag:
                x, y = [int(n) for n in line.rstrip(";").split(", ")]

                outline_list.append(local_placement(fm.CoordTuple(x, y)))

                # is this the last outline entry?
                if not line.endswith(";"):
                    continue

                outline_flag = False

                outlines[local_name] = outline_list
                outline_list = []
                continue

            # add rules for the tooling
            if line.startswith("TOOLING"):
                tooling_flag = True
                continue

            if tooling_flag:
                split_line = line.split()

                three_items = len(split_line) == 3
                first_isdigit = split_line[0].isdigit()

                if not three_items or not first_isdigit:
                    tooling_flag = False
                    tooling[local_name] = tooling_list
                    tooling_list = []
                    continue

                width, x, y = [int(item.strip(", ;")) for item in split_line]

                # calculate the offset due to placement
                point = local_placement(fm.CoordTuple(x, y))
                tooling_list.append(TOOLING_TUPLE(point, width))

    return (outlines, tooling)


def process_pin_lines(pins_lines):
    """
    After the parent function collections all of the
    pin lines from the fixture, this function converts it into
    a dict.
    """

    pins_dict = {}
    pins_lookup = {}

    pin_status_list = ["BLOCKED", "DRILLED", "SOCKETED", "OVERRIDE"]

    for node_name, line in pins_lines:
        split_line = line.rstrip(';').split()

        brc = fm.PinID(split_line[0])

        status = "SOCKETED"
        x_offset = 0
        y_offset = 0

        num_of_items = len(split_line)

        if num_of_items == 1:
            pins_data = PinsTuple(brc, status, (x_offset, y_offset))
            pins_lookup[brc] = pins_data

            inserts_loc = fm.create_brc_loc(brc)
            pins_lookup[inserts_loc] = pins_data

            if node_name in pins_dict:
                pins_dict[node_name].append(pins_data)
            else:
                pins_dict[node_name] = [pins_data]
            continue

        # this flag goes True if the status is updated.
        status_flag = False

        for item in split_line[1:2]:
            if item in pin_status_list:
                status_flag = True
                status = item

        # only 2 items, and an updated status
        # means no offset info.
        if status_flag and num_of_items == 2:
            pins_data = PinsTuple(brc, status, (0, 0))

            inserts_loc = fm.create_brc_loc(brc)
            pins_lookup[inserts_loc] = pins_data

            if node_name in pins_dict:
                pins_dict[node_name].append(pins_data)
            else:
                pins_dict[node_name] = [pins_data]
            continue

        if status_flag:
            offset_data = split_line[2:]
        else:
            offset_data = split_line[1:]

        if len(offset_data) == 1:
            offset_data.append(0)

        y_offset, x_offset = [int(n) for n in offset_data]

        pins_data = PinsTuple(brc, status, (x_offset, y_offset))

        inserts_loc = fm.create_brc_loc(brc, (x_offset, y_offset))
        pins_lookup[inserts_loc] = pins_data

        if node_name in pins_dict:
            pins_dict[node_name].append(pins_data)
        else:
            pins_dict[node_name] = [pins_data]

    fp_logger.info("pins found: %d", sum(len(pins)
                                         for pins in pins_dict.values()))

    return pins_lookup


def parse_fix_file(fixture_path):
    """
    This function extracts all of the pins from the fixture file.
    the nets they are connected to are unimportant, however the offsets
    will be extrated from the fixture file.

    The offsets are needed because they are used to match brc locations
    with the coresponding pin.

    This is important because fixture verifier can reports errors when presented
    with offset BRC information.
    """

    f_file_path = fixture_path / "fixture.o"

    probe_tuple = namedtuple("probe_tuple", ["name", "coord"])

    panel_flag = False
    board_flag = False

    pins_flag = False
    wires_flag = False
    ground_flag = False
    probes_flag = False

    panel_offset = fm.CoordTuple(0, 0)
    panel_rotate = 0.0

    board_offset = fm.CoordTuple(0, 0)
    board_rotate = 0.0

    pins_lines = []
    pins_dict = {}

    probes_dict = {}

    wires_lines = []

    ground_nodes = []

    node_name = ""

    end_node_trigger = ("NODE ", "END UNIT", "TESTJET")

    with open(f_file_path) as fixture:

        def insert_end_node(fixture):
            for raw_line in fixture:

                line = raw_line.strip()

                if line.startswith(end_node_trigger):
                    yield "END NODE"
                yield raw_line

        for raw_line in insert_end_node(fixture):
            line = raw_line.strip()

            if not line:
                continue

            if line.startswith("PANEL "):
                panel_flag = True
                panel_offset = fm.CoordTuple(0, 0)
                panel_rotate = 0.0
                continue

            if line.startswith("END PANEL"):
                panel_flag = False
                continue

            if line.startswith("BOARD "):
                board_flag = True
                board_offset = fm.CoordTuple(0, 0)
                board_rotate = 0.0
                continue

            if line.startswith("END BOARD"):
                board_flag = False
                continue

            if line.startswith("PLACEMENT "):

                # remove the semi colon and all text afterwards.
                semicolon_index = line.find(";")
                line = line[:semicolon_index]

                # remove the preceding placement

                _, coord_x, coord_y, rotation = line.split()
                int_x = int(coord_x.strip(","))
                int_y = int(coord_y)
                f_rotation = float(rotation)
                if board_flag:
                    board_offset = fm.CoordTuple(int_x, int_y)
                    board_rotate = f_rotation
                else:
                    panel_offset = fm.CoordTuple(int_x, int_y)
                    panel_rotate = f_rotation

            if line.startswith("OTHER"):
                node_name = "<Extra>"
                ground_flag = False

            elif line.startswith("NODE "):
                ground_flag = False
                split_line = line.split()
                node_name = split_line[1].strip('"')
                if line.endswith(" GROUND"):
                    ground_flag = True
                    ground_nodes.append(node_name)

            if line == "PINS" and node_name:
                pins_flag = True
                wires_flag = False
                probes_flag = False
                continue

            if line in ["PROBES", "TRANSFERS"] and node_name:
                pins_flag = False
                wires_flag = False
                probes_flag = True
                continue

            if line.startswith("WIRES") and ground_flag:
                pins_flag = False
                wires_flag = True
                probes_flag = False
                continue

            if pins_flag and not line.endswith(";"):
                pins_flag = False
                continue

            if probes_flag and not line.endswith(";"):
                probes_flag = False
                continue

            if wires_flag and not line.endswith(";"):
                wires_flag = False
                continue

            if pins_flag:
                pins_lines.append((node_name, line))
                continue

            if probes_flag:
                name, coord_x, coord_y = line.split()[:3]
                top_flag = " TOP" in line
                int_x = int(coord_x.strip(","))
                int_y = int(coord_y.strip(";"))
                probe_coord = fm.CoordTuple(int_x, int_y)

                board_coord = probe_coord.rotate(board_rotate) + board_offset
                fix_coord = board_coord.rotate(panel_rotate) + panel_offset
                if top_flag:
                    fix_coord = fix_coord.flip_coord()

                if node_name in probes_dict:
                    probes_dict[node_name].append(probe_tuple(name, fix_coord))
                else:
                    probes_dict[node_name] = [probe_tuple(name, fix_coord)]

            if wires_flag:
                wires_lines.append((node_name, line))

    pins_lookup = process_pin_lines(pins_lines)

    return pins_lookup, probes_dict, ground_nodes

from datetime import datetime
from . import fixture_maths as fm

import logging

fp_logger = logging.getLogger('fixture_processing.fixture_output')


WIRES_AUTOMATIC_KEY = """\
    ( Pin )   [ Probe ]    Length = in.
"""

AUTOMATIC_TABLE_HEADER = {
    "wires": """\
                |     From      |     To        |     From      |      To
Length|Ga|Color |(b   r      c )|(b   r      c )|    X       Y  |    X       Y
------|--|------|---------------|---------------|-------|-------|-------|-------
""",
    "inserts": """\
(b   r      c )     X       Y     Type   Spring Node Name  On Device
---------------|---------------|--------|------|----------|---------------------
"""}

# example:
# AGILENT ICT FIXTURE WIRING REPORT          Tue Mar 20 11:33:07 2018
AUTOMATIC_REPORT_LINE = {
    "wires": """\
AGILENT ICT FIXTURE WIRING REPORT          %a %b %d %H:%M:%S %Y
""",
    "inserts": """\
AGILENT ICT FIXTURE INSERTION REPORT          %a %b %d %H:%M:%S %Y
"""}

WIRES_LINE = """\
{length:>6} {gauge:>2} {colour:^6} {from_brc} {to_brc:<15} {from_x:>7} {from_y:>7} {to_x:>7} {to_y:>7}
"""

INSERTS_LINE = """\
{brc} {x:>7} {y:>7} {insert_type:^8}{spring_space}{spring:^6} {node:^10}{device_space}{device}
"""

DASHES = """\
------------------------------------------------------------------------------
"""

TOP = """\

                                *+*+* Top *+*+*

"""

SETTINGS = """\
Fixture Type : {fixture_type}
Fixture Size : {fixture_size}
Fixture Part Number : {fixture_part_num}
Top Probes Allowed : {top_probes}
Autofile : {autofile}
Units : {units}
Wiring Method : {wiring_method}
"""


def insert_page_break(file_handle, page, date_line, source_dir, name):
    """
    Used to simplify the calling of page breaks.
    """
    file_handle.write("\f\n")
    file_handle.write("Page {}\n".format(page))
    file_handle.write(DASHES)
    file_handle.write(date_line)
    file_handle.write("\n")
    file_handle.write((source_dir / name).as_posix())
    file_handle.write("\n")
    file_handle.write(DASHES)
    file_handle.write("\n")
    file_handle.write(AUTOMATIC_TABLE_HEADER[name])


def write_wires_line(wire, top_flag):

    line_dict = {}
    lgc, from_brc, to_brc, from_xy, to_xy, custom_wire = wire
    length, gauge, colour = lgc
    from_x, from_y = from_xy
    to_x, to_y = to_xy

    line_dict["length"] = length
    line_dict["gauge"] = gauge
    line_dict["colour"] = colour

    line_dict["from_brc"] = from_brc
    line_dict["to_brc"] = to_brc

    line_dict["from_x"] = from_x
    if top_flag:
        line_dict["from_y"] = -from_y
    else:
        line_dict["from_y"] = from_y

    line_dict["to_x"] = to_x

    # probes in the automatic layout have inversed Y.
    if to_brc[0] == "[":
        line_dict["to_y"] = -to_y
    else:
        line_dict["to_y"] = to_y

    return WIRES_LINE.format(**line_dict)


def write_inserts_line(insert):

    xy, data = insert
    x, y = data.coord

    line_dict = {}

    line_dict["x"] = x
    line_dict["y"] = y

    brc = data.brc
    line_dict["brc"] = brc

    line_dict["insert_type"] = data.insert_type
    line_dict["spring"] = str(data.spring) + " oz" if data.spring else ""

    if data.spring or data.node or data.device:
        line_dict["spring_space"] = " "
    else:
        reduced_inserts_line = INSERTS_LINE.split("{spring_space}")[0]
        return reduced_inserts_line.format(**line_dict) + "\n"

    node = "" if data.node is None else data.node

    if node == "<Extra>":
        line_dict["node"] = "Extra"
    elif node == "<OTHER>":
        line_dict["node"] = "OTHER"
    elif node == "<AUTOFILE>":
        line_dict["node"] = "AUTOFILE"
    else:
        line_dict["node"] = node

    line_dict["device"] = data.device
    line_dict["device_space"] = " " if data.device else ""

    return INSERTS_LINE.format(**line_dict)


def output_wires_inserts(new_dir, source_dir, settings_dict, fixture_data, name):
    """
    This function outputs the wires and inserts
    data to a new wires and inserts file within the
    given dir.

    The output will be provided in Automatic mode to subvert the requirement
    of calculating wire numbers (this is subject to change).
    """

    if name == "wires":
        data_list, top_data_list = fixture_data._wires
        inserts_bottom, inserts_top = fixture_data._inserts
    else:
        data_list, top_data_list = fixture_data._inserts
        inserts_bottom, inserts_top = None, None

    output_path = new_dir / name

    today = datetime.now()

    date_line = today.strftime(AUTOMATIC_REPORT_LINE[name])

    wires_setting_txt = SETTINGS.format(**settings_dict)

    with output_path.open("w") as f_data:

        f_data.write(DASHES)
        f_data.write(date_line)
        f_data.write("\n")
        f_data.write((source_dir / name).as_posix())
        f_data.write("\n")
        f_data.write(DASHES)
        f_data.write("\n")
        f_data.write(wires_setting_txt)
        f_data.write(DASHES)

        if name == "wires":
            f_data.write("\n")
            f_data.write(WIRES_AUTOMATIC_KEY)
            f_data.write("\n")

        f_data.write(AUTOMATIC_TABLE_HEADER[name])

        line_count = 0
        lf_count = 0
        lf_distance = 5
        if name == "wires":
            page_break = 38
        else:
            page_break = 42
        page = 1

        # convert the inserts dict to a list of tuples,
        # to allow convenient output.
        if name == "inserts":
            data_list = [(xy, data) for xy, data in data_list.items()]
            if top_data_list:
                top_data_list = [(xy, data)
                                 for xy, data in top_data_list.items()]

        if top_data_list:
            all_data = data_list + [None] + top_data_list
        else:
            all_data = data_list

        top_flag = False
        for data in all_data:

            if data is None:
                top_flag = True

                line_count = line_count + 6
                f_data.write(TOP)
                f_data.write(AUTOMATIC_TABLE_HEADER[name])
                continue

            if top_flag:
                inserts = inserts_top
            else:
                inserts = inserts_bottom

            if name == "wires":
                replace_dict = {}
                from_xy, to_xy = data._get_xy_coords

                for xy, label in zip([from_xy, to_xy], ["from", "to"]):
                    terminal_check = f"_{label}_is_terminal"
                    # skip if the from / to entry is a terminal.
                    if getattr(data, terminal_check):
                        continue

                    insert = inserts[xy]
                    if insert.coord == xy:
                        continue

                    replace_dict[f"{label}_xy"] = insert.coord
                    replace_dict[f"{label}_brc"] = insert.brc

                if replace_dict:

                    # re-calculate wire length if wire is not on
                    # a terminal.
                    if not data._is_terminal_wire:
                        from_insert = inserts[from_xy]
                        to_insert = inserts[to_xy]
                        wire_length = fm.get_wire_length(
                            from_insert, to_insert)

                        replace_dict["wire_info"] = data.wire_info._replace(
                            length=wire_length)

                    data = data._replace(**replace_dict)

                f_data.write(write_wires_line(data, top_flag))
            else:
                f_data.write(write_inserts_line(data))

            line_count = line_count + 1
            lf_count = lf_count + 1
            if name == "inserts" and lf_count >= lf_distance:
                lf_count = 0
                line_count = line_count + 1
                f_data.write("\n")

            if line_count >= page_break:
                line_count = 0
                page = page + 1
                if name == "wires":
                    page_break = 44
                else:
                    page_break = 48
                insert_page_break(f_data, page, date_line, source_dir, name)

    return True

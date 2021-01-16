"""
This script is intended to be used to take fixture
data and output plots.

It will also output BRC lists.
"""

import logging

from tkinter import messagebox as mb

import operator as op

from dxfwrite import DXFEngine as dxf
from turtle import Vec2D
from itertools import product

from src.fixture_processor.fixture_functions import fixture_maths as fm
# from fixture_processor.fixture_functions import fixture_processing as fp

fp_logger = logging.getLogger('fixture_processing.output_data')

# For consistancy, each element will be scaled down.
# This is to allow simple code
PLOT_SCALE = 0.00254


def scaled_circle(radius, center):

    scaled_radius = radius * PLOT_SCALE
    scaled_centre = center.to_mm_dxf_point()

    return dxf.circle(scaled_radius, scaled_centre)


def scaled_line(point1, point2):
    return dxf.line(point1.to_mm_dxf_point(), point2.to_mm_dxf_point())


def scaled_text(text, insert, height):
    return dxf.text(text, insert.to_mm_dxf_point(), height * PLOT_SCALE)


def output_ground_pins_list(fixture_data, flags):
    """
    This function generates a list of interface pins
    within the fixture which are ground BRCs.
    """

    # get the bottom wires and inserts
    wires, inserts = fixture_data._bottom

    # are asru switched grounds considerered grounds?
    include_asru = flags.gplane_include_asru

    # store ground pins in a set.
    ground_inserts = set()

    # assume that only ground BRCs with a wire
    # will be included in this list.

    for coord, insert_data in inserts.items():

        if insert_data._is_fixture_ground(include_asru=include_asru):
            ground_inserts.add(insert_data)

    return ground_inserts


def circle_cross(radius, center, *, cross_overlap=1, initial_angle=45):
    """
    yields elements which make up a circle with 
    a diagonal cross.    
    """

    yield scaled_circle(radius, center)

    # take the overlap into account
    # when drawing the lines.
    line_radius = radius * cross_overlap

    # Draw a line straight up as a base reference.
    # (This will later be rotated and offset)
    origin_point = Vec2D(0, radius)

    for angle in [initial_angle, initial_angle + 90]:

        point1 = center + origin_point.rotate(angle)
        point2 = center + origin_point.rotate(angle + 180)

        yield scaled_line(point1, point2)


def rectangle(top_left, width, height):
    """
    Given a top left coord along with a width and height
    This function yields lines which make up a rectangle.
    """

    top_right = top_left + (width, 0)
    bot_right = top_right - (0, height)
    bot_left = bot_right - (width, 0)

    # place all locations in a list.
    # add top_left on the end, for the final line
    corners = [top_left, top_right, bot_right, bot_left, top_left]

    for point1, point2 in zip(corners, corners[1:]):
        yield scaled_line(point1, point2)


def square_point(radius, center, initial_angle=0):
    """
    creates a simple square around a point with
    the first corner being placed at the angle
    given (default 0 degrees (straight up))
    """
    origin_corner = Vec2D(0, radius).rotate(initial_angle)

    corner1 = origin_corner + center
    corner2 = origin_corner.rotate(90) + center
    corner3 = origin_corner.rotate(180) + center
    corner4 = origin_corner.rotate(270) + center

    corners = [corner1, corner2, corner3, corner4, corner1]
    for point1, point2 in zip(corners, corners[1:]):
        yield scaled_line(point1, point2)


def add_plot_essentials(drawing, fixture_settings, fixture_data, flags):

    # add the essential plot layers
    drawing.add_layer("FIXTURE_OUTLINE", color=144)
    drawing.add_layer("MODULE_OUTLINE", color=192)
    drawing.add_layer("VACUUM_PORTS", color=144)
    drawing.add_layer("CARD_OUTLINE", color=192)

    # The default (none offset) location of all
    # interface pins / brc pins.
    # includes ground BRCs.
    drawing.add_layer("TESTER_INTERFACE_PIN", color=144)
    drawing.add_layer("TESTER_INTERFACE_PIN_LABEL", color=144)

    # the fixture_rows set will contain
    # each row in this fixture (213, 105) etc.
    fixture_rows = set()

    # store the y value for each row.
    row_y_coord = {}

    # get the fixture size (Full / Bank 1 / Bank 2)
    fixture_size = fixture_settings["fixture_size"]

    origin = fm.CoordTuple(0, 0)
    # first, add the tooling origin.
    for element in circle_cross(1000, origin):
        element["layer"] = "FIXTURE_OUTLINE"

        drawing.add(element)

    # Then add the fixture outline.
    # starting by defining the origin

    fixture_height = fm.PHY_FIXTURE_MAXIMUM_Y
    if fixture_size == "Full":
        fixture_width = fm.PHY_FIXTURE_MAXIMUM_X
    else:
        fixture_width = fm.PHY_HALF_BANK_WIDTH

    top_left = fm.CoordTuple(-fm.X_TOOLING_OFFSET,
                             fm.PHY_FIXTURE_MAXIMUM_Y - fm.Y_TOOLING_OFFSET)

    for element in rectangle(top_left, fixture_width, fixture_height):
        element["layer"] = "FIXTURE_OUTLINE"
        drawing.add(element)

    # module outline skipped for now
    # vacuum port skipped for now.

    # card outline rectangle, only on rows with installed interface pins.
    # skipped for now.

    # get the bottom inserts
    bottom_inserts = fixture_data.bottom_inserts

    # collect the bank-row data
    for coord, data in bottom_inserts.items():

        # only process pins / offsets.
        if data.insert_type not in ["Pin", "Offset"]:
            continue

        brc = data.fix_id.brc
        bank = brc.bank
        row = brc.row

        half = brc.is_half_row

        # add this row to the
        fixture_rows.add((bank, row, half))

    # add the tester interface pins.
    for (bank, row, half), column in product(fixture_rows, range(1, 79)):

        # generate the name.

        brc_name = fm.PinID.from_elements(bank, row, column, half)

        coord = brc_name.to_xy(fixture_size)
        pin_circle = scaled_circle(90, coord)
        pin_circle["layer"] = "TESTER_INTERFACE_PIN"
        drawing.add(pin_circle)

        height = 100
        text = scaled_text(brc_name, coord + (150, (-height) / 2), height)
        text["layer"] = "TESTER_INTERFACE_PIN_LABEL"
        drawing.add(text)


def add_pins(drawing, fixture_settings, fixture_data, ground_inserts, flags):
    """
    This function draws in all of the inserted pins of the fixture.

    if a pin counts as a "ground" pin, it is given a different colour
     / layer.
    """

    # The location of fixture interface / brc pins,
    # after offset has been applied.
    # not including ground brcs.
    drawing.add_layer("FIXTURE_INTERFACE_PIN", color=4)

    # The location of the ground interface / brc pins.
    drawing.add_layer("GROUND_INTERFACE_PIN", color=100)

    offset_line_flag = False
    old_location_flag = False

    circle_size = 100

    # get a set of corrected pins, bottom only
    bottom_inserts = fixture_data.bottom_inserts

    gnd_brcs = [insert.fix_id.brc for insert in ground_inserts]

    for lookup_coord, data in bottom_inserts.items():

        coord = data.coord.flip_coord()
        lookup_coord = lookup_coord.flip_coord()

        # only process pins / offsets.
        if data.insert_type not in ["Pin", "Offset"]:
            continue
        brc = data.fix_id.brc

        # the proper location of the pin - assuming no offsets.
        ideal_coord = brc.to_xy(fixture_settings["fixture_size"])

        # if there is an offset, draw a line linking them.
        if coord != ideal_coord:

            if not offset_line_flag:
                drawing.add_layer("PIN_OFFSET_ARROW", color=144)

            line = scaled_line(coord, ideal_coord)
            line["layer"] = "PIN_OFFSET_ARROW"
            drawing.add(line)

        if coord != lookup_coord and lookup_coord != ideal_coord:
            # ensure the layer has been added.
            if not old_location_flag:
                drawing.add_layer(f"OLD_FIXTURE_INTERFACE_PIN", color=143)
                old_location_flag = True

            # add circle to indicate location
            pin_circle = scaled_circle(circle_size, lookup_coord)
            pin_circle["layer"] = f"OLD_FIXTURE_INTERFACE_PIN"
            drawing.add(pin_circle)

            height = circle_size
            x_offset = x_offset = height * 1.5

            text = scaled_text(data.fix_id.brc + "_OLD",
                               lookup_coord + (x_offset, (-height) / 2), height)
            text["layer"] = f"OLD_FIXTURE_INTERFACE_PIN"
            drawing.add(text)

            # add line to indicate its origin.
            line = scaled_line(lookup_coord, coord)
            line["layer"] = f"OLD_FIXTURE_INTERFACE_PIN"
            drawing.add(line)

        if brc in gnd_brcs:
            layer = "GROUND_INTERFACE_PIN"
        else:
            layer = "FIXTURE_INTERFACE_PIN"

        # pin_circle = scaled_circle(442.913385827, Vec2D(x, -y))
        pin_circle = scaled_circle(circle_size, coord)
        pin_circle["layer"] = layer
        drawing.add(pin_circle)


def add_probes(drawing, fixture_settings, fixture_data, flags):
    """
    This function extracts the probes (normal and transfer)
    And places them on the plot.
    """

    bottom_inserts, top_inserts = fixture_data._inserts

    loop_var = zip([bottom_inserts, top_inserts],
                   ["BOTTOM", "TOP"])

    for inserts, side in loop_var:

        # the following flags are made True if the corresponding layer
        # has been made for them.
        # This includes offset Transfer.
        probes_flag = False
        old_probes_flag = False

        transfers_flag = False
        custom_transfer_flag = False
        old_transfers_flag = False

        # first add the bottom probes (including transfer probes)
        for lookup_coord, data in inserts.items():

            coord = data.coord

            if side == "TOP":
                coord = coord.flip_coord()
                lookup_coord = lookup_coord.flip_coord()

            # set layer flags, skip unneeded inserts
            type = data.insert_type

            # only deal with Transfer from the bottom inserts.
            if type == "Transfer":

                if data.fix_id.startswith("custom"):
                    transfer_layer = f"{side}_CUSTOM_TRANSFER"
                    transfer_label_layer = f"{side}_CUSTOM_TRANSFER_LABEL"
                    transfer_label_brc = f"{side}_CUSTOM_TRANSFER_B_R_C"
                    
                    if not custom_transfer_flag:
                        drawing.add_layer(transfer_layer, color=2)
                        drawing.add_layer(transfer_label_layer, color=50)
                        layer_object =  drawing.add_layer(transfer_label_brc, color=50)
                        layer_object.off()
                        custom_transfer_flag = True

                else:
                    transfer_layer = f"{side}_TRANSFER"
                    transfer_label_layer = f"{side}_TRANSFER_LABEL"
                    transfer_label_brc = f"{side}_TRANSFER_B_R_C"

                    if not transfers_flag:
                        drawing.add_layer(transfer_layer, color=2)
                        drawing.add_layer(transfer_label_layer, color=50)
                        layer_object = drawing.add_layer(transfer_label_brc, color=50)
                        layer_object.off()
                        transfers_flag = True

                if side == "BOTTOM":
                    probe_size = 100
                    height = 100
                    x_offset = height * 1.5
                else:
                    probe_size = 50
                    height = 100
                    x_offset = height * 1.5

                pin_circle = scaled_circle(probe_size, coord)
                pin_circle["layer"] = transfer_layer
                drawing.add(pin_circle)

                text = scaled_text(data.fix_id, coord +
                                   (x_offset, (-height) / 2), height)
                text["layer"] = transfer_label_layer
                drawing.add(text)
                
                # add the brc location.
                text = scaled_text(data.brc, coord +
                                   (x_offset, (-height) / 2), height * 0.8)
                text["layer"] = transfer_label_brc
                drawing.add(text)

                # draw old transfer on the plot.

                if lookup_coord != coord:
                    transfer_layer = f"old_{side}_TRANSFER"

                    # ensure the layer has been added.
                    if not old_transfers_flag:
                        drawing.add_layer(transfer_layer, color=52)
                        old_transfers_flag = True

                    # add circle to indicate location
                    pin_circle = scaled_circle(probe_size, lookup_coord)
                    pin_circle["layer"] = transfer_layer
                    drawing.add(pin_circle)

                    text = scaled_text(
                        data.fix_id + "_OLD", lookup_coord + (x_offset, (-height) / 2), height)
                    text["layer"] = transfer_layer
                    drawing.add(text)

                    # add line to indicate its origin.
                    line = scaled_line(lookup_coord, coord)
                    line["layer"] = transfer_layer
                    drawing.add(line)

            elif type.endswith("mil"):
                if not probes_flag:

                    if side == "BOTTOM":
                        probe_colour = 1
                        label_colour = 12
                    else:
                        probe_colour = 6
                        label_colour = 200

                    drawing.add_layer(f"{side}_PROBES", color=probe_colour)
                    drawing.add_layer(
                        f"{side}_PROBES_LABEL", color=label_colour)
                        
                    layer_object = drawing.add_layer(
                        f"{side}_PROBES_B_R_C", color=label_colour)
                    layer_object.off()    
                        
                        
                    probes_flag = True

                probe_size_str = type.replace(" mil", "", 1)
                try:
                    probe_size = int(probe_size_str)
                except ValueError:
                    probe_size = 100

                pin_circle = scaled_circle(probe_size, coord)
                pin_circle["layer"] = f"{side}_PROBES"
                drawing.add(pin_circle)

                height = probe_size
                x_offset = height * 1.5
                text = scaled_text(data.fix_id, coord +
                                   (x_offset, (-height) / 2), height)
                text["layer"] = f"{side}_PROBES_LABEL"
                drawing.add(text)
                
                text = scaled_text(data.brc, coord +
                                   (x_offset, (-height) / 2), height * 0.8)
                text["layer"] = f"{side}_PROBES_B_R_C"
                drawing.add(text)

                if lookup_coord != coord:
                    # ensure the layer has been added.
                    if not old_probes_flag:
                        drawing.add_layer(f"old_{side}_PROBES", color=24)
                        old_probes_flag = True

                    # add circle to indicate location
                    pin_circle = scaled_circle(probe_size, lookup_coord)
                    pin_circle["layer"] = f"old_{side}_PROBES"
                    drawing.add(pin_circle)

                    text = scaled_text(
                        data.fix_id + "_OLD", lookup_coord + (x_offset, (-height) / 2), height)
                    text["layer"] = f"old_{side}_PROBES"
                    drawing.add(text)

                    # add line to indicate its origin.
                    line = scaled_line(lookup_coord, coord)
                    line["layer"] = f"old_{side}_PROBES"
                    drawing.add(line)
                    



def add_wire(inserts, from_xy, to_xy, side):

    if side == "TOP":
        flip = 1
    else:
        flip = 0

    from_insert = inserts[from_xy]
    to_insert = inserts[to_xy]

    from_coord = from_insert.coord
    to_coord = to_insert.coord

    # a pins y value is flipped,
    # as it is inserted from the
    # other side
    if from_insert._is_pin:
        from_flip = flip + 1
    else:
        from_flip = flip

    # a pins y value is flipped,
    # as it is inserted from the
    # other side
    if to_insert._is_pin:
        to_flip = flip + 1
    else:
        to_flip = flip

    from_coord = from_coord.flip_coord(from_flip)
    to_coord = to_coord.flip_coord(to_flip)

    return scaled_line(from_coord, to_coord)


def add_wires(drawing, fixture_settings, fixture_data, flags):
    """
    This function adds all of the wires in the fixture to the plot.
    """

    bottom_inserts, top_inserts = fixture_data._inserts

    bottom_wires, top_wires = fixture_data._wires

    # wire_colours = {"BLACK": 250,
    #                 "SKYBLUE": 4,
    #                 "BLUE": 5,
    #                 "RED": 10,
    #                 "GREEN": 92,
    #                 "LIGHTGREEN": 3,
    #                 "WHITE": 7,
    #                 "YELLOW": 2,
    #                 "PURPLE": 6,
    #                 "VIOLET": 6,
    #                 "PINK": 210,
    #                 "GRAY": 9,
    #                 "GREY": 9,
    #                 "DARKGRAY": 8,
    #                 "DARKGREY": 8,
    #                 "BROWN": 46,
    #                 "ORANGE": 30}

    wire_colours = {"BLACK":  250,
                    "BLUE": 5,
                    "RED": 10}

    loop_var = zip([bottom_wires, top_wires],
                   [bottom_inserts, top_inserts],
                   ["BOTTOM", "TOP"])

    for wires, inserts, side in loop_var:

        layer_flags = {"BLACK": (False, 250),
                       "BLUE": (False, 5),
                       "RED": (False, 10),
                       "CUSTOM": (False, 254)}

        for wire in wires:

            # skip terminal wires
            if wire._is_terminal_wire:
                continue

            from_xy, to_xy = wire._get_xy_coords

            colour = wire.wire_info.colour.upper()

            if wire.custom_wire:
                flag = "CUSTOM"
                line_colour = wire_colours.get(colour, 256)
            else:
                flag = colour
                line_colour = 256

            (layer_added, colour_index) = layer_flags.get(flag, layer_flags["CUSTOM"])

            layer_name = f"{side}_WIRES_{flag}"

            if not layer_added:
                if side == "TOP":
                    linetype = "CENTER"
                else:
                    linetype = "CONTINUOUS"

                drawing.add_layer(
                    layer_name, color=colour_index, linetype=linetype)
                layer_flags[flag] = (True, colour_index)

            line = add_wire(inserts, from_xy, to_xy, side)
            line["layer"] = layer_name
            line["color"] = line_colour

            drawing.add(line)


def generate_dxf_elements(f_output_path, fixture_settings, fixture_data, ground_inserts, flags):
    """
    This function will take the fixure data,
    and plot the contents of it.

    depending on the flags this plot will include:

    [bottom]
    interface pins (original & offset)

    soldered interface pins (original and offset)

    probes & transfer probes

    wires from interface pin to probes

    """

    drawing = dxf.drawing(f_output_path.as_posix())
    
    # remove default layers
    drawing.layers.clear()

    # add the fixture essentials ie outlines
    # tooling origin etc. Also adds pin locations and
    # names for (suspected) used tester cards.
    add_plot_essentials(drawing, fixture_settings, fixture_data, flags)

    # add the pins and ground pins of the fixture
    add_pins(drawing, fixture_settings, fixture_data, ground_inserts, flags)

    # add the probes when in
    if flags.output_plot:
        add_probes(drawing, fixture_settings, fixture_data, flags)
        add_wires(drawing, fixture_settings, fixture_data, flags)



    drawing.header['$CLAYER'] = "FIXTURE_OUTLINE"

    drawing.save()



def output_fixture_plot(output_dir,
                        plot_filename,
                        fixture_settings,
                        fixture_data,
                        generation_flags,
                        module_list,
                        flags):
    """
    This function ensures the
    output files can be written to
    before calling the functions to create
    the the ground list and plot.
    """

    if flags.fixture_gplane:
        gnd_inserts = output_ground_pins_list(fixture_data, flags)

        # create ground plane list in ground
        # plane mode.

        if generation_flags.gplane_plot:

            # define the output path.
            output_path = output_dir / "ground_brc_list.txt"

            try:
                f_output_path = output_path.open("w")

            except PermissionError:
                mb.showerror(
                    "Permission Error",
                    "    '{}' has been opened by another process.\n"
                    "    Close this file and try again.".format(file_name))
                return False
            else:

                brc_list = (gnd_ins.fix_id.brc for gnd_ins in gnd_inserts)

                if flags.throughput_multiplier:
                    f_output_path.write(\
                        "This fixture has throughput multiplier\n"\
                        "Ensure the ground plane is split along the modules.\n"\
                        "(Above row 13 on Bank 2, Below row 11 on Bank 1)\n")
                        
                else:
                    f_output_path.write(
                        "Please ensure the ground plane links all modules.\n")

                for brc in sorted(brc_list, key=op.attrgetter("bank", "row_and_half", "column")):

                    f_output_path.write("{0}\n".format(brc))

    else:
        gnd_inserts = []

    # define the output path.
    output_path = output_dir / plot_filename

    try:
        f_output_path = output_path.open("w")

    except PermissionError:
        mb.showerror(
            "Permission Error",
            "    '{}' has been opened by another process (Autocad?).\n"
            "    Close this file and try again.".format(plot_filename))
        return False

    else:
        f_output_path.close()
        generate_dxf_elements(
            output_path,
            fixture_settings,
            fixture_data,
            gnd_inserts,
            flags)

    return True

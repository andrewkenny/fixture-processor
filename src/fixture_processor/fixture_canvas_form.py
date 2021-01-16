"""
This module holds all of the code to
extract relevent data from the fixture file
and draw it to the turtle canvas
"""

import re
import turtle
from turtle import Vec2D

import tkinter as tk

from src.fixture_processor.fixture_functions import fixture_input as fi


class FixtureCanvas(tk.Frame):  # pylint: disable=too-many-ancestors
    """
    The frame showing the canvas of
    the fixture.
    """

    def __init__(self, window, master):
        if master:
            tk.Frame.__init__(self, master)

        # define local variables.
        self.offset_outlines = {}
        self.offset_tooling = {}
        self.board_center = {}
        self.panel_fixture = {}
        self.program_options = {}
        self.raw_fixture_data = tuple()

        self.window = window
        self.create_widgets()

    @property
    def canvas_width(self):
        "returns parent windows canvas width"
        return self.window.canvas_width

    @property
    def canvas_height(self):
        "returns parent windows canvas height"
        return self.window.canvas_height

    @property
    def fixture_path(self):
        "returns parent window fixture path"
        return self.window.fixture_path

    @property
    def width_ratio(self):
        "returns parent window width ratio"
        return self.window.width_ratio

    def create_widgets(self):
        """
        This method is called in __init__
        in order to fill this frame with widgets.
        """
        # create canvas for holding turtle screen
        self.cnv_plot = tk.Canvas(master=self, relief=tk.SUNKEN)
        self.cnv_plot["width"] = self.canvas_width
        self.cnv_plot["height"] = self.canvas_height
        self.cnv_plot.pack()

        # create turtle screen with which to place RawTurtle
        self.turtle_screen = turtle.TurtleScreen(self.cnv_plot)
        self.turtle_screen.bgcolor("#202020")
        self.turtle_screen.tracer(0)

        # place raw turtle.
        self.pen = turtle.RawTurtle(self.turtle_screen)
        self.pen.hideturtle()
        self.pen.speed(0)

    def get_program_options(self):
        "loads the program options from the uni file."
        self.program_options = self.window.get_program_options()

    def draw_fixture(self):
        """
        This method uses the alrady loaded raw_fixture_data,
        processes the dimensions so they will fit the canvas
        size, then draws them to the screen.
        """
        self.get_program_options()
        self.process_locations()
        self.update_plot()

    def load_fixture_and_draw(self):
        """
        This method parses the fixture file,
        and outputs the result on the canvas.
        """

        self.raw_fixture_data = fi.get_outline_info(self.fixture_path)
        self.draw_fixture()

    def process_locations(self):
        """
        This function scales all of the locations so that
        they fit into the given screen,
        Given that "border_ratio" < 1.
        boarder_ratio is adjusted to give a
        "zoom in" and a "zoom out" affect.

        seek_offset provides a method to "move" L, R, U, D
        """

        outlines, tooling = self.raw_fixture_data

        self.offset_outlines = {}
        self.offset_tooling = {}

        self.board_center = {}
        board_center = {}

        self.panel_fixture = False

        plot_options = self.program_options["Plot_Options"]
        plot_filters = self.program_options["Plot_Filters"]

        plot_scale = plot_options["plot_scale"]

        manual_offset_x = plot_options["manual_offset_x"]
        manual_offset_y = plot_options["manual_offset_y"]

        show_panel_outline = plot_filters["show_panel_outline"]
        show_panel_tooling = plot_filters["show_panel_tooling"]
        show_board_tooling = plot_filters["show_board_tooling"]

        manual_offset = Vec2D(manual_offset_x, manual_offset_y)

        # create a list of all locations
        # to allow for min max calculatations.
        x_list = []
        y_list = []

        for name, locations in outlines.items():

            if name.startswith("P_"):
                self.panel_fixture = True

            all_x, all_y = zip(*locations)

            max_x = max(all_x)
            min_x = min(all_x)
            max_y = max(all_y)
            min_y = min(all_y)

            x_list.extend([max_x, min_x])
            y_list.extend([max_y, min_y])

            if name.startswith("B_"):
                mean_x = (max_x + min_x) / 2
                mean_y = (max_y + min_y) / 2
                board_center[name] = Vec2D(mean_x, mean_y)

        max_x = max(x_list)
        min_x = min(x_list)
        max_y = max(y_list)
        min_y = min(y_list)

        # calculate the mean X and mean Y
        # which is also the center locations.
        mean_x = (max_x + min_x) / 2
        mean_y = (max_y + min_y) / 2

        # the midpoint will be extracted
        # from every location in centralise the plot.
        center_offset = Vec2D(mean_x, mean_y)

        # is the X or the Y largest?
        x_dim = max_x - mean_x
        y_dim = max_y - mean_y

        dim_ratio = x_dim / y_dim

        if dim_ratio > self.width_ratio:
            max_dim = x_dim
            outline_edge = (self.canvas_width / 2) * plot_scale
        else:
            outline_edge = (self.canvas_height / 2) * plot_scale
            max_dim = y_dim

        max_dim = max(max_x - mean_x, max_y - mean_y)

        # what should coordinates be multiplied by
        # in order to nicely fill the allotted area?
        multiplier = outline_edge / max_dim

        def fit_to_canvas(loc):
            return ((loc - center_offset) * multiplier) + manual_offset

        for name, locations in outlines.items():

            if name.startswith("P_") and not show_panel_outline:
                continue

            new_locations = [fit_to_canvas(loc)
                             for loc in locations]

            self.offset_outlines[name] = new_locations

        for name, tooling_pins in tooling.items():

            if name.startswith("P_") and not show_panel_tooling:
                continue

            if name.startswith("B_") and not show_board_tooling:
                continue

            new_tools = []

            for location, width in tooling_pins:

                new_width = int(width / 4) * multiplier
                new_location = ((location - center_offset)
                                * multiplier) + manual_offset

                new_tools.append((new_width, new_location))

            self.offset_tooling[name] = new_tools

        # process the board center information
        for name, location in board_center.items():
            self.board_center[name] = (
                (location - center_offset) * multiplier) + manual_offset

    def update_plot(self):
        """
        This function draws the outlines and the tooling
        of the provided boards.

        Additionally overlays the board numbers
        to allow engineers to understand the layout.
        """

        plot_colours = self.program_options["Plot_Colours"]

        background_colour = plot_colours["background_colour"]
        panel_outline_colour = plot_colours["panel_outline_colour"]
        board_outline_colour = plot_colours["board_outline_colour"]

        panel_tooling_colour = plot_colours["panel_tooling_colour"]
        board_tooling_colour = plot_colours["board_tooling_colour"]

        text_colour = plot_colours["text_colour"]

        outlines, tooling = self.offset_outlines, self.offset_tooling

        self.turtle_screen.bgcolor(background_colour)

        self.pen.clear()

        self.pen.hideturtle()
        self.pen.speed(0)

        for name, locations in outlines.items():

            # skip blank locations.
            # to account for dummy boards
            if not locations:
                continue

            if name.startswith("P_"):
                self.pen.pencolor(panel_outline_colour)
            else:
                self.pen.pencolor(board_outline_colour)

            initial_location = locations[0]

            # send the pin to the starting location.
            self.pen.penup()
            self.pen.goto(initial_location)
            self.pen.pendown()

            # draw the outline lines.
            for loc in locations:
                self.pen.goto(loc)

            # ensure the pen goes to the initial point
            # (to ensure the box is complete & without gaps
            self.pen.goto(initial_location)

            # lift pen, to move onto the next outline.
            self.pen.penup()

        # add the tooling holes.
        for name, locations in tooling.items():

            if name.startswith("P_"):
                self.pen.pencolor(panel_tooling_colour)
                self.pen.fillcolor(panel_tooling_colour)
            else:
                self.pen.pencolor(board_tooling_colour)
                self.pen.fillcolor(board_tooling_colour)

            for width, location in locations:
                self.pen.goto(location)
                self.pen.pendown()
                self.pen.begin_fill()
                self.pen.circle(width)
                self.pen.end_fill()
                self.pen.penup()

        # add the board numbers where relevent.
        all_names = outlines.keys()
        board_outline_names = [name for name in
                               list(all_names)
                               if name.startswith("B_")]

        self.pen.pencolor(text_colour)
        if self.panel_fixture:

            for name in board_outline_names:

                board_number = str(re.split(r"[:%]", name)[-1])

                font = ("Arial", 15, "normal")
                text_centre = self.board_center[name]

                text_x_offset = -5*len(board_number)

                self.pen.goto(text_centre + Vec2D(text_x_offset, -12))
                self.pen.pendown()
                self.pen.write(board_number, font=font)
                self.pen.penup()

        self.turtle_screen.update()

"""
option_form.py contains all the code used to
create the options form.
"""

import tkinter as tk
from tkinter import messagebox as mb
from collections import namedtuple


from pathlib import Path

from fixture_processor.options_lib import fixture_processing_options

from fixture_processor.options_lib import fp_option_functions as fp_options

from fixture_processor.options_lib.options_functions import OptionsForm
from fixture_processor.options_lib.fixture_processing_options import WIDGET_LIST

from fixture_processor import file_operations as fo
from fixture_processor.fixture_functions import fixture_modifications as fm
from fixture_processor.fixture_functions import extract_wires as ew

from typing import NamedTuple


USER_OPTIONS_FILE = "user_options.ini"


class GenerationTuple(NamedTuple):
    processing: bool
    gplane_plot: bool
    wires_plot: bool


class WidgetDict(dict):

    @property
    def encode_settings(self):

        extra_variables = fixture_processing_options.EXTRA_VARIABLES

        field_names = list(self) + list(extra_variables)

        encode_tuple = namedtuple("processing_options", field_names)

        variable_data = {name: widget.variable.get()
                         for name, widget in self.items()}

        return encode_tuple(**variable_data, **extra_variables)


class FixtureProcessingForm(OptionsForm):
    """
    This class will contain all of the code related to
    the user selecting options and running commands.
    """

    def __init__(self, engineering_flag, window, master=None):

        # ensure the master / root is applied properly.
        if master:
            tk.Frame.__init__(self, master)

        self.window = window
        self.engineering_flag = engineering_flag

        # add the user config buttons
        self.open_remove_wires_config = lambda: self.create_and_open_file(
            "remove_wires.csv",
            fm.get_wire_removal_instructions())

        self.open_modify_inserts_config = lambda: self.create_and_open_file(
            "modify_inserts.csv",
            fm.get_inserts_modifier_instructions())

        self.open_add_wires_config = lambda: self.create_and_open_file(
            "add_wires.csv",
            fm.get_wire_addition_instructions())

        # keep a list of checkboxes, which can be disabled
        # when required.
        self.user_data_widgets = WidgetDict()

        self.form_widgets = WIDGET_LIST
        self.ini_filename = USER_OPTIONS_FILE

        self.add_widgets()

        self.options_functions = fp_options

    @property
    def fixture_path(self):
        return self.window.fixture_path

    def create_and_open_file(self, filename: str,
                             stub_text: str = None):
        """
        This function takes a filename, and some
        initial stub text.

        if the file doesn't exist, this program creates it,
        and fills it with stub text.

        fo.open_file_for_editing is called next to allow
        the operator to edit the contents.
        """

        file_path: Path = self.fixture_path / filename

        fo.create_file_stub(file_path, stub_text)
        fo.open_file_for_editing(file_path)

    def open_folder(self):
        fo.open_folder(self.fixture_path)

    def clean_targets(self):

        if ew.clean_targets(self.fixture_path):
            mb.showinfo("cleanup complete",
                        "    Target output files removed successfully.")

    def process_wi(self):

        processing_options = self.user_data_widgets.encode_settings

        generation_flags = GenerationTuple(processing=True,
                                           gplane_plot=False,
                                           wires_plot=False)

        ew.process_fixture_info(self.fixture_path, processing_options,
                                generation_flags)

    def generate_gplane_data(self):
        """
        """

        processing_options = self.user_data_widgets.encode_settings

        generation_flags = GenerationTuple(processing=False,
                                           gplane_plot=True,
                                           wires_plot=False)

        ew.process_fixture_info(self.fixture_path, processing_options,
                                generation_flags)

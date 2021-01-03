"""
This script holds all of the code for loading and storing the settings.

the settings will be stored as an ini within the '%APPDATA%/forwessun_fp' folder

The current settings will be:

    [Fixture_Corrections]
    remove_terminal_wires # look for job folder or look for fixture.o?
    remove_testjet_transfer_wires  # the default folder for above dialog box to open in.
    correct_offset_pins            # 


    [Ground_Plane_Options]
    ground_plane_enabled
    include_ASRU_gnd
    reserve_module_gnd


    [Wire_Removal_Options]
    remove_user_defined_wires     # look for a while which defines wires to be removed.
    ignore_missing_wires          # if true a missing wire does not produce an error (but is noted is the log)




"""

from collections import namedtuple, OrderedDict
from pathlib import Path
from string import hexdigits
from dataclasses import dataclass
from typing import Optional, List

from fixture_processor.options_lib.options_functions import Optiontuple, get_sections
from fixture_processor.options_lib import options_functions as of


OPTIONS_COLLECTION = []

# define the fixture correction options, along with the
# checkbox text.
FIXTURE_CORRECTIONS_OPTIONS = \
    {"name": "fixture_corrections",
     "label": "Fixture Corrections",
     "comment": "Removes / corrects problematic and unnecessary wires.",
     "position": of.FormPosition(column=1, row=1),
     "hidden": False,
     "resolve_terminals": of.CheckbuttonData("Resolve terminal wires", False, disabled=None),
     "remove_terminal_wires": of.CheckbuttonData("Remove terminal wires", True),
     "remove_tj_transfers": of.CheckbuttonData("Remove testjet transfer wires", True),
     "pin_offset_fix": of.CheckbuttonData("Correct offset pins (verifier only)", True),
     "reserve_hybrid": of.CheckbuttonData("Reserve hybrid ground for VTEP", False, disabled=None, dependants=["hybrid_location"]),
     "hybrid_location": of.EntryTextData("VTEP ground location",
                                         default="TopLeft", disabled=True, hidden=True, width=15)
     }
OPTIONS_COLLECTION.append(FIXTURE_CORRECTIONS_OPTIONS)

FIXTURE_GROUND_PLANE_OPTIONS = \
    {"name": "ground_plane_options",
     "label": "Ground Plane Options",
     "comment": "Removes unnessary wires in fixtures with ground plane",
     "position": of.FormPosition(column=1, row=2),
     "hidden": False,
     "fixture_gplane": of.CheckbuttonData("This fixture has ground plane", False, False, dependants=["gplane_include_asru", "cmd_gplane_plot"]),
     "gplane_include_asru": of.CheckbuttonData("Include ASRU SWGND in ground plane?", True, disabled=True),\
     # "gplane_include_rcvc": of.CheckbuttonData("Include RCVC GND in ground plane?", False, None),\
     "cmd_gplane_plot": of.CmdbuttonData("Output Ground\nBRCs Plot & List", True, "generate_gplane_data")}
OPTIONS_COLLECTION.append(FIXTURE_GROUND_PLANE_OPTIONS)

wire_removal_filename = "remove_wires.csv"
WIRE_REMOVAL_OPTIONS = \
    {"name": "wire_removal_options",
     "label": "Wire Removal Options",
     "comment": "Allows the user to describe wires to be removed.",
     "filename": wire_removal_filename,
     "position": of.FormPosition(column=2, row=2),
     "hidden": False,
     "remove_custom_wires": of.CheckbuttonData("Remove user defined wires", False, False, dependants=["ignore_missing_wires", "cmd_open_remove_csv"]),
     "ignore_missing_wires": of.CheckbuttonData("Ignore missing wires", False, hidden=True),
     "cmd_open_remove_csv": of.CmdbuttonData(f"Open '{wire_removal_filename}'\nfor editing", True, "open_remove_wires_config")}
OPTIONS_COLLECTION.append(WIRE_REMOVAL_OPTIONS)

inserts_modifier_filename = "modify_inserts.csv"
INSERTS_MODIFIER_OPTIONS = \
    {"name": "inserts_modifier_options",
     "label": "Inserts Modifier Options",
     "comment": "Allows the user to add inserts, and offset some inserts.",
     "filename": inserts_modifier_filename,
     "position": of.FormPosition(column=2, row=1),
     "hidden": False,
     "modify_inserts": of.CheckbuttonData("Modify user defined inserts", False, False, dependants=["ignore_missing_inserts", "cmd_open_modify_csv"]),
     "ignore_missing_inserts": of.CheckbuttonData("Ignore missing inserts", False, disabled=None, hidden=True),
     "pin2_offset": of.EntryTextData("TJ Mux Pin 2 Offset (⅒ mils): ",
                                         default="(1000, 0)", disabled=True, hidden=False, width=8),
     "pin6_offset": of.EntryTextData("TJ Mux Pin 6 Offset (⅒ mils): ",
                                         default="(0, 1000)", disabled=True, hidden=False, width=8),
     "block_offset": of.EntryTextData("Transfer Block Offset (⅒ mils): ",
                                         default="1000", disabled=True, hidden=False, width=5),
     "cmd_open_modify_csv": of.CmdbuttonData(f"Open '{inserts_modifier_filename}'\nfor editing", True, "open_modify_inserts_config")}
OPTIONS_COLLECTION.append(INSERTS_MODIFIER_OPTIONS)

new_wire_filename = "add_wires.csv"
NEW_WIRE_OPTIONS = \
    {"name": "new_wire_options",
     "label": "New Wire Options",
     "comment": "Allows the user to describe wires new wires (between already existing inserts).",
     "filename": new_wire_filename,
     "position": of.FormPosition(column=2, row=3),
     "hidden": False,
     "add_custom_wires": of.CheckbuttonData("Add user defined wires", False, False, dependants=["ignore_missing_custom_inserts", "cmd_open_add_csv"]),
     "ignore_missing_custom_inserts": of.CheckbuttonData("Ignore missing custom inserts", False, disabled=None, hidden=True),
     "cmd_open_add_csv": of.CmdbuttonData(f"Open '{new_wire_filename}'\nfor editing", True, "open_add_wires_config")}
OPTIONS_COLLECTION.append(NEW_WIRE_OPTIONS)

ENGINEERING_OPTIONS = \
    {"name": "engineering_options",
     "label": "Engineering Options",
     "comment": "Advanced options for Engineers only.",
     "position": of.FormPosition(column=3, row=2),
     "hidden": True,
     "disable_checkboxes": of.CheckbuttonData("Disable checkboxes on next load.", False),
     "log_level": of.EntryTextData("Log Level: ", default="INFO", hidden=True, width=10),
     "cmd_save_options_csv": of.CmdbuttonData("Save User Options", False, "set_user_options")}
OPTIONS_COLLECTION.append(ENGINEERING_OPTIONS)

PROCESS_OPTIONS = \
    {"name": "processing_options",
     "label": "Processing Options",
     "comment": "Trigger wires and inserts processing. Select targets",
     "position": of.FormPosition(column=3, row=3),
     "hidden": False,
     "wiring_machine": of.CheckbuttonData("Enable wiring machine target", True),
     "verifier": of.CheckbuttonData("Enable verifier target", True),
     "verifier_top": of.CheckbuttonData("Enable Verifier top plate target", False, disabled=None, hidden=True),
     "output_plot": of.CheckbuttonData("Output fixture .dxf", False),
     "cmd_process_wires_inserts": of.CmdbuttonData("Process Wires & Inserts", False, "process_wi")}
OPTIONS_COLLECTION.append(PROCESS_OPTIONS)

WIDGET_LIST = OPTIONS_COLLECTION.copy()

FIXTURE_TARGETS = [key for key,
                   data in PROCESS_OPTIONS.items() if of.is_checkbutton(data)]


# The following options are only describing a set of helper commands.

HELPER_COMMANDS = \
    {"name": "Admin_Options",
     "label": "Helper Commands",
     "comment": "Contains a set of useful functions.",
     "position": of.FormPosition(column=3, row=1),
     "hidden": False,
     "cmd_open_fixture_folder": of.CmdbuttonData("Open job fixture folder", False, "open_folder"),
     "cmd_clean_fixture_output": of.CmdbuttonData("Clean job fixture targets", False, "clean_targets"),
     "cmd_view_prog_log": of.CmdbuttonData("View Program Log", None, None)}

WIDGET_LIST.append(HELPER_COMMANDS)

# These variables are calculated during processing
# and are not user selectable.
EXTRA_VARIABLES = {
    'throughput_multiplier': False
}


# todo - Modifiy the get section comments to it uses the
# option dictionary data above.
def get_section_comments():

    section_comments = OrderedDict()

    for option in OPTIONS_COLLECTION:
        name = option["name"]
        comment = option["comment"]
        section_comments[name] = comment

    return section_comments


"""
the option tuple will contain information about each option included
in the ini file.

it is used to create the initial default settings.

    name       - name of option
    section    - which of the above sections does it belong in.
    default    - what is the default value of this option.
    get_method - used for getfloat, getint, getboolean etc
    validation - contains None or a validation function,
                 if None, no validation is performed.
                 if the validation fails, the default value is used.
    comment    - if not None, the text is inserted above the option line in
                 the ini file. (comments are recomended to be placed above the section
                 option.
"""


def add_options(option_list, section_name, option_data):
    """
    Adds the pre-defined option data to the 
    option_list to be used to generate
    ini files.
    """

    option_list[section_name] = []

    for name, data in option_data.items():
        if not of.is_config_data(data):
            continue

        default = data.default
        get_method = data.get_method
        comment = data.comment

        option_list[section_name].append(
            Optiontuple(
                name,
                default,
                get_method,
                lambda option_text: True,
                default))


def get_options():
    option_list = OrderedDict()

    for option in OPTIONS_COLLECTION:
        name = option["name"]
        add_options(option_list, name, option)

    return option_list

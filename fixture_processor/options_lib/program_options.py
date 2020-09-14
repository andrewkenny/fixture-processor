"""
This script holds all of the code for loading and storing the settings.

the settings will be stored as an ini within the '%APPDATA%/forwessun_fp' folder

The current settings will be:

    [Dialog_Options]
    job open method # look for job folder or look for fixture.o?
    default folder  # the default folder for above dialog box to open in.

    [Plot_Colours]
    background colour
    panel_outline_colour
    panel_tooling_colour
    board_outline_colour
    board_tooling_colour
    text colour

    [Plot_Options]
    border_ratio
    tooling_shape
    text_size
    line_width

    [Plot_Filters]
    show_panel_outline    # useful if panel outline is much bigger than board.
    show_panel_tooling    # useful if the tooling is blocking something else
    show_board_tooling    # useful if the tooling is blocking something else


"""

from collections import namedtuple, OrderedDict
from pathlib import Path
from string import hexdigits

from .options_functions import Optiontuple, get_sections


def get_section_comments():

    section_comments = OrderedDict()

    name = "Dialog_Options"
    comment = "Settings which control how jobs are opened."
    section_comments[name] = comment

    name = "Plot_Colours"
    comment = "Settings which control the colour of the plot."
    section_comments[name] = comment

    name = "Plot_Options"
    comment = "Settings which control various features of the plot"
    section_comments[name] = comment

    name = "Plot_Filters"
    comment = "Settings which filter elements on the plot."
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


def get_options():
    option_list = get_sections(get_section_comments().keys())

    name = "default_folder"
    section = "Dialog_Options"
    default = "c:"
    get_method = None
    def df_validation(option_text):

        test_path = Path(option_text)
        return test_path.is_dir()
    comment = None
    option_list[section].append(
        Optiontuple(
            name,
            default,
            get_method,
            df_validation,
            comment))

    ##########################################################################

    def colour_validation(option_text):

        hash_flag = option_text.startswith('#')
        length_flag = len(option_text) == 7
        hex_flag = all(c in hexdigits for c in option_text[1:])

        return hash_flag and length_flag and hex_flag

    name = "background_colour"
    section = "Plot_Colours"
    default = "#202020"    # very dark grey
    get_method = None
    comment = None
    option_list[section].append(
        Optiontuple(
            name,
            default,
            get_method,
            colour_validation,
            comment))

    name = "panel_outline_colour"
    section = "Plot_Colours"
    # default = "#FFFFE0"  # lightyellow
    default = "#EEE8AA"    # palegoldenrod
    # default = "# 999900" # dark yellow 2
    get_method = None
    comment = None
    option_list[section].append(
        Optiontuple(
            name,
            default,
            get_method,
            colour_validation,
            comment))

    name = "panel_tooling_colour"
    section = "Plot_Colours"
    # default = "#FFFFE0"  # lightyellow
    default = "#EEE8AA"    # palegoldenrod
    # default = "# 999900" # dark yellow 2
    get_method = None
    comment = None
    option_list[section].append(
        Optiontuple(
            name,
            default,
            get_method,
            colour_validation,
            comment))

    name = "board_outline_colour"
    section = "Plot_Colours"
    # default = "#FFFFE0"  # lightyellow
    default = "#EEE8AA"    # palegoldenrod
    # default = "# 999900" # dark yellow 2
    get_method = None
    comment = None
    option_list[section].append(
        Optiontuple(
            name,
            default,
            get_method,
            colour_validation,
            comment))

    name = "board_tooling_colour"
    section = "Plot_Colours"
    # default = "#FFFFE0"  # lightyellow
    default = "#EEE8AA"    # palegoldenrod
    # default = "# 999900" # dark yellow 2
    get_method = None
    comment = None
    option_list[section].append(
        Optiontuple(
            name,
            default,
            get_method,
            colour_validation,
            comment))

    name = "text_colour"
    section = "Plot_Colours"
    default = "#EE82EE"  # violet
    get_method = None
    comment = None
    option_list[section].append(
        Optiontuple(
            name,
            default,
            get_method,
            colour_validation,
            comment))

    ##########################################################################

    name = "plot_scale"
    section = "Plot_Options"
    default = 0.95
    get_method = "getfloat"
    bd_validation = None
    comment = None
    option_list[section].append(
        Optiontuple(
            name,
            default,
            get_method,
            bd_validation,
            comment))

    name = "manual_offset_x"
    section = "Plot_Options"
    default = 0
    get_method = "getint"
    mox_validation = None
    comment = None
    option_list[section].append(
        Optiontuple(
            name,
            default,
            get_method,
            mox_validation,
            comment))

    name = "manual_offset_y"
    section = "Plot_Options"
    default = 0
    get_method = "getint"
    moy_validation = None
    comment = None
    option_list[section].append(
        Optiontuple(
            name,
            default,
            get_method,
            moy_validation,
            comment))

    name = "tooling_shape"
    section = "Plot_Options"
    default = "circle"
    get_method = None

    def tshape_validation(option_text):
        return option_text in ["circle", "cross", "both"]

    comment = None
    option_list[section].append(
        Optiontuple(
            name,
            default,
            get_method,
            tshape_validation,
            comment))

    name = "text_size"
    section = "Plot_Options"
    default = 15
    get_method = "getint"
    def textsize_validation(option_int):

        return option_int in range(10, 21)

    comment = None
    option_list[section].append(
        Optiontuple(
            name,
            default,
            get_method,
            textsize_validation,
            comment))

    name = "line_width"
    section = "Plot_Options"
    default = 1
    get_method = "getint"
    def lw_validation(option_int):

        return option_int in range(1, 6)

    comment = None
    option_list[section].append(
        Optiontuple(
            name,
            default,
            get_method,
            lw_validation,
            comment))

    ##########################################################################

    name = "show_panel_outline"
    section = "Plot_Filters"
    default = True
    get_method = "getboolean"
    validation = None

    comment = None
    option_list[section].append(
        Optiontuple(
            name,
            default,
            get_method,
            validation,
            comment))

    name = "show_panel_tooling"
    section = "Plot_Filters"
    default = True
    get_method = "getboolean"
    validation = None

    comment = None
    option_list[section].append(
        Optiontuple(
            name,
            default,
            get_method,
            validation,
            comment))

    name = "show_board_tooling"
    section = "Plot_Filters"
    default = True
    get_method = "getboolean"
    validation = None

    comment = None
    option_list[section].append(
        Optiontuple(
            name,
            default,
            get_method,
            validation,
            comment))

    return option_list

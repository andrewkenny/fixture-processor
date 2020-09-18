"""

This file is intended to perform 2 actions.

1, load the options from a given file path.

   if the options file does not exist, create an options
   file with the default values.

   then load the newly created options file.

2, save the users options to an options file.
   note that the sections and the individual options
   have comments.

"""
import configparser
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional, List, NamedTuple, Callable, Any
from contextlib import contextmanager


import tkinter as tk


class Optiontuple(NamedTuple):
    name: str
    default: Any
    get_method: str
    validation: Callable[[str], bool]
    comment: str


# These dataclasses are used to generate options
# and auto fill GUI forms.

class FormPosition(NamedTuple):
    column: int
    row: int


@dataclass
class CheckbuttonData:
    description: str         # the text to the right of the checkbutton
    default: bool            # The default state of the checkbox

    # If True the checkbox is never rendered, unless the engineering flag is set.
    hidden: bool = False
    # Is the checkbutton disabled to begin with (None means always disabled / RFU)
    disabled: Optional[bool] = False

    # does this checkbutton enable other widgets when checked?
    dependants: Optional[List[str]] = None

    # describes the checkbuttons purpose is more detail, may be used when tooltips are incorporated.
    comment: str = ""

    @property
    def get_method(self):
        return "getboolean"


@dataclass
class EntryTextData:
    description: str          # The text to the left of the entry box
    default: str = ""           # The default value of the entry box.
    # if True if the entry box is never rendered, unless the engineering flag is set.
    hidden: bool = False

    # Is the checkbutton disabled to begin with (None means always disabled / RFU)
    disabled: Optional[bool] = False

    width: int = 20

    # describes the entryboxes purpose in more detail, may be use when tooltips are incorporated.
    comment: str = ""

    @property
    def get_method(self):
        return "get"


@dataclass
class CmdbuttonData:
    description: str          # the text on the command button.
    # Is the command button disabled to begin with (None means always disabled / RFU)
    disabled: Optional[bool]
    # The name of the method called when the button is pushed.
    command: Optional[str]
    # Describes the buttons purpose in more detail, may be used when tooltips are incorporated.
    comment: str = ""


def is_checkbutton(data):

    return isinstance(data, CheckbuttonData)


def is_entrybox(data):

    return isinstance(data, EntryTextData)


def is_config_data(data):

    return is_checkbutton(data) or is_entrybox(data)


def is_cmdbutton(data):

    return isinstance(data, CmdbuttonData)


# create an ordered dict, with a key for each section name.
# fill the ordered dict with blank lists. to be filled
# by options.
def get_sections(sections_names_list):

    sections = OrderedDict()

    for section in sections_names_list:
        sections[section] = []

    return sections


"""
This function is intended to simplify the "get" code.

If the option lookup fails, the default data is returned.

if a getboolean / getfloat / getint method is specified,
but fails, the default data is returned.

If a validation function is declared, and fails, the default
data is returned.

"""


def get_data(config_section, option):

    name = option.name
    default = option.default
    get_method = option.get_method
    validation = option.validation

    if get_method is None:
        get_method = "get"

    try:
        # use the relevent lookup method to obtain the data.
        config_data = getattr(config_section, get_method)(name, default)
    except ValueError:
        return default

    # no validation means that the data is returned as is
    if validation is None:
        return config_data

    # a validation fail means the default data is returned.
    validated = validation(config_data)

    if validated:
        return config_data
    else:
        return default


"""
This function is actually a function generator.

Arguments:
    section_comments_dict: a dictionary split into sections
                           each section has a comment uses to describe
                           the section

    options_dict: a dictionary split into sections.
                  each sections contains an options list.

it returns:
    a function which will save these options to a given file handle

    a function which will load these optiosn from a given file handle.


"""


def generate_option_functions(section_comments_dict, options_dict):

    class ReturnTuple(NamedTuple):
        save: Callable
        load: Callable

    """
    This function will save the provided "user_options"
    to a config_parser ini file.

    if an option from the options_list is not included in the
    "user_options" dict, or if the "user_options" argument is None,
    then a default value is used.


    """
    def save_options(user_options, file_handle):

        if user_options is None or user_options == {}:
            user_options = OrderedDict()

        config = configparser.ConfigParser()

        for section, options in options_dict.items():

            # create a new section, (ordered for compatability)
            # The section with be filled with relevent options.
            config[section] = OrderedDict()

            # get the users options.
            user_section = user_options.get(section, {})

            for option in options:

                option_name = option.name
                option_default = option.default

                # look up the option value in the user section, falling back
                # on the default, if it cannot be found.
                option_value = user_section.get(
                    option_name, str(option_default))

                config[section][option_name] = option_value

        config.write(file_handle)

    """
    This function loads the user_options from
    the file described by "file_handle"

    If an item in the config is missing (from the options_list)
    then a default value is assigned.
    """
    def load_options(file_handle=None):

        user_options = OrderedDict()

        config = configparser.ConfigParser()

        if file_handle is not None:
            config.read_file(file_handle)

        for section, options in options_dict.items():

            # create a new section, (ordered for compatability)
            # The section with be filled with relevent options.
            user_options[section] = OrderedDict()

            # get the config options
            if section in config.sections():
                config_section = config[section]
            else:
                config[section] = {}
                config_section = config[section]

            for option in options:
                option_name = option.name

                # look up the option value in the loaded config, falling back
                # on the default, if it cannot be found.
                option_value = get_data(config_section, option)

                user_options[section][option_name] = option_value

        return user_options

    return ReturnTuple(save_options, load_options)


class OptionsForm(tk.Frame):

    @staticmethod
    def on_update(self):
        """
        when a checkbox has dependents,
        the dependants are disabled when
        the checkbox is not selected.
        """

        # no dependants means do not run code.
        dependants = self.data.dependants
        if not dependants:
            return

        enabled_flag = self.variable.get()

        variable_widget_lookup = self.master.variable_dict

        # disable or enable the dependant checkbox.
        for dependant_name in dependants:

            # get the variable.
            if dependant_name in variable_widget_lookup:
                tk_object = variable_widget_lookup[dependant_name]

            else:
                tk_object = getattr(self.master, dependant_name)

            try:
                dependant_variable = tk_object.variable
            except AttributeError:
                dependant_variable = None

            # should this checkbox stay disabled?
            if tk_object.data.disabled is None:
                continue

            # if the box is ticked, enable the checkbox.
            # if the box is not ticked, disable the checkbox
            # and clear the flags.

            if enabled_flag:
                tk_object["state"] = tk.NORMAL
                tk_object.backup_state = tk.NORMAL

                # skip tkinter objects which
                # don't have associated variables
                # or when
                # the state is being updated
                # by the options_loader
                if dependant_variable is None or self.options_load:
                    continue

                # check the checkbox is the default is "True"
                default_value = tk_object.data.default
                if default_value is True:
                    tk_object.select()

                if isinstance(default_value, str):
                    tk_object.delete(0, tk.END)
                    tk_object.insert(0, default_value)

            else:

                if isinstance(dependant_variable, tk.BooleanVar):
                    tk_object.deselect()

                if isinstance(dependant_variable, tk.StringVar):
                    tk_object.delete(0, tk.END)

                tk_object["state"] = tk.DISABLED
                tk_object.backup_state = tk.DISABLED

    def disable_checkbuttons(self):
        """
        This function is intended to prevent tampering
        by disabling checkboxes.
        """

        disable_checkboxes = self.disable_checkboxes.get()

        # if the flag is true, disable the checkboxes.
        if disable_checkboxes and not self.engineering_flag:
            for var_name, form_widget in self.user_data_widgets.items():

                form_widget["state"] = tk.DISABLED

        # re-enable relevent checkboxes
        elif not disable_checkboxes or self.engineering_flag:

            for var_name, form_widget in self.user_data_widgets.items():

                form_widget["state"] = form_widget.backup_state

    def add_checkbutton(self, parent_frame, row, name, data):
        """
        given a parent frame, a name and a predefined
        set of data, insert a button onto the parent frame.

        return the number of rows the button used (normally one)
        """

        # create a boolean variable, and assign it to the
        # processor options frame.
        bool_variable = tk.BooleanVar()
        setattr(self, name, bool_variable)

        # is the button disabled / RFU?
        if data.disabled in [True, None]:
            checkbutton_state = tk.DISABLED
        else:
            checkbutton_state = tk.NORMAL
            bool_variable.set(data.default)

        # create the checkbutton.
        checkbutton_name = "chk_" + name
        checkbutton = tk.Checkbutton(parent_frame,
                                     variable=bool_variable,
                                     text=data.description,
                                     state=checkbutton_state)

        checkbutton.data = data
        checkbutton.variable = bool_variable
        checkbutton.backup_state = checkbutton_state
        checkbutton["command"] = lambda: self.on_update(checkbutton)

        # add a flag which is True when the checkbuttons are
        # being updated by the loading the ini options.
        checkbutton.options_load = False

        # add the checkbutton name to the variable_dict
        # with the variable name as a key.
        parent_frame.variable_dict[name] = checkbutton
        self.user_data_widgets[name] = checkbutton

        setattr(parent_frame, checkbutton_name, checkbutton)

        # do not render checkbox if it is required to be hidden.
        if data.hidden and not self.engineering_flag:
            return 0

        checkbutton.grid(row=row, column=1, sticky=tk.W, padx=[5, 0])
        return 1

    def add_entrybox(self, parent_frame, row, name, data):
        """
        given a parent frame, a name and a predefined set of data,

        either:
            - insert a container frame (to allow for a column width of 1)
              containing a label and an entry side by side.
        or:
            - insert a label and an entry box below.   


        then within that frame create a:
        label: entrybox.
        return the number of rows used.
        """

        str_variable = tk.StringVar()
        setattr(self, name, str_variable)

        # is the entry box disabled / RFU?
        if data.disabled in [True, None]:
            str_variable.set(data.default)
            entry_state = tk.DISABLED
        else:
            entry_state = tk.NORMAL
            str_variable.set(data.default)

        # create a container frame.
        frame_name = "frm_" + name
        self.frame_name = tk.Frame(parent_frame)

        # create the label decribing the textbox.
        label_name = "lbl_" + name
        label = tk.Label(self.frame_name, text=data.description)

        # create the entry box.
        entry_name = "txt_" + name

        entrybox = tk.Entry(self.frame_name,
                            textvariable=str_variable,
                            width=data.width + 2,
                            state=entry_state)

        # assign variables.
        entrybox.data = data
        entrybox.variable = str_variable
        entrybox.backup_state = entry_state

        # add a flag which is True when the textbox is
        # being updated by the loading the ini options.
        entrybox.options_load = False

        # add the entry name to the variable_dict
        # with the variable name as a key.
        parent_frame.variable_dict[name] = entrybox
        self.user_data_widgets[name] = entrybox

        setattr(parent_frame, entry_name, entrybox)

        # do not render checkbox if it is required to be hidden.
        if data.hidden and not self.engineering_flag:
            return 0

        self.frame_name.columnconfigure(1, weight=1)
        self.frame_name.grid(
            row=row, column=1, sticky=tk.W + tk.E, pady=[0, 5], padx=5)
        label.grid(row=1, column=1, sticky=tk.W)
        entrybox.grid(row=1, column=2, sticky=tk.E, padx=[0, 5])

        return 1

    def add_button(self, parent_frame, row, name, data):
        """
        given a parent frame, a name and a predefined
        set of data, insert a button onto the parent frame.

        return the number of rows the button used (normally one)
        """

        # is the button disabled / RFU?
        if data.disabled in [True, None]:
            button_state = tk.DISABLED
        else:
            button_state = tk.NORMAL

        # if the command property is a string,
        # it refers to an attribute of self.
        command = data.command
        if isinstance(command, str):
            button_command = getattr(self, command)
        else:
            button_command = command

        new_button = tk.Button(parent_frame,
                               text=data.description,
                               state=button_state,
                               command=button_command)

        new_button.grid(row=row, column=1, pady=10)
        new_button.data = data
        new_button.backup_state = button_state
        setattr(parent_frame, name, new_button)

        return 1

    def add_optioned_label_frame(self, parent_frame, grid_location,
                                 frame_elements):
        """
        Given some basic data, this function creates a label frame
        at the given location, fills it with checkboxes, and
        when relevent, a command button.
        """

        name = frame_elements["name"]
        label = frame_elements["label"]

        # create new frame and store to self.
        new_frame = tk.LabelFrame(parent_frame, text=label)

        if grid_location is not None:
            column, row = grid_location
            new_frame.grid(
                row=row, column=column, sticky=tk.NW + tk.NE, pady=[10, 0], padx=10)

            new_frame.grid_columnconfigure(1, weight=1)

        setattr(self, name, new_frame)

        # initialise the last_row to 1 (as no parts have been placed yet)
        last_row = 1

        # create a variable: checkbutton_name lookup table.
        # to allow the on_update function to work.
        new_frame.variable_dict = {}

        row = last_row + 1
        for name, data in frame_elements.items():

            if is_cmdbutton(data):
                row += self.add_button(new_frame, row, name, data)

            if is_checkbutton(data):
                row += self.add_checkbutton(new_frame, row, name, data)

            if is_entrybox(data):
                row += self.add_entrybox(new_frame, row, name, data)

        last_row = row

        return last_row

    def get_user_options(self):
        """
        This method is used to lookup the
        user options (if the file exists)
        if the file does not exist, no changes
        are made to the checkboxes.
        """

        @contextmanager
        def enable_options_load(widget):
            """
            This contect manager will enable a widget
            while it is being invoked, while setting
            a flag to allow dependant updates to skip.    

            after invoking, the widget will return to its
            previous state and the program continues.
            """

            widget.options_load = True
            widget["state"] = tk.NORMAL
            yield
            widget.options_load = False
            widget["state"] = widget.backup_state

        user_options_path = self.fixture_path / self.ini_filename

        # if there is not user options file, exit.
        if not user_options_path.is_file():
            return

        with user_options_path.open() as f_user_options:
            user_options_layout = self.options_functions.load(f_user_options)

        # go through each section, updating the varibles
        for section_name, section_data in user_options_layout.items():
            for name, value in section_data.items():

                # get the tk_object associated with this variable.
                tk_object = self.user_data_widgets[name]

                variable = getattr(self, name)

                # invoke on_update if the tk_object has
                # dependants
                if hasattr(tk_object.data, "dependants") and tk_object.data.dependants:
                    with enable_options_load(tk_object):
                        variable.set(not value)
                        tk_object.invoke()
                else:
                    variable.set(value)

        # see if the checkbuttons are disabled.
        self.disable_checkbuttons()

    def set_user_options(self):
        """
        This method looks at all of the variables
        in the program, and stores them in the
        ini file.
        """
        self.user_options = self.options_functions.load()
        for section_name, section_data in self.user_options.items():
            for name, value in section_data.items():

                # store the tk VAR in a local variable (for instance checking)
                option_var = getattr(self, name)

                option_data = option_var.get()

                if isinstance(option_var, tk.BooleanVar):
                    section_data[name] = str(bool(option_data))
                else:
                    section_data[name] = str(option_data)

        with (self.fixture_path / self.ini_filename).open("w") as option_path:
            self.options_functions.save(self.user_options, option_path)

    def add_column_frame(self, column):
        """
        This function creates a column frame,
        and fills it with label frame option widgets.
        """

        frame_name = f"frm_column_{column}"

        column_frame = tk.Frame(self)
        column_frame.grid(row=1, column=column,
                          sticky=tk.NW + tk.S, padx=[10, 0])

        for section in self.form_widgets:

            position = section["position"]

            # only add items from this column.
            if position.column != column:
                continue

            hidden = section["hidden"]
            if self.engineering_flag or hidden is False:
                grid_location = (1, position.row)
            else:
                grid_location = None

            self.add_optioned_label_frame(column_frame, grid_location,
                                          section)

        setattr(self, frame_name, column_frame)

    def add_widgets(self):

        # in the event that add_widgets is called more than once,
        # reset the checkboxes variable.
        self.checkboxes = {}

        # get a set of all the columns.
        columns = {section["position"].column for section in self.form_widgets}

        for column in columns:
            self.add_column_frame(column)

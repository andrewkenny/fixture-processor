

# Admin /stdlib library imports.
import os
import sys
import base64
import argparse
import tempfile
import logging



# Admin / stdlib single imports.
from pathlib import Path


# functional imports
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askdirectory
from tkinter.filedialog import askopenfilename
from tkinter import messagebox as mb
from pathlib import Path
from typing import NamedTuple


from fixture_processor.options_lib import program_option_functions as p_options
from fixture_processor.options_lib import fixture_processing_options as fp_options

from fixture_processor.fixture_functions.fixture_input import get_outline_info

from fixture_processor.fixture_processor_form import FixtureProcessingForm
from fixture_processor.fixture_canvas_form import FixtureCanvas

from fixture_processor.fixture_functions import extract_wires as ew
from fixture_processor.fixture_functions import fixture_processing as fp
from fixture_processor.fixture_functions import fixture_modifications as fmod
from fixture_processor import file_operations as fo

# ---------

# ---------

# -250 : 0 : 250
CANVAS_SIZE = 650
PROGRAM_CONFIG_FOLDER = Path(f"{os.getenv('APPDATA')}/ForwessunFixtures")
# PROGRAM_CONFIG_FOLDER = Path( "./APPDATA/ForwessunFixtures")

PROGRAM_CONFIG_FILE = "config.ini"
PROGRAM_LOGGING_FILE = "ffp.log"

USER_OPTIONS_FILE = "user_options.ini"

# ensure the program folder exists.
PROGRAM_CONFIG_FOLDER.mkdir(parents=True, exist_ok=True)

FULL_LOGGING_PATH = Path(f"{PROGRAM_CONFIG_FOLDER}/{PROGRAM_LOGGING_FILE}")
print("FULL_LOGGING_PATH:", FULL_LOGGING_PATH)


try:
    if FULL_LOGGING_PATH.is_file():
        FULL_LOGGING_PATH.unlink()


except PermissionError:
    root = tk.Tk()
    root.withdraw()
    mb.showerror(
        "program error",
        "    This program is already running.\n\n    Closing...")
    sys.exit()


icon = "".join([
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAB4FBMVEUAAAD/02j/02j/02j/02j/",
    "02j/02j/02j/02j80Gb80Gb80Gb80Gb80Gb80Gb80Gb80Gb80Gb80Gb5zGT5zGT5zGT5zGT5zGT5",
    "zGT5zGT5zGT5zGT5zGT5zGT5zGT5zGT1x2H1x2H1x2H1x2H1x2H1x2H1x2H1x2H1x2H1x2H1x2H1",
    "x2Hwwl3wwl3wwl3wwl3wwl3wwl3wwl3wwl3wwl3wwl3wwl3wwl3rvFnrvFnrvFnrvFnrvFnrvFnr",
    "vFnrvFnrvFnmtlbmtlbmtlbmtlbmtlbmtlbmtlbmtlbmtlbmtlbmtlbgsFLgsFLgsFLgsFLgsFLg",
    "sFLgsFLgsFLgsFLgsFLgsFLgsFLgsFLaqU7aqU7aqU7aqU7aqU7aqU7aqU7aqU7aqU7Vo0rVo0rV",
    "o0rVo0rVo0rVo0rVo0rVo0rVo0rVo0rVo0rVo0rVo0rQnkbQnkbQnkbQnkbQnkbQnkbQnkbQnkbQ",
    "nkbQnkbQnkbQnkbQnkbLmEPLmEPLmEPLmEPLmEPLmEPLmEPLmEPLmEPLmEPLmEPHlD/HlD/HlD/H",
    "lD/HlD/HlD/HlD/HlD/HlD/HlD/HlD/EkD3EkD3EkD3EkD3EkD3EkD3EkD3EkD3BjTvBjTvBjTvB",
    "jTvBjTvBjTslMwBZAAAAoHRSTlMALYK81cvDgSlspd7l0cPj7Khna3winR5ycRGNQoFlBTXUMZxK",
    "Al0GqdMqCo5xitWQj7rInXaGBxaXMHNdRGKUIiWZKnCCK3gsVJc4Hr5+rLV/r66BocG8NRiSMHFf",
    "YEqRJpZ5kdaPjrm6kNlyiwlDySOZQFdWSZYp0DcKfGkkmRx5oBpzeAoBf6vg2L3O2tSifUWSztzn",
    "wZFBGFB0ck4XWZ6FzwAAAOlJREFUGNNjYMAGGJmYWVjZ2DlgfE4ubh5ePn4BQSEIX1hEVExcQlJK",
    "WkZWjkGegUFBUUlZRVVNTV1JQ0FTS5uBQUdXT9/A0MhIR8fYxNTMnMHCksHKmoHBxoaBwdaOwd6B",
    "wdHJ2cXVzdnd3c3D08nZy5vBx9fPPyAwMCg4MCQ0zC88giEyiiE6hoEhNg6I4xkSEhkYkpJTUtPS",
    "MzLTsrLTcnLzGBjyCwqLihlKShnKyisqq6qBDqupratvaGysa2puaWVoAwq0d3R2dff09vVPmAjz",
    "zKTJU6ZOmz5jJsK7s2bPmTtvPpgJAGJIN0wyMhTbAAAAAElFTkSuQmCC"
    ])


class ModeTuple(NamedTuple):
    design: bool = False
    debug: bool = False


class Window(tk.Frame):
    """
    The main window of the fixture processing software.
    """

    def __init__(self, fixture_path, engineering_flag, master=None):

        if master:
            tk.Frame.__init__(self, master)
            self.master.wm_title("Forwessun Fixture Processor")

            # todo add icon
            # img = tk.PhotoImage(file=ICON_DIRECTORY)
            # master.call('wm', 'iconphoto', master._w, img)

        self.fixture_path = ""

        # is True if the engineering flag is passed into the program.
        self.engineering_flag = engineering_flag

        self.pack()

        self.width_ratio = 1.6

        logging.info(f"Window Width radio = {self.width_ratio:.2f}")

        self.create_widgets()
        self.load_fixture(fixture_path)
        self.add_job_widgets()

    def get_program_options(self):
        """
        The following function will:
        create the 'forwessun_fixtures' folder in roaming,
        and will the 'config.ini' config file (if it doesn't exist)
        if they do exist, then the config is loaded and stored to self.
        """
        write_error = False

        if not PROGRAM_CONFIG_FOLDER.exists():
            PROGRAM_CONFIG_FOLDER.mkdir(parents=True)

        # set error flag if the folder is not a directory.
        # (or there are other errors)
        if not PROGRAM_CONFIG_FOLDER.is_dir():
            # todo - provide warning about invalid
            # config location.
            sys.exit()

        config_path = PROGRAM_CONFIG_FOLDER / PROGRAM_CONFIG_FILE

        if not config_path.exists():
            with config_path.open("w") as f_config:
                p_options.save({}, f_config)

        with config_path.open() as f_config:
            return p_options.load(f_config)

    def create_widgets(self):
        """Creates window widgets"""

        self.menubar = tk.Menu(self.master)

        self.menu_file = tk.Menu(self.menubar, tearoff=0)
        self.menu_file.add_command(label="Open", command=self.load_fixture)
        self.menu_file.add_command(label="Close", command=sys.exit)

        self.menubar.add_cascade(label="File", menu=self.menu_file)

        self.menubar.add_command(label="Redraw", command=self.redraw_fixture)

        self.master.config(menu=self.menubar)

        # The Header for the window
        # font = ("Courier", 30)
        # font = ("Times New Roman", 30)
        font = ("Arial", 25)
        self.lbl_header = tk.Label(self, font=font, justify=tk.CENTER)

        self.lbl_header["text"] = "Forwessun Fixture Processor"
        self.lbl_header.grid(row=1,
                             column=1,
                             columnspan=6,
                             padx=10,
                             pady=[10, 0])

        self.canvas_width = int(CANVAS_SIZE * self.width_ratio)
        self.canvas_height = CANVAS_SIZE

        self.ntbk_tabs = ttk.Notebook(self)
        self.ntbk_tabs["width"] = self.canvas_width
        self.ntbk_tabs["height"] = self.canvas_height
        self.ntbk_tabs.grid(row=3, column=1,
                            columnspan=6, padx=[0, 0], pady=[0, 0])

        self.fixture_canvas = FixtureCanvas(self, self.ntbk_tabs)
        self.fixture_canvas.grid(row=1, column=1,
                                 columnspan=6, padx=[5, 5], pady=[0, 5])

        self.ntbk_tabs.add(self.fixture_canvas, text="Fixture Layout Plot.")

    def add_job_widgets(self):
        """
        These contain the widgets to be added after the job has been loaded,
        To see what stage the job is at (design / debug / fixture only)
        """

        # add the fixture processing option widgets form.
        self.fp_form = FixtureProcessingForm(
            self.engineering_flag, self, self.ntbk_tabs)
        self.ntbk_tabs.add(self.fp_form, text="Fixture Processor Options.")
        
        # get user options, and fill the checkboxes
        self.fp_form.get_user_options()

    def choose_directory(self):

        file_path = askopenfilename(
            initialfile="fixture.o",
            multiple=False,
            filetypes=(("fixture file", "fixture.o"),
                       ("all files", "*.o")),
            title="Select Fixture file."
        )

        return Path(file_path).parent.as_posix()

    def validate_fixture_path(self, fixture_path=None):
        """
        This function makes sure that the path
        selected by the end user is a valid fixture path
        This means that is must contain a:

        - fixture.o file
        - wires file
        - inserts file
        """

        error_message = \
            "    Invalid directory chosen.\n" \
            "    Please try again."

        while True:

            continue_flag = False
            cancel_flag = False

            if fixture_path is None:
                logging.info("User is Choosing fixture folder")
                fixture_path = self.choose_directory()

            if fixture_path in ["", "."]:
                if self.fixture_path == "":
                    logging.info(
                        "User has pressed Cancel or [X] when selecting folder")
                    if mb.askokcancel("Quit", "Exit Now?"):
                        sys.exit()
                    else:
                        fixture_path = None
                        continue
                else:
                    cancel_flag = True
                    fixture_path = self.fixture_path

            fixture_path = Path(fixture_path)

            fixture_dot_o = fixture_path / "fixture.o"
            wires = fixture_path / "wires"
            inserts = fixture_path / "inserts"

            for file in [fixture_dot_o, wires, inserts]:

                not_present = not file.exists()
                invalid_file = file.is_dir()
                if not_present and invalid_file:
                    if not_present:
                        logging.info(
                            "'%s' cannot be found at '%s'", file.name, file.parent)
                    if not_present:
                        logging.info(
                            "'%s' in '%s' is not a valid file",
                            file.name,
                            file.parent)

                    mb.showerror("ERROR", error_message)
                    fixture_path = None

                    continue_flag = True
                    break
            if continue_flag:
                continue

            if cancel_flag:
                logging.info(
                    "User Pressed Cancel or (x). Program will keep previous path.")
            self.master.wm_title(fixture_path.as_posix())
            return fixture_path

    def redraw_fixture(self):
        """
        This method re-draws the fixture,
        and re-loads the program config to
        account for any changes.
        """

        self.fixture_canvas.draw_fixture()

    def load_fixture(self, fixture_path=None):
        """
        This method is called at the start of the program,
        And if the end user wishes to change the project
        they have open. it will:

         - ask the end user for a fixture directory
           if one has not been provided by way of an argument.
         - load the fixture contents.
         - process and scale the points.
         - update the plot to display the points.
        """
        self.program_options = self.get_program_options()
        self.fixture_path = self.validate_fixture_path(fixture_path)

        # draw the outline of the fixture to the fixture canvas.
        self.fixture_canvas.load_fixture_and_draw()




def main():
    "The main entry point to the program"

    # get the programs arguments.
    parser = argparse.ArgumentParser(
        description='Loads fixture related documents for processing'
        )

    help_text = "The path to the fixture directory you want to open."
    parser.add_argument('-P', '--Path', 
        type=str,
        help=help_text,
        default=None
        )

    help_text = "Enables extra Engineering specific options (not recomended)."
    parser.add_argument('-E', '--Engineering',
        help=help_text,
        action='store_true',
        default=False
        )

    help_text = "Enables the programs extra functions"
    parser.add_argument('-M', '--Mode',
        type=str,
        choices=["design", "debug"],
        default=None
        )

    args = parser.parse_args()
    str_fixture_path = args.Path
    engineering_flag = args.Engineering

    # if args.Mode is None:
    #     mode = ModeTuple()
    # elif args.Mode == "design":
    #     mode = ModeTuple(design=True)
    # elif args.Mode == "debug":
    #     mode = ModeTuple(debug=True)

    if str_fixture_path is None:
        fixture_path = None
    else:
        logging.info(f"path argument provided: {str_fixture_path}")
        fixture_path = Path(str_fixture_path)

    root = tk.Tk()
    root.resizable(False, False)

    with tempfile.NamedTemporaryFile('w+b',delete=False) as outputfile:
        outputfile.write(base64.b64decode(icon))
        
    img = tk.PhotoImage(file=outputfile.name)
    root.call('wm', 'iconphoto', root._w, img)
    
    try:
        os.unlink(outputfile.name)
    except:
        pass
    
    # create root object for tkinter


    logging.basicConfig(filename=FULL_LOGGING_PATH,
                        level=logging.DEBUG)

    app = Window(fixture_path,
                 engineering_flag,
                 master=root)

    app.mainloop()


# # begin the main program.
# if __name__ == "__main__":
#     main()

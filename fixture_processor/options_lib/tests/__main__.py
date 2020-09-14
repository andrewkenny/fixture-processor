
import sys

sys.path.insert(0, "..")


from program_options.options_functions import generate_option_functions


from program_options.options_list import get_section_comments as _get_section_comments
from program_options.options_list import get_options as _get_options


program_options = generate_option_functions(_get_section_comments(),
                                                     _get_options())

with open(r"C:\Users\Andrew Kenny\Documents\test.ini","w") as write_file:
    #Changed_data = {"Dialog_Options":{"default_folder": r"D:\Games"}}
    Changed_data = {}
    program_options.save(Changed_data, write_file)


with open(r"C:\Users\Andrew Kenny\Documents\test.ini",) as read_file:
    options = program_options.load(read_file)
    
    for section, options in options.items():
        print(section)
        
        for name, value in options.items():
            print ("   [{}] = {}".format(name, value))
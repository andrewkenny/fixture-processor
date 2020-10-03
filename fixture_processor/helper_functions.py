
"""
The aim of this module is to store helper functions,
not specific to fixture processing.
"""


def error_message_header(filename):
    """
    generates the error header, seen at the top
    of all messagebox errors.
    """
    
    def inner(line_number, raw_line):
        
        inner_filename = filename
        
        # removing trailing newline from rawline.
        raw_line = raw_line.rstrip("\r\n")
        
        return f"    The following line in '{inner_filename}\n'"\
               f"    {line_number}: '{raw_line}'\n"
        
    return inner

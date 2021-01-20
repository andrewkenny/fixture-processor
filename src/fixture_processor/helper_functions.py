
"""
The aim of this module is to store helper functions,
not specific to fixture processing.
"""


def error_message_header(filename, parsing=False):
    """
    generates the error header, seen at the top
    of all messagebox errors.
    """
    
    if parsing:
        first_line = f"    Error when parsing '{filename}'\n'"
    else:
        first_line = f"    Error found in '{filename}'\n'"
    
    
    def inner(line_number, raw_line):
        
        inner_filename = filename
        
        # removing trailing newline from rawline.
        raw_line = raw_line.rstrip("\r\n")
        
        return first_line + \
               f"    {line_number}: '{raw_line}'\n"
        
    return inner

from decimal import Decimal
from typing import Dict, Tuple

import operator as op

import math
import decimal
import logging
import typing

fp_logger = logging.getLogger('fixture_processing.fixture_maths')

# define constants
PHY_X_OFFSET = 21500
PHY_Y_OFFSET = 13000
MAX_PIN_PER_CARD = 78
PHY_PIN_DISTANCE = 1500
PHY_CARD_DISTANCE = 7000
PHY_ROW_DISTANCE = 3500
PHY_FIXTURE_MAXIMUM_X = 301000
PHY_HALF_BANK_WIDTH = 150000
PHY_FIXTURE_MAXIMUM_Y = 180000
X_TOOLING_OFFSET = 1889
Y_TOOLING_OFFSET = 85275
BANK1_OFFSET = 142500

# define derived constants.
MIDDLE = op.floordiv(PHY_FIXTURE_MAXIMUM_X, 2)
B2_C0_X = PHY_X_OFFSET + (MAX_PIN_PER_CARD * PHY_PIN_DISTANCE)
B1_C0_X = PHY_FIXTURE_MAXIMUM_X - PHY_X_OFFSET + PHY_PIN_DISTANCE
ROW0_Y = PHY_FIXTURE_MAXIMUM_Y - PHY_Y_OFFSET + PHY_CARD_DISTANCE


def xy_to_brc(x, y, fixture_size):
    """
    This function converts an XY coordinate (as described in the
    wires & inserts file) to a Bank Row Column format.

    if fixture_size is bank1, the bank will also always be 1.
    """

    # differes between xy_to_brc and brc_to_xy
    b1_c0_x = MIDDLE - PHY_X_OFFSET + PHY_PIN_DISTANCE

    x = x + X_TOOLING_OFFSET
    y = y + Y_TOOLING_OFFSET

    if x > MIDDLE:
        bank = 1
        column = (b1_c0_x - (x - MIDDLE)) / PHY_PIN_DISTANCE
    else:
        bank = 2
        column = (B2_C0_X - x) / PHY_PIN_DISTANCE

    row = (ROW0_Y - y) / PHY_CARD_DISTANCE

    if fixture_size.replace(" ", "") == "BANK1":
        bank = 1

    return (bank, row, column)


def brc_to_xy(bank, row, column, fixture_size):
    """
    This function converts a b r c as provided in the inserts / wires
    file into an x, y coordinate.

    it is recomended that this only be applied to none offset BRCs due to
    the loss of precision when applied to probes and transfers.
    """

    double_density_flag = False

    if column > MAX_PIN_PER_CARD:
        column = column - 100
        double_density_flag = True

    if bank == 1:
        XVal = B1_C0_X - (column * PHY_PIN_DISTANCE)
    else:
        XVal = B2_C0_X - (column * PHY_PIN_DISTANCE)

    YVal = ROW0_Y - (row * PHY_CARD_DISTANCE)

    if fixture_size.replace(" ", "") == "BANK1":
        XVal = XVal - BANK1_OFFSET

    if double_density_flag:
        if bank == 1:
            YVal = YVal + PHY_ROW_DISTANCE
        else:
            YVal = YVal - PHY_ROW_DISTANCE

    XVal = XVal - X_TOOLING_OFFSET
    YVal = YVal - Y_TOOLING_OFFSET

    return XVal, YVal


def get_wire_length(insert_1, insert_2):
    """
    Given 2 coords, consisting of a tuple of ints,
    with the unit of mils (10,000s of an inch).
    returns the distance in inches, rounded up to
    the nearest half inch.
    """

    x_1, y_1 = insert_1._wire_coord
    x_2, y_2 = insert_2._wire_coord

    mils_length = math.sqrt(((x_1 - x_2) ** 2) + ((y_1 - y_2) ** 2))

    inches_length = mils_length / 10_000

    half_rounded = math.ceil((inches_length + 0.25) * 2) / 2

    return f"{half_rounded:.1f}"


class CoordTuple(typing.NamedTuple):
    x_coord: int
    y_coord: int

    def __add__(self, other):
        """
        Used when adding 2 coords.
        """

        other_x, other_y = other

        return CoordTuple(self.x_coord + other_x, self.y_coord + other_y)

    def __sub__(self, other):
        """
        Used when adding 2 coords.
        """

        other_x, other_y = other

        return CoordTuple(self.x_coord - other_x, self.y_coord - other_y)

    def __mul__(self, other):
        if isinstance(other, CoordTuple):
            return self.x_coord * other.x_coord + self.y_coord * other.y_coord

        return CoordTuple(int(self.x_coord * other), int(self.y_coord * other))

    def rotate(self, angle):
        """
        rotate self counterclockwise by angle
        """

        perp = CoordTuple(-self.y_coord, self.x_coord)
        angle = angle * math.pi / 180.0

        c, s = math.cos(angle), math.sin(angle)

        new_x = int(self.x_coord * c + perp.x_coord * s)
        new_y = int(self.y_coord * c + perp.y_coord * s)

        return CoordTuple(new_x, new_y)

    def flip_coord(self, flip_count: int = 1):

        # when flip_count is even return
        # the original coord
        if (flip_count % 2) == 0:
            return self

        x, y = self

        return CoordTuple(x, -y)

    @classmethod
    def from_mm(cls, mm_x_coord: str, mm_y_coord: str):
        """
        creates a coord with the units in mils.
        assuming the input a string of the coord in mm.
        """
        mils_x_coord = int((float(mm_x_coord) * 100000) / 254)
        mils_y_coord = int((float(mm_y_coord) * 100000) / 254)

        return cls(mils_x_coord, mils_y_coord)

    @classmethod
    def from_mils(cls, mils_x_coord: str, mils_y_coord: str):
        """
        creates a coord with the units in mils
        assuming the input is a string of the coord in mils
        """

        return cls(int(mils_x_coord), int(mils_y_coord))
        
    @classmethod
    def from_mils_str(cls, mils_coord_str: str):
        """
        creates a coord with the units in mils
        assuming the input is a string of the coord in mils
        in a tuple like format.
        """
        
        mils_coord_str = mils_coord_str.strip("()")
        

        mils_x_coord, mils_y_coord = mils_coord_str.split(",")

        return cls(int(mils_x_coord), int(mils_y_coord))

    def to_mm(self) -> tuple:
        """
        returns a normal x, y tuple, containing the 
        coord, converted from mils to mm
        """
        coord_x, coord_y = self

        return (coord_x * 254) / 100000, (coord_y * 254) / 100000

    def to_brc(self, fixture_size: str):
        """
        Using the reference function, calculates the bank,
        row and column of the coord.
        """

        coord_x, coord_y = self

        # differences between xy_to_brc and brc_to_xy
        b1_c0_x = MIDDLE - PHY_X_OFFSET + PHY_PIN_DISTANCE

        coord_x = coord_x + X_TOOLING_OFFSET
        coord_y = coord_y + Y_TOOLING_OFFSET

        if coord_x > MIDDLE:
            bank = 1
            column = (b1_c0_x - (coord_x - MIDDLE)) / PHY_PIN_DISTANCE
        else:
            bank = 2
            column = (B2_C0_X - coord_x) / PHY_PIN_DISTANCE

        row = (ROW0_Y - coord_y) / PHY_CARD_DISTANCE

        if fixture_size.replace(" ", "").upper() == "BANK1":
            bank = 1

        return (bank, row, column)

    def to_brc_str(self, fixture_size: str, round_brackets=False) -> str:
        """
        performs normal to brc, then converts to string representation
        """

        (bank, row, column) = self.to_brc(fixture_size)

        if round_brackets:
            start = "("
            end = ")"
        else:
            start = "["
            end = "]"
            
        row_str = f"{abs(row):05.2f}"
        if f"{row}".startswith("-"):
            row_str = "-" + row_str

        return f"{start}{bank}{row_str:>6}  {column:.1f}{end}"


class PinID(str):
    """
    Based on a string, this class will contain
    helper methods / functions used to
    extract data and validate the pin_id

    All lower down methods assume the above
    validation methods passed.
    """

    # variables used for validation.
    _min_length: int = 5
    _max_length: int = 6

    _min_row: int = 1
    _max_row: int = 23

    _min_column: int = 1
    _max_column: int = MAX_PIN_PER_CARD

    @classmethod
    def from_elements(cls, bank, row, column, half):

        half_str = "1" if half else ""

        return cls(f"{bank}{row:0>2}{half_str}{column:0>2}")

    @property
    def validation_checks(self):

        yield (
            "is_valid_length",   f"    Current length of '{self}' is '{len(self)}.'\n"
                                 f"    Required Length is {self._min_length} - {self._max_length}.")

        yield (
            "is_valid_format",   f"    Token '{self}' contains illegal characters.\n"
                                 f"    A BRC / PIN can only consist of decimal numbers (0 - 9)")

        yield (
            "is_valid_bank",     f"    The current Bank is '{self.bank}'.\n"
                                 f"    Bank must be '1' or '2'.")

        yield (
            "is_valid_row",      f"    The current Row is '{self.row}'.\n"
                                 f"    Row must be {self._min_row} - {self._max_row}.")

        yield (
            "is_valid_half_row", f"    The current 'Half Row' is '{self.half_row}'.\n"
                                 f"    The 'Half Row' indicator must be '1'.")

        yield (
            "is_valid_column",   f"    The current Column is '{self.column}'.\n"
                                 f"    Column must be {self._min_column} - {self._max_column}")

    @property
    def is_valid_length(self) -> bool:
        """
        Returns true if the PinID is the correct length.
        (5 or 6)
        """

        return len(self) in range(self._min_length, self._max_length + 1)

    @property
    def is_valid_format(self) -> bool:
        """
        a PinID can only contain
        decimal integers.
        """

        try:
            int(self)
        except ValueError:
            return False
        else:
            return True

    @property
    def bank(self) -> int:
        """
        returns the first character
        of the PinID as an int.

        This represents the bank number.
        """

        return int(self[0])

    @property
    def is_valid_bank(self) -> bool:
        """
        The 3070 tester only has 2 banks,
        1 and 2.
        Returns False if the Bank is invalid.
        """

        return self.bank in [1, 2]

    @property
    def row(self) -> int:
        """
        returns the row of the PinId
        """
        return int(self[1:3])

    @property
    def is_valid_row(self) -> bool:
        """
        The are 23 rows in the 3070 tester.
        returns False if the PinID is outside
        of that range.
        """

        return self.row in range(self._min_row, self._max_row + 1)

    @property
    def is_half_row(self) -> bool:
        """
        This method returns True
        if the PinID is on the half row.
        """

        return len(self) == 6

    @property
    def half_row(self):
        """
        when a PinID refers to a half row,
        the fourth character is a 1.
        This returns that, or None if
        not relevent.
        """

        if self.is_half_row:
            return int(self[3])

        return None

    @property
    def is_valid_half_row(self) -> bool:
        """
        accepts None or 1
        """

        return self.half_row in [None, 1]

    @property
    def row_and_half(self) -> float:
        """
        gets the row, then adds
        half if the pin_id is
        on the second row.
        """

        # no half row means return pure row
        if not self.is_half_row:
            return float(self.row)

        if self.bank == 1:
            return self.row - 0.5
        else:
            return self.row + 0.5

    @property
    def column(self) -> int:
        """
        The last 2 digits of the PinID
        are the column.
        """

        return int(self[-2:])

    @property
    def is_valid_column(self) -> bool:
        """
        a column ins valid if it is between
        1 to 78 inclusive. (described by local variables.
        """

        return self.column in range(self._min_column, self._max_column + 1)

    @property
    def module(self) -> int:
        """
        The 3070 is split into 4 modules.
        0 and 1 are in bank 1
        2 and 3 are in bank 2
        This method returns the module this PinID is in.
        """

        msb = self.bank - 1
        lsb = self.row in range(13, 23 + 1)
        return (msb * 2) + lsb

    @property
    def is_asru(self) -> bool:
        """
        returns True if this PinID
        is on the Asru Card.
        """

        asru_set = \
            {"201", "213", "123", "111"}

        return self[:3] in asru_set

    @property
    def is_ctrl(self) -> bool:
        """
        Returns True if this PinID
        is on the control card.
        """

        return self.row in {6, 18}

    @property
    def is_testjet(self) -> bool:
        """
        Returns True if the PinID
        is one which is used for Testjet / VTEP
        """

        asru_tesetjet_columns = {
            1: {47, 8, 7, 3, 4, 5, 6},
            2: {32, 71, 72, 73, 74, 75, 76}}[self.bank]

        ctrl_tesetjet_columns = {
            1: {61, 60, 58, 56},
            2: {18, 19, 21, 23}}[self.bank]

        # half rows are not testjet / VTEP PinIDs.
        if self.is_half_row:
            return False

        if self.is_asru:
            return self.column in asru_tesetjet_columns
        elif self.is_ctrl:
            return self.column in ctrl_tesetjet_columns
        else:
            return False

    @property
    def is_asru_ground(self) -> bool:
        """
        Returns True if the PinID is
        on an asru card, and is a ground pin.
        """

        asru_ground_columns = {
            1: {30, 29, 28, 27, 15, 14, 13, 12},
            2: {49, 50, 51, 52, 64, 65, 66, 67}}[self.bank]

        # only relevent to main row of asru card.
        if not self.is_asru or self.is_half_row:
            return False

        return self.column in asru_ground_columns

    @property
    def is_ctrl_ground(self) -> bool:
        """
        At the time of writing, there are no
        control card ground pins.
        """
        return False

    @property
    def is_hybrid_ground(self) -> bool:
        """
        Returns True if the pinID is a ground
        on a hybrid / analog / digital card
        """

        hybrid_ground_columns = {19, 20, 39, 40, 59, 60}

        if self.is_asru or self.is_ctrl:
            return False

        return self.column in hybrid_ground_columns

    def is_fixture_ground(self, *, include_asru: bool = False, include_ctrl: bool = False) -> bool:
        """
        Returns True if the PinID is a fixture ground
        """

        asru_ground = include_asru and self.is_asru_ground
        ctrl_ground = include_ctrl and self.is_ctrl_ground

        return any([self.is_hybrid_ground, asru_ground, ctrl_ground])

    def to_xy(self, fixture_size: str) -> Tuple[int, int]:
        """
        This function converts self (the brc / pin) into 
        the X, Y coordinate which represents its location
        in the fixture.
        """

        row = self.row_and_half
        column = self.column

        if self.bank == 1:
            XVal = B1_C0_X - (self.column * PHY_PIN_DISTANCE)
        else:
            XVal = B2_C0_X - (self.column * PHY_PIN_DISTANCE)

        YVal = ROW0_Y - (self.row_and_half * PHY_CARD_DISTANCE)

        if fixture_size.replace(" ", "") == "BANK1":
            XVal = XVal - BANK1_OFFSET

        XVal = XVal - X_TOOLING_OFFSET
        YVal = YVal - Y_TOOLING_OFFSET

        return CoordTuple(XVal, int(YVal))


def create_brc_loc(pin_id, offset=None):
    """
    This function creates a bank row column
    fixture location from a pin id number

    so 20101 becomes (2 01.00  01.0)
    """

    # todo bank 1 calculations

    if offset:
        x, y = offset
    else:
        x, y = 0, 0

    bank = pin_id.bank
    row = Decimal(pin_id.row)
    column = Decimal(pin_id.column)

    half = Decimal("0.5")

    if pin_id.is_half_row:

        if bank == 1:
            row_decimal = row - half
        else:
            row_decimal = row + half
    else:
        row_decimal = row

    y_brc_offset = 0
    if y:
        y_brc_offset = Decimal(y / PHY_CARD_DISTANCE)

        # old program expects .5 to be rounded down not up.
        # the addition of 0.001 is intended to prevent this.
        row_decimal = row_decimal - y_brc_offset

    if x:
        x_brc_offset = Decimal(x / PHY_PIN_DISTANCE)

        column_decimal = column - x_brc_offset
    else:
        column_decimal = column

    one_dp = Decimal('.1')
    two_dp = Decimal('.01')
    rhu = decimal.ROUND_HALF_UP
    rhd = decimal.ROUND_HALF_DOWN

    rounded_row = row_decimal.quantize(two_dp, rounding=rhd)
    # rounded_column = column_decimal.quantize(two_dp, rounding=rhd)
    rounded_column = column_decimal.quantize(one_dp, rounding=rhd)

    brc_str = f"({bank} {rounded_row:05.2f}  {rounded_column:04.1f})"

    return brc_str


def throughput_multiplier(fixture_data):
    """
    This function runs a smoke test to see if the fixure
    information provided by the user is a throughput_multiplier
    fixture, In that its module grounds have to be seperated.
    """

    ground_nodes = fixture_data.ground_nodes


    throughput_multiplier_flag = True

    fp_logger.info(
        "Seeing if Hybrid grounds are shorted (throughput multiplier)")
    fp_logger.info("Ground nodes are: %s", ground_nodes)

    if len(ground_nodes) <= 1:
        fp_logger.info(
            "Single boards (or only one grounded board) cannot have throughput multiplier")
        return False, set()

    # get the bottom wires and inserts
    wires, inserts = fixture_data._bottom

    # first, filter the wires list, so that
    # only ground wires are present.
    ground_wires = []
    ground_inserts = {}

    # with the probe as a key, store all of the BRCs
    # that the probe is connected to in a list.
    probe_dict = {}
    node_dict = {}

    # first, collate all ground wires and inserts data.
    for coord_xy, insert_data in inserts.items():
        if insert_data.node in ground_nodes:
            ground_inserts[coord_xy] = insert_data

            insert_type = insert_data.insert_type
            if insert_type.endswith(" mil") or insert_type == "Transfer":
                probe_dict[insert_data] = set()

    fp_logger.info("ground probes found: %d", len(probe_dict))

    for wire_data in wires:
        from_xy, to_xy = wire_data._get_xy_coords

        # skip terminals.
        if to_xy == (0, 0) or from_xy == (0, 0):
            continue

        if from_xy in ground_inserts or to_xy in ground_inserts:
            # add the brcs directly connected to probes to the brc lists.

            to_insert = inserts[to_xy]

            insert_type = to_insert.insert_type

            if insert_type.endswith(" mil") or insert_type == "Transfer":
                from_insert = inserts[from_xy]
                probe_dict[to_insert].add(from_insert)

            else:
                ground_wires.append(wire_data)

    # possibly inefficient part of code.
    # consider refactorying in the future.

    while ground_wires:

        fp_logger.info(
            "%d wires are to be assigned to a ground probe", len(ground_wires))

        # the list entries we don't want to keep.
        del_list = []

        for index, wire_data in enumerate(ground_wires):

            # del flag goes True if this wire
            # is added to the pin_list
            del_flag = False

            from_xy, to_xy = wire_data._get_xy_coords

            from_insert = inserts[from_xy]
            to_insert = inserts[to_xy]

            for probe, pin_set in probe_dict.items():

                # see if the to and from are in the list.
                from_flag = from_insert in pin_set
                to_flag = to_insert in pin_set

                # if only one is present, add the other.
                if from_flag and not to_flag:
                    pin_set.add(to_insert)
                    del_flag = True

                elif to_flag and not from_flag:
                    pin_set.add(from_insert)
                    del_flag = True

            if del_flag:
                # fp_logger.debug("removing index %d from the next iteration of %s", index, ground_wires)
                del_list.append(index)

        ground_wires = [entry for index, entry
                        in enumerate(ground_wires)
                        if index not in del_list]

    # Create a "node dict"
    for i, (probe, pin_set) in enumerate(probe_dict.items()):
        node = probe.node

        fp_logger.debug("Probe %s (%s) has %d pins",
                        probe.brc, node, len(pin_set))
        if node not in node_dict:
            node_dict[node] = set()

        node_dict[node].update(pin_set)

    # iterate through the "node dict"
    
    fixture_module_list = set()
    
    for node, pin_set in node_dict.items():
        fp_logger.debug("Node %s  has %d pins", node, len(pin_set))
        fp_logger.debug("%s", pin_set)

        brc_list = [pin.fix_id.brc for pin in pin_set]

        module_list = {brc.module for brc in brc_list}
        
        # add this module list to the fixtures module list.
        fixture_module_list.update(module_list)

        if len(module_list) > 1:
            throughput_multiplier_flag = False
            
    # one module for the whole fixture means throughput multiplier is False.
    if len(fixture_module_list) == 1:
        throughput_multiplier_flag = False

        # fp_logger.debug("%s", [(brc,get_module(brc) ) for brc in brc_list])

    if throughput_multiplier_flag:
        fp_logger.debug("This is a throughput multiplier fixture.")
    else:
        fp_logger.debug("This is not a throughput multiplier fixture.")

    return throughput_multiplier_flag, module_list

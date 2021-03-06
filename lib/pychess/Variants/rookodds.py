from pychess.Utils.const import *
from pychess.Utils.Board import Board

ROOKODDSSTART = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/1NBQKBNR w Kkq - 0 1"

class RookOddsBoard(Board):
    variant = ROOKODDSCHESS
    __desc__ = _("One player starts with one less rook piece")
    name = _("Rook odds")
    cecp_name = "normal"
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_ODDS

    def __init__ (self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=ROOKODDSSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

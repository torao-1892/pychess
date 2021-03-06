#!/usr/bin/pypy -u
from __future__ import print_function

#if __name__ == "__main__":
#    print("feature done=0")

import os
import random
import sys
from time import time

this_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.join(this_dir, "../..") not in sys.path:
    sys.path = [os.path.join(this_dir, "../..")] + sys.path

from pychess.compat import PY2
from pychess.Utils import const
from pychess.Utils.book import getOpenings
from pychess.Utils.const import *
from pychess.Utils.lutils import lsearch
from pychess.Utils.lutils.ldata import MAXPLY
from pychess.Utils.lutils.lsearch import alphaBeta
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import listToSan, toSAN
from pychess.System.Log import log


class PyChess (object):
    def __init__ (self):
        self.sd = MAXPLY
        self.skipPruneChance = 0
        
        self.clock = [0, 0]
        self.increment = [0, 0]
        self.movestogo = 0
        self.searchtime = 0
        self.scr = 0 # The current predicted score. Used when accepting draw offers
        self.playingAs = WHITE
        self.ponder = False # Currently unused
        self.post = False
        self.debug = True
        self.outOfBook = False

    def print(self, text):
        print(text)
        sys.stdout.flush()
        log.debug(text, extra={"task": "stdout"})
    
    #===========================================================================
    # Play related
    #===========================================================================
    
    def __remainingMovesA (self):
        # Based on regression of a 180k games pgn
        x = self.board.plyCount
        return -1.71086e-12*x**6 \
               +1.69103e-9*x**5 \
               -6.00801e-7*x**4 \
               +8.17741e-5*x**3 \
               +2.91858e-4*x**2 \
               -0.94497*x \
               +78.8979
    
    def __remainingMovesB (self):
        # We bet a game will be around 80 moves
        x = self.board.plyCount
        return max(80-x,4)
    
    def __getBestOpening (self):
        totalWeight = 0
        choice = None
        if self.board.variant not in (ASEANCHESS, CAMBODIANCHESS, MAKRUKCHESS, \
                                      SITTUYINCHESS, LOSERSCHESS, SUICIDECHESS,\
                                      ATOMICCHESS, KINGOFTHEHILLCHESS, THREECHECKCHESS):
            for move, weight, histGames, histScore in getOpenings(self.board):
                totalWeight += weight
                if totalWeight == 0:
                    break
                if not move or random.randrange(totalWeight) < weight:
                    choice = move
        if choice is None:
            self.outOfBook = True
        return choice
    
    def __go (self, ondone=None):
        """ Finds and prints the best move from the current position """
        
        mv = False if self.outOfBook else self.__getBestOpening()
        if mv:
            mvs = [mv]
        
        if not mv:
               
            lsearch.skipPruneChance = self.skipPruneChance
            lsearch.searching = True
            
            timed = self.basetime > 0
            
            if self.searchtime > 0:
                usetime = self.searchtime
            else:
                usetime = self.clock[self.playingAs] / self.__remainingMovesA()
                if self.clock[self.playingAs] > 10:
                    # If we have time, we assume 40 moves rather than 80
                    usetime *= 2
                # The increment is a constant. We'll use this always
                usetime += self.increment[self.playingAs]

            prevtime = 0
            starttime = time()
            lsearch.endtime = starttime + usetime if timed else sys.maxsize
            if self.debug:
                if timed:
                    self.print("# Time left: %3.2f s; Planing to think for %3.2f s" % (self.clock[self.playingAs], usetime))
                else:
                    self.print("# Searching to depth %d without timelimit" % self.sd)

            for depth in range(1, self.sd+1):
                # Heuristic time saving
                # Don't waste time, if the estimated isn't enough to complete next depth
                if timed and usetime <= prevtime*4 and usetime > 1:
                    break
                lsearch.timecheck_counter = lsearch.TIMECHECK_FREQ
                search_result = alphaBeta(self.board, depth)
                if lsearch.searching:
                    mvs, self.scr = search_result
                    if time() > lsearch.endtime:
                        break
                    if self.post:
                        pv = " ".join(listToSan(self.board, mvs))
                        time_cs = int(100 * (time()-starttime))
                        self.print("%s %s %s %s %s" % (depth, self.scr, time_cs, lsearch.nodes, pv))
                else:
                    # We were interrupted
                    if depth == 1:
                        mvs, self.scr = search_result
                    break
                prevtime = time()-starttime - prevtime
                
                self.clock[self.playingAs] -= time() - starttime - self.increment[self.playingAs]
            
            if not mvs:
                if not lsearch.searching:
                    # We were interupted
                    lsearch.nodes = 0
                    return
                
                # This should only happen in terminal mode
                
                if self.scr == 0:
                    self.print("result %s" % reprResult[DRAW])
                elif self.scr < 0:
                    if self.board.color == WHITE:
                        self.print("result %s" % reprResult[BLACKWON])
                    else: self.print("result %s" % reprResult[WHITEWON])
                else:
                    if self.board.color == WHITE:
                        self.print("result %s" % reprResult[WHITEWON])
                    else: self.print("result %s" % reprResult[BLACKWON])
                return
            
            lsearch.nodes = 0
            lsearch.searching = False
        
        move = mvs[0]
        sanmove = toSAN(self.board, move)
        if ondone: ondone(sanmove)
        return sanmove
    
    def __analyze (self):
        """ Searches, and prints info from, the position as stated in the cecp
            protocol """
        
        start = time()
        lsearch.endtime = sys.maxsize
        lsearch.searching = True
        
        for depth in range (1, self.sd):
            if not lsearch.searching:
                break
            t = time()
            board = self.board.clone()
            mvs, scr = alphaBeta (board, depth)
            
            pv = " ".join(listToSan(board, mvs))
            time_cs = int(100 * (time() - start))
            self.print("%s %s %s %s %s" % (depth, scr, time_cs, lsearch.nodes, pv))
            
            lsearch.nodes = 0

################################################################################
# main                                                                         #
################################################################################

if __name__ == "__main__":
    import logging
    from pychess.Players.PyChessCECP import PyChessCECP
    from pychess.System.Log import log
    if len(sys.argv) == 1 or sys.argv[1:] == ["debug"]:
        if "debug" in sys.argv[1:]:
            log.logger.setLevel(logging.DEBUG)
        else:
            log.logger.setLevel(logging.WARNING)

        pychess = PyChessCECP()
    else:
        print("Unknown argument(s):", repr(sys.argv))
        sys.exit(0)
        
    pychess.makeReady()
    pychess.run()

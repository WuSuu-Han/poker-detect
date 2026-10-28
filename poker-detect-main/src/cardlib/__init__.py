# -*- coding: utf-8 -*-

__version__ = "0.1.0"

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["s", "h", "d", "c"]

SUIT_CN = {"s": "黑桃", "h": "红桃", "d": "方块", "c": "梅花"}
SUIT_SYMBOL = {"s": u"\u2660", "h": u"\u2665", "d": u"\u2666", "c": u"\u2663"}

RED_SUITS = ("h", "d")


def card_name(rank, suit):
    return "{}{}".format(rank, SUIT_CN.get(suit, suit))

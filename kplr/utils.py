# -*- coding: utf-8 -*-

from __future__ import division, print_function

__all__ = ["singleton"]


class singleton(object):

    def __init__(self, cls):
        self.cls = cls
        self.inst = None

    def __call__(self, *args, **kwargs):
        if self.inst is None:
            self.inst = self.cls(*args, **kwargs)
        return self.inst

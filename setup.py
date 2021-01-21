#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from setuptools import setup

setup(
    name="kplr",
    author="Daniel Foreman-Mackey",
    author_email="danfm@nyu.edu",
    packages=["kplr"],
    url="https://github.com/dfm/kplr",
    license="MIT",
    description="Tools for working with Kepler data in Python",
    long_description=open("README.rst").read(),
    install_requires=["six"],
    classifiers=[
        # "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
)

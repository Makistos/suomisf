# -*- coding: utf-8 -*-
from app.orm_decl import Work, Edition, Part, Person, Author, Editor, ShortStory, Alias
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import re
import os
from typing import Dict, List, Tuple


if __name__ == '__main__':
    import_magazines('bibfiles/magazines/')

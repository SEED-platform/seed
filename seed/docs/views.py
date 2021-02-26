# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.conf import settings
from django.contrib import auth
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import SetPasswordForm
from django.urls import reverse
from django.forms.forms import NON_FIELD_ERRORS
from django.forms.utils import ErrorList
from django.http import HttpResponseRedirect
from django.shortcuts import render

from collections import namedtuple
from json import dumps
import os
import re

import markdown
import yaml


YAML_DOC_BOUNDARY = re.compile(r"^-{3,}\s*$", re.MULTILINE)
FaqItem = namedtuple('FaqItem', ['question', 'answer', 'tags'])


def parse_faq_file(faq_file):
    """Turns an faq file into a dict

    :param faq_file: str | DirEntry
    :return: FaqItem
    """
    with open(faq_file) as f:
        _, frontmatter, body = YAML_DOC_BOUNDARY.split(f.read(), 2)
    parsed_frontmatter = yaml.safe_load(frontmatter)
    faq_item = FaqItem(
        question=parsed_frontmatter.get('question', ''),
        answer=markdown.markdown(body),
        tags=parsed_frontmatter.get('tags', [])
    )
    return faq_item


def faq_page(request):
    faq_dir = os.path.join(os.path.dirname(__file__), 'faq')
    faq_data = {}
    for category_dir in os.scandir(faq_dir):
        category_name = category_dir.name
        faq_data[category_name] = []
        for faq_file in os.scandir(category_dir):
            if faq_file.path.endswith('.md'):
                parsed_faq = parse_faq_file(faq_file)
                # convert to dict so json conversion works when templating
                faq_data[category_name].append(parsed_faq._asdict())

    return render(request, 'docs/faq.html', {'faq_data': faq_data})

#!/usr/bin/python
# -*- coding: utf-8 -*-
import pprint

from gapps import auth

__author__ = 'm.kupriyanov'

import settings
import sys
import difflib
import re

from googleapiclient.discovery import build

# if len(sys.argv) < 4:
#     print 'Usage: %s <job-file> <recursive> <dry-run>' % __file__
#     exit(1)

# Check https://developers.google.com/drive/scopes for all available scopes
OAUTH_SCOPES = [
    'https://www.googleapis.com/auth/tagmanager.readonly',
    #   'https://www.googleapis.com/auth/tagmanager.edit.containers',
]

# json_data = open(sys.argv[1])
# actions = json.load(json_data)

# RECURSIVE_RUN = (sys.argv[2] == 'true')
# DRY_RUN = (sys.argv[3] == 'true')

# print "RECURSIVE_RUN:%s" % RECURSIVE_RUN
# print "DRY_RUN:%s" % DRY_RUN


http = auth.Auth.create_service(
    ",".join(OAUTH_SCOPES)
    , 'config/credentials_gtm.txt'
    # , settings.CLIENT_CREDENTIALS_FILE
    # , settings.CLIENT_SECRET_FILE
    , 'config/client_secret_.json'
)

gtm_service = build('tagmanager', 'v1', http=http)

# containers
# get tags

#SOURCE CONTAINER
sourceAccountId = '<PUT_SOURCE_ACCOUNTID_HERE>'
sourceContainerId = '<PUT_SOURCE_CONTAINERID_HERE>'

source_tags = gtm_service.accounts().containers().tags().list(accountId=sourceAccountId,
                                                              containerId=sourceContainerId).execute()
source_variables = gtm_service.accounts().containers().variables().list(accountId=sourceAccountId,
                                                                        containerId=sourceContainerId).execute()
# pprint.pprint(source_tags)

# TARGET CONTAINER
targetAccountId = '<PUT_TARGET_ACCOUNTID_HERE>'
targetContainerId = '<PUT_TARGET_CONTAINERID_HERE>'

target_tags = gtm_service.accounts().containers().tags().list(accountId=targetAccountId,
                                                              containerId=targetContainerId).execute()
target_variables = gtm_service.accounts().containers().variables().list(accountId=targetAccountId,
                                                                        containerId=targetContainerId).execute()


# pprint.pprint(target_tags)

def get_tag_parameter_template_html(tag):
    for parameter in tag['parameter']:
        if parameter['type'] == 'template' and parameter['key'] == 'html':
            return parameter['value']


def compare_tag(source_tag, target_tag):
    result = {}

    source_parameter_template_html = get_tag_parameter_template_html(source_tag)
    target_parameter_template_html = get_tag_parameter_template_html(target_tag)

    if source_parameter_template_html == target_parameter_template_html:
        result['result'] = '='
        return result

    result['result'] = '!='

    # todo: Fix diff
    diff = difflib.context_diff(source_parameter_template_html, target_parameter_template_html, fromfile='before.py',
                                tofile='after.py')
    # print ''.join(diff)

    result['source'] = source_parameter_template_html
    result['target'] = target_parameter_template_html
    result['diff'] = ''.join(diff)

    return result


def get_tag_variables_from_html(tag):
    # get variables
    source_parameter_template_html = get_tag_parameter_template_html(tag)
    if not source_parameter_template_html:
        return

    p = re.compile('{{([^}]*)}}')
    variables = re.findall(p, source_parameter_template_html)
    variables = list(set(variables))  # get unique values
    if not variables:
        return

    return sorted(variables)


def compare_tags(source_tags, target_tags):
    result = {}
    # group by tag name
    for tag in source_tags['tags']:
        result[tag['name']] = {}
        result[tag['name']]['source'] = tag

        result[tag['name']]['source_variables'] = get_tag_variables_from_html(tag)
        result[tag['name']]['comparison_variables'] = '?'
        result[tag['name']]['target_variables'] = None

    for tag in target_tags['tags']:
        if tag['name'] in result:
            result[tag['name']]['target'] = tag
            result[tag['name']]['target_variables'] = get_tag_variables_from_html(tag)

            tag_comparison_result = compare_tag(result[tag['name']]['source'], tag)
            # print '%s\t%s' % (tag['name'], tag_comparison_result)

            result[tag['name']]['comparison'] = tag_comparison_result

            if result[tag['name']]['source_variables'] is None and result[tag['name']]['target_variables'] is None :
                result[tag['name']]['comparison_variables'] = '='
                continue

            if result[tag['name']]['source_variables'] is not None and result[tag['name']]['target_variables'] is not None:
                diff = list(
                    set(result[tag['name']]['source_variables']) - set(result[tag['name']]['target_variables']))
                if len(diff) == 0:
                    result[tag['name']]['comparison_variables'] = '='
                else:
                    result[tag['name']]['comparison_variables'] = diff


        else:
            result[tag['name']] = {}
            result[tag['name']]['target'] = tag

    return result


tags_comparison_result = compare_tags(source_tags, target_tags)

print '%s\t%s\t%s\t%s\t%s\t%s\t%s' % ('tag', 'source', 'comparison', 'target', 'variable_source', 'variable_comparison', 'variable_target')

for tag_name in sorted(tags_comparison_result.iterkeys()):
    tag_comparison_result = tags_comparison_result[tag_name]

    # print '---------------------'
    source = ''
    target = ''
    comparison = ''

    comparison_variables_source = ''
    comparison_variables_target = ''
    comparison_variables_comparison = '?'

    if 'source' in tag_comparison_result:
        source = 'o'

    if 'target' in tag_comparison_result:
        target = 'o'

    if 'comparison' in tag_comparison_result:
        comparison = '\'' + tag_comparison_result['comparison']['result']

    #variables output
    if 'source_variables' in tag_comparison_result:
        if tag_comparison_result['source_variables'] is not None:
            comparison_variables_source =  tag_comparison_result['source_variables']

    if 'target_variables' in tag_comparison_result:
        if tag_comparison_result['target_variables'] is not None:
            comparison_variables_target = tag_comparison_result['target_variables']

    if 'comparison_variables' in tag_comparison_result:
        if tag_comparison_result['comparison_variables'] is not None:
            comparison_variables_comparison = tag_comparison_result['comparison_variables']

    if comparison_variables_comparison == '=':
        comparison_variables_comparison = '\'='
        comparison_variables_source = ''
        comparison_variables_target = ''

    if comparison_variables_source == '' and comparison_variables_target == '':
        comparison_variables_comparison = ''

    #print '%s\t%s\t%s\t%s' % (tag_name, source, comparison, target)
    print '%s\t%s\t%s\t%s\t%s\t%s\t%s'  % (tag_name, source, comparison, target, comparison_variables_source, comparison_variables_comparison, comparison_variables_target)

sys.exit(0)

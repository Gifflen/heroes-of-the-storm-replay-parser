from __future__ import absolute_import

import os

from celery import shared_task
from celery.utils.log import get_task_logger

from api.StormReplayParser import StormReplayParser

import boto
import StringIO

import json
import gzip

from boto.s3.key import Key

log = get_task_logger(__name__)

@shared_task
def LocallyStoredReplayParsingTask(fileName):
    log.info('File name='+fileName)
    replayFile = open(fileName)
    srp = StormReplayParser(replayFile)
    log.info("Created StormReplayParser, getting data") 
    retval = {
        'unique_match_id': srp.getUniqueMatchId(),
        'map': srp.getMapName(),
        'players': srp.getReplayPlayers(),
        'chat': srp.getChat(),
        #'game': srp.getReplayGameEvents(),
    }
    log.info("Finished reading from StormReplay. Cleaning up.")
    replayFile.close()
    os.remove(replayFile.name)
    return retval

@shared_task
def S3StoredReplayParsingTask(keyName):

    splitKey = keyName.split('/')
    if len(splitKey) != 2:
        raise ValueError("keyName must be of the form: <folder>/<file>")
    keyBase = splitKey[0]
    resultKeyName = keyBase + '/replay.json.gz'

    #todo: duplicate limiting
    log.info('Key='+keyName)
    s3 = boto.connect_s3()
    bucket = s3.get_bucket(os.environ.get('AWS_BUCKET_NAME'), validate=False)

    k = Key(bucket)
    k.key = keyName

    #todo: is there a better way than just pretending the string is a file?
    # try: https://chromium.googlesource.com/external/boto/+/refs/heads/master/boto/s3/keyfile.py
    # It's possible we just need to read this to a temp file to save memory.
    # also: use cStringIO instead
    replayFile = StringIO.StringIO(k.get_contents_as_string())
    srp = StormReplayParser(replayFile)
    log.info("Created StormReplayParser, getting data") 

    retval = {
        'unique_match_id': srp.getUniqueMatchId(),
        'map': srp.getMapName(),
        'players': srp.getReplayPlayers(),
        'chat': srp.getChat(),
        #'game': srp.getReplayGameEvents(),
    }

    rk = Key(bucket)
    rk.key = resultKeyName
    rk.set_metadata('Content-Encoding', 'gzip')
    out = StringIO.StringIO()
    with gzip.GzipFile(fileobj=out, mode="w") as f:
        f.write(json.dumps(retval))
    rk.set_contents_from_string(out.getvalue())
    out.close()

    secondsToExpire = 1*60*60
    responseHeaders = {
        'response-content-encoding': 'gzip',
        'response-content-type': 'application/json',
    }
    s3UrlToResultKey = rk.generate_url(secondsToExpire, 'GET', response_headers=responseHeaders)

    log.info("Result: " + s3UrlToResultKey);
    log.info("Finished reading from StormReplay. Cleaning up.")
    return {
        'url': s3UrlToResultKey
    }


# todo: task specific logging?
# http://blog.mapado.com/task-specific-logging-in-celery/

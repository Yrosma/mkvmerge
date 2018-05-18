""" mkvmerge module

   ...

"""

import subprocess
import json
import threading
import os
import platform
import logging

MKVMERGE_EXECUTABLE = "mkvmerge.exe"

logger = logging.getLogger('mkvmerge')


def check_executable(mkvmerge_executable=MKVMERGE_EXECUTABLE):
    print("Check if mkvtoolnix is available ...")
    try:
        with open(os.devnull, 'w') as temp_file:
            subprocess.check_call([mkvmerge_executable, "-h"], stdout=temp_file, stderr=temp_file)
    except:
        print("mkvmerge not found")
        raise IOError('mkvmerge not found.')
    print("mkvtoolnix found")


def get_tracks(file):
    if str(platform.system()) == 'Windows':
        print("building command windows style")
        cmd = [MKVMERGE_EXECUTABLE, '-i', '-F', 'json', file]
    else:
        print("building command linux style")
        cmd = [MKVMERGE_EXECUTABLE + " -i -F json " + file]
    print(f'command : [{cmd}]')
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = p.communicate(timeout=10)
    json_output = stdout.decode('utf-8')
    err = stderr.decode('utf-8')
    print(f'json output : "{json_output}"')
    print(f'error : "{err}"')
    tracks = json.loads(json_output)["tracks"]
    print(f'type : {type(tracks)}, tracks : {tracks}')
    return tracks


def get_video_tracks(tracks):
    video = []
    for track in tracks:
        if track['type'] == 'video':
            video.append(track)
    if len(video) != 1:
        raise ValueError(f'no video track found in {tracks}')
    return video


def get_audio_tracks(tracks):
    audio = []
    for track in tracks:
        if track['type'] == 'audio':
            audio.append(track)
    if len(audio) == 0:
        logger.warning(f'no audio track found in {tracks}')
        return None
    return audio


def get_subtitle_tracks(tracks):
    subs = []
    for track in tracks:
        if track['type'] == 'subtitles':
            subs.append(track)
    if len(subs) == 0:
        logger.warning(f'no subtitle track found in {tracks}')
        return None
    return subs


def merge(options_filename):
    if str(platform.system()) == 'Windows':
        print("building command windows style")
        cmd = [MKVMERGE_EXECUTABLE, f'@{options_filename}']
    else:
        print("building command linux style")
        cmd = [MKVMERGE_EXECUTABLE + f' @{options_filename}']
    print(f'command : [{cmd}]')
    subprocess.call(cmd)


def disable_video_track(videoTrackId):
    return "-v !" + videoTrackId


def disable_audio_track(audioTrackId):
    return "-a !" + audioTrackId


def disable_subtitle_track(subtitleTrackId):
    return "-s !" + subtitleTrackId


def _getSubtitleLanguageCodeAndTrackName(languageId):
    language_code = str.lower(languageId)
    if (language_code == "nl" or language_code == "dut"):
        language = "dut"
        track_name = "Nederlands"
    elif (language_code == "en" or language_code == "eng"):
        language = "eng"
        track_name = "Engels"
    elif (language_code == "ja" or language_code == "jpn"):
        language = "jpn"
        track_name = "Japanese"
    else:
        language = "und"
        track_name = ""

    return language, track_name


def MergeSubtitle(subtitleTrackId, languageCode):
    id = subtitleTrackId
    language, trackname = _getSubtitleLanguageCodeAndTrackName(languageCode)

    return f'--language {id}:{language} --track-name {id}:{trackname} -- default-track {id}:false --forced-track {id}:false'
    """    "--language " + id + ":" + language +
           " --track-name " + id + ":" + trackname +
           " --default-track " + id + ":false --forced-track " + id + ":false"
    """


def MergeSubtitleFile(filename):
    file, ext = os.path.splitext(filename)
    file, languageCodeFromFile = file.rsplit('.', 1)
    language, trackname = _getSubtitleLanguageCodeAndTrackName(languageCodeFromFile)
    return f'--language 0:{language} --track-name 0:{trackname} --default-track 0:false --forced-track 0:false {filename}'
    """            "--language 0:" + language +
           " --track-name 0:" + trackname +
           " --default-track 0:false --forced-track 0:false " + filename
    """

if __name__ == '__main__':
    # execute only if run as the entry point into the program
    print("mkvmerge module")

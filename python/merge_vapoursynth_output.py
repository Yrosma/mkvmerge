""" Merge vapoursynth output

    When using vapoursynth for converting the video output will always be a seperated output.
    This output needed to merged back again.
    This module will search a given folder for the files that need to be merged together.
"""

import sys
import os
import time
import argparse
import json
import logging
from pathlib import Path

# import settings
import mkvmerge

# Const definitions
DEFAULT_VS_OUTPUT_POSTFIX_TEXT = "[filtered_video]"
DEFAULT_OPTION_FILE = "option_file.json"
DEFAULT_INPUT_FOLDER = "2do"
DEFAULT_OUTPUT_FOLDER = "done"

logger = logging.getLogger('vs_merge')


def _write_options_begin(file_handler):
    file_handler.write(f'[\n')


def _write_options_end(file_handler):
    file_handler.write(f']')


def _write_option(file_handler, option, comma=True):
    file_handler.write(f'    "{option}"')
    if comma:
        file_handler.write(f',')
    file_handler.write(f'\n')
    # if comma:
    #     file_handler.write(f'    "{option}",\n')
    # else:
    #     file_handler.write(f'    "{option}"\n')


def _write_language_option(file_handler, track_id, language):
    _write_option(file_handler, "--language")
    _write_option(file_handler, f'{track_id}:{language}')


def _write_track_name_option(file_handler, track_id, name=None):
    _write_option(file_handler, "--track-name")
    if name is None:
        _write_option(file_handler, f'{track_id}:')
    else:
        _write_option(file_handler, f'{track_id}:{name}')


def _write_default_track_option(file_handler, track_id, default):
    _write_option(file_handler, "--default-track")
    default_option = str(default)
    _write_option(file_handler, f'{track_id}:{default_option.lower()}')


def _write_forced_track_option(file_handler, track_id):
    _write_option(file_handler, "--forced-track")
    _write_option(file_handler, f'{track_id}:no')


def _write_subtitle_option(file_handler, subtitle):
    subtitle = str(subtitle)
    _write_forced_track_option(file_handler, 0)
    _write_default_track_option(file_handler, 0, 'no')
    _write_track_name_option(file_handler, 0)
    if '.nl.' in subtitle:
        _write_language_option(file_handler, 0, 'dut')
    elif '.en.' in subtitle:
        _write_language_option(file_handler, 0, 'eng')
    elif '.jp.' in subtitle:
        _write_language_option(file_handler, 0, 'jpn')
    else:
        raise ValueError(f'unknown subtitle language or filename does not contain language : "{subtitle}"')
    _write_filename_option(file_handler, subtitle)


def _write_filename_option(file_handler, filename, comma=True):
    _write_option(file_handler, filename.replace('\\', '\\\\'), comma)


def _write_options_ignore_video_tag(file_handler):
    _write_option(file_handler, "-D")


def _write_options_ignore_tags(file_handler):
    _write_option(file_handler, "-T")
    _write_options_ignore_global_tags(file_handler)


def _write_options_ignore_global_tags(file_handler):
    _write_option(file_handler, "--no-global-tags")


def _write_track_name_smart(file_handler, track, clean=False):
    if clean:
        _write_track_name_option(file_handler, track["id"])
    else:
        try:
            _write_track_name_option(file_handler, track["id"], track['properties']['track_name'])
        except KeyError:
            _write_track_name_option(file_handler, track["id"])


def create_mkvmerge_subtitles_option_file(
        media_file,
        subtitles,
        destination,
        option_filename=DEFAULT_OPTION_FILE,
        clean=False):

    with open(option_filename, "w") as f:
        _write_options_begin(f)
        _write_option(f, "-o")
        output_file = os.path.join(destination, os.path.basename(media_file))
        _write_filename_option(f, output_file)
        _write_options_ignore_tags(f)
        _write_option(f, "-S")
        # TODO dirty hack to get it working, media_file shoudl be fixed also containing the input folder
        # input_file = os.path.join('2do', os.path.basename(media_file))
        _write_filename_option(f, media_file)
        for subtitle in subtitles:
            _write_subtitle_option(f, subtitle)
        # TODO remove hack of the adding the -v option to force a command with comma false. The whole comma /
        # parameter should be removed and this should be handled differently but using + operator maybe? /
        # or look into how it is done with printing with the sep and end parameters
        _write_option(f, '-v', comma=False)
        _write_options_end(f)
        f.close()


def create_mkvmerge_vapoursynth_option_file(
        full_file,                              # filename of the file with all tracks
        video_file,                             # filename of the vapoursynth file with only the video track
        full_tracks,                            # track information of the file with all the tracks
        video_tracks,                           # track information of the vapoursynth output file
        destination,                            # destination folder
        option_filename=DEFAULT_OPTION_FILE,    # filename of the option file to generate
        clean=False):                           # if set the names will be cleaned
    with open(option_filename, "w") as f:
        _write_options_begin(f)
        _write_option(f, "-o")
        # _write_option(f, full_file.replace(DEFAULT_INPUT_FOLDER, DEFAULT_OUTPUT_FOLDER))
        output_file = os.path.join(destination, os.path.basename(full_file))
        _write_filename_option(f, output_file)
        _write_options_ignore_tags(f)

        # write mkvmerge video options
        video_only_track = mkvmerge.get_video_tracks(video_tracks)[0]
        audio_tracks = mkvmerge.get_audio_tracks(full_tracks)
        if audio_tracks is not None:
            _write_language_option(f, video_only_track["id"], audio_tracks[0]['properties']['language'])
            _write_track_name_option(f, 0)
            _write_default_track_option(f, 0, True)
            # _write_option(f, video_file)
            _write_filename_option(f, video_file)
            _write_options_ignore_tags(f)
            _write_options_ignore_video_tag(f)

            # write mkvmerge audio options
            for i in range(len(audio_tracks)):
                track = audio_tracks[i]
                _write_language_option(f, track["id"], track['properties']['language'])
                _write_track_name_smart(f, track, clean)
                # only write first audio track as default track, this should already be OK
                if i == 0:
                    _write_default_track_option(f, track["id"], True)
                else:
                    _write_default_track_option(f, track["id"], False)

        # write mkvmerge subtitle options
        subs_tracks = mkvmerge.get_subtitle_tracks(full_tracks)
        if subs_tracks is not None:
            for track in subs_tracks:
                _write_language_option(f, track["id"], track['properties']['language'])
                _write_track_name_smart(f, track, clean)
                _write_default_track_option(f, track["id"], False)

        # _write_option(f, full_file, comma=False)
        _write_filename_option(f, full_file, comma=False)
        _write_options_end(f)
        f.close()


def merge_video_files(media_full, media_video_only, destination, clean, working_dir=None):
    # TODO check destination as it looks sometimes its a folder, other times its a file
    print(f'destination is "{destination}"')
    # TODO: check if folder than do the make dir, not always
    os.makedirs(destination, exist_ok=True)
    print(f'Full media file : "{media_full}"\nVideo only file : "{media_video_only}"')
    full_tracks = mkvmerge.get_tracks(media_full)
    video_tracks = mkvmerge.get_tracks(media_video_only)
    print(f'type: {type(full_tracks)}, full tracks : {full_tracks}')
    print(f'type: {type(video_tracks)}, video track : {video_tracks}')
    # TODO: options_file should be handled better
    if working_dir is not None:
        options_file = os.path.join(working_dir, 'options_file.json')
    else:
        options_file = 'options_file.json'
    create_mkvmerge_vapoursynth_option_file(
        media_full,
        media_video_only,
        full_tracks,
        video_tracks,
        destination,
        option_filename=options_file,
        clean=clean)
    mkvmerge.merge(options_file)


def merge_subtitle_files(media_file, subtitles, destination, clean):
    print(f'-> media file : "{media_file}"\n-> subtitles : {subtitles}\n-> destination : "{destination}\n-> clean : {clean}"')
    options_file = 'subtitles_options_file.json'
    create_mkvmerge_subtitles_option_file(
        media_file,
        subtitles,
        destination,
        option_filename=options_file,
        clean=clean)
    mkvmerge.merge(options_file)


def merge_vapoursynth_output_in_folder(working_folder, vs_postfix_text, extension, clean):
    """     loop through the working dir folder and merge the vapoursynth output files
    """
    print(f'working_folder : "{working_folder}"\nvs_postfix_text : "{vs_postfix_text}"\nextension : "{extension}"')
    print(f'Check folder still exist "{working_folder}":"{str(os.path.isdir(working_folder))}"')
    for root, dirs, files in os.walk(working_folder):
        print("root : ", root)
        print("dirs : ", dirs)
        print(f"type : {type(files)}, files : {files}")

        for file in files:
            print(file)
            name, ext = os.path.splitext(file)
            print(f'name : "{name}"\nextension : "{ext}"')
            if ext == extension and vs_postfix_text in name:
                filename = os.path.join(root, file)
                video_only = os.path.abspath(filename)
                full = os.path.abspath(filename).replace(vs_postfix_text, "")
                merge_video_files(full, video_only, DEFAULT_OUTPUT_FOLDER, clean)


def _look_for_subs_belonging_to_media_file(media_file):
    found_subs = []
    name, _ = os.path.splitext(media_file)
    folder = os.path.dirname(media_file)
    print(f'folder to search subs in is "{folder}"')
    folder = Path(folder)
    for current_file in folder.iterdir():
        sub_name, ext = os.path.splitext(current_file)
        print(f'sub name : "{sub_name}"\nextension : "{ext}"')
        accepted_extensions = ['.srt', '.ssa', 'ass']
        if ext in accepted_extensions:
            print(f'a subtitle found : "{current_file}"')
            if name in sub_name:
                found_subs.append(str(current_file))
    return found_subs


def _sort_subtitles_to_defined_order(subtitles, languages):
    sorted_subs = []
    for l in languages:
        for sub in subtitles:
            if l.lower() in sub.lower():
                sorted_subs.append(sub)
    return sorted_subs


def merge_seperate_subtitles_in_folder(working_folder, output_folder, clean):
    """     loop through the working dir folder and merge the vapoursynth output files
    """
    print(f'working_folder : "{working_folder}"\ndestination : "{output_folder}"')
    print(f'Check folder still exist "{working_folder}":"{str(os.path.isdir(working_folder))}"')
    for root, dirs, files in os.walk(working_folder):
        print("root : ", root)
        print("dirs : ", dirs)
        print(f"type : {type(files)}, files : {files}")

        for file in files:
            print(file)
            name, ext = os.path.splitext(file)
            print(f'name : "{name}"\nextension : "{ext}"')
            accepted_extensions = ['.mkv', '.mp4']
            if ext in accepted_extensions:
                filename = os.path.join(root, file)
                print(f'media file found : "{filename}", looking for subs')
                subs = _look_for_subs_belonging_to_media_file(filename)
                print(f'subtitles found : [{subs}]')
                subs = _sort_subtitles_to_defined_order(subs, ['nl', 'en', 'jp'])
                print(f'subtitles sorted : [{subs}]')
                merge_subtitle_files(os.path.join(root, file), subs, output_folder, clean=clean)

                # video_only = os.path.abspath(filename)
                # full = os.path.abspath(filename).replace(vs_postfix_text, "")
                # merge_video_files(full, video_only, DEFAULT_OUTPUT_FOLDER, clean)

# return file_list

# MkvMergeCheckExecutable()

# color_text.header("Scanning file : " + mkvFile + " ...")
# MkvMergeIdentify(mkvFile)


if __name__ == '__main__':
    print("Merging vapoursynth output files")
    parser = argparse.ArgumentParser("Vapoursynth output merging parameters.")
    parser.add_argument("-i",
                        "--input_directory",
                        help="input folder to scan for merging",
                        required=True)
    parser.add_argument("-o",
                        "--output_directory",
                        help="output folder for merging output files",
                        required=True)
    parser.add_argument("-v",
                        "--vs_postfix_text",
                        help="vapoursynth postfix text for the video output file",
                        required=False,
                        default=DEFAULT_VS_OUTPUT_POSTFIX_TEXT)
    parser.add_argument("-e",
                        "--extension",
                        help="expected extension of the vapoursynth output files",
                        required=False,
                        default='mkv')
    parser.add_argument("-c",
                        "--clean",
                        help="enabled the merge will also clean titles / track names etc",
                        required=False,
                        action='store_true')
    parser.add_argument("-s",
                        "--subtitles",
                        help="subtitles are expected to be in seperate files with 2 char language code",
                        required=False,
                        action="store_true")

    args = parser.parse_args()
    print(args)

    mkvmerge.check_executable()

    if args.subtitles:
        merge_seperate_subtitles_in_folder(
            working_folder=args.input_directory,
            output_folder=args.output_directory,
            clean=args.clean)
    else:
        merge_vapoursynth_output_in_folder(
            working_folder=args.input_directory,
            vs_postfix_text=args.vs_postfix_text,
            extension=str.format('.{}', args.extension),
            clean=args.clean)

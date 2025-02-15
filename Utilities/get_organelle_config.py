#!/usr/bin/env python

import sys
import os
import platform
import time
from shutil import copy
from argparse import ArgumentParser
PATH_OF_THIS_SCRIPT = os.path.split(os.path.realpath(__file__))[0]
sys.path.insert(0, os.path.join(PATH_OF_THIS_SCRIPT, ".."))
import GetOrganelleLib
from GetOrganelleLib.versions import get_versions
from GetOrganelleLib.seq_parser import check_fasta_seq_names
from GetOrganelleLib.pipe_control_func \
    import \
    GO_PATH, LBL_NAME, SEQ_NAME, LBL_DB_PATH, SEQ_DB_PATH, \
    remove_db_postfix, make_blast_db, build_bowtie2_db, simple_log, \
    detect_bowtie2_path, detect_blast_path, detect_bowtie2_version, detect_blast_version, \
    cal_f_sha256, \
    ORGANELLE_TYPE_LIST, ORGANELLE_TYPE_SET, SEED_DB_HASH, LABEL_DB_HASH, \
    get_static_html_context, download_file_with_progress, get_current_db_versions
PATH_OF_THIS_SCRIPT = os.path.split(os.path.realpath(__file__))[0]

# system info
SYSTEM_NAME = ""
if platform.system() == "Linux":
    SYSTEM_NAME = "linux"
elif platform.system() == "Darwin":
    SYSTEM_NAME = "macOS"
else:
    sys.stdout.write("Error: currently GetOrganelle is not supported for " + platform.system() + "! ")
    exit()
# python version
MAJOR_VERSION, MINOR_VERSION = sys.version_info[:2]
if MAJOR_VERSION == 2 and MINOR_VERSION >= 7:
    pass
elif MAJOR_VERSION == 3 and MINOR_VERSION >= 5:
    pass
else:
    sys.stdout.write("Python version have to be 2.7+ or 3.5+")
    sys.exit(0)


LIB_NAME = "GetOrganelleLib"
DEP_NAME = "GetOrganelleDep"
GO_LIB_PATH = os.path.split(GetOrganelleLib.__file__)[0]
GO_DEP_PATH = os.path.realpath(os.path.join(GO_LIB_PATH, "..", DEP_NAME, SYSTEM_NAME))
UTILITY_PATH = os.path.join(PATH_OF_THIS_SCRIPT, "Utilities")

_GO_PATH = GO_PATH
_LBL_DB_PATH = LBL_DB_PATH
_SEQ_DB_PATH = SEQ_DB_PATH

VERSION_URLS = ["https://raw.githubusercontent.com/Kinggerm/GetOrganelleDB/master/VERSION",
                "https://gitlab.com/Kinggerm/GetOrganelleDB/-/raw/master/VERSION",
                "https://gitee.com/jinjianjun/GetOrganelleDB/raw/master/VERSION"]
seed_url_temp = ["https://raw.githubusercontent.com/Kinggerm/GetOrganelleDB/master/{0}/SeedDatabase/{1}.fasta",
                 "https://gitlab.com/Kinggerm/GetOrganelleDB/-/raw/master/{0}/SeedDatabase/{1}.fasta",
                 "https://gitee.com/jinjianjun/GetOrganelleDB/raw/master/{0}/SeedDatabase/{1}.fasta"]
label_url_temp = ["https://raw.githubusercontent.com/Kinggerm/GetOrganelleDB/master/{0}/LabelDatabase/{1}.fasta",
                  "https://gitlab.com/Kinggerm/GetOrganelleDB/-/raw/master/{0}/LabelDatabase/{1}.fasta",
                  "https://gitee.com/jinjianjun/GetOrganelleDB/raw/master/{0}/LabelDatabase/{1}.fasta"]


def get_options(description):
    parser = ArgumentParser(description=description, usage="get_organelle_config.py -a embplant_pt,embplant_mt")
    parser.add_argument("-a", "--add", dest="add_organelle_type",
                        help="Add database for organelle type(s). Followed by any of all/" +
                             "/".join(ORGANELLE_TYPE_LIST) + " or multiple types joined by comma such as "
                             "embplant_pt,embplant_mt,fungus_mt.")
    parser.add_argument("--use-version", dest="db_version", default="latest",
                        help="The version of database to add. "
                             "Find more versions at github.com/Kinggerm/GetOrganelleDB. "
                             "Default: %(default)s")
    parser.add_argument("-r", "--rm", dest="rm_organelle_type",
                        help="Remove local database(s) for organelle type(s). Followed by any of all/" +
                             "/".join(ORGANELLE_TYPE_LIST) + " or multiple types joined by comma "
                             "such as embplant_pt,embplant_mt.")
    parser.add_argument("--update", dest="update", default=False, action="store_true",
                        help="Update local databases to the latest online version, or the local version "
                             "if \"--use-local LOCAL_DB_PATH\" provided.")
    parser.add_argument("--config-dir", dest="get_organelle_path", default=None,
                        help="The directory where the default databases were placed. "
                             "The default value also can be changed by adding 'export GETORG_PATH=your_favor' "
                             "to the shell script (e.g. ~/.bash_profile or ~/.bashrc) "
                             "Default: " + GO_PATH)
    parser.add_argument("--use-local", dest="use_local",
                        help="Input a path. This local database path must include subdirectories "
                             "LabelDatabase and SeedDatabase, under which there is the fasta file(s) named by the "
                             "organelle type you want add, such as fungus_mt.fasta. ")
    parser.add_argument("--clean", dest="clean", default=False, action="store_true",
                        help="Remove all configured database files (==\"--rm all\").")
    parser.add_argument("--list", dest="list_available", default=False, action="store_true",
                        help="List configured databases checking and exit. ")
    parser.add_argument("--check", dest="check", default=False, action="store_true",
                        help="Check configured database files and exit. ")
    parser.add_argument("--db-type", dest="db_type", default="both",
                        help="The database type (seed/label/both). Default: %(default)s")
    parser.add_argument("--which-blast", dest="which_blast", default="",
                        help="Assign the path to BLAST binary files if not added to the path. "
                             "Default: try \"" + os.path.realpath("GetOrganelleDep") + "/" + SYSTEM_NAME +
                             "/ncbi-blast\" first, then $PATH")
    parser.add_argument("--which-bowtie2", dest="which_bowtie2", default="",
                        help="Assign the path to Bowtie2 binary files if not added to the path. "
                             "Default: try \"" + os.path.realpath("GetOrganelleDep") + "/" + SYSTEM_NAME +
                             "/bowtie2\" first, then $PATH")
    parser.add_argument("--verbose", dest="verbose", default=False, action="store_true",
                        help="verbose output to the screen. Default: %(default)s")
    parser.add_argument("-v", "--version", action="version",
                        version="GetOrganelle v{version}".format(version=get_versions()))
    options = parser.parse_args()
    assert options.db_type in ("seed", "label", "both")
    global _GO_PATH, _LBL_DB_PATH, _SEQ_DB_PATH
    if options.get_organelle_path:
        _GO_PATH = os.path.expanduser(options.get_organelle_path)
        if os.path.isdir(_GO_PATH):
            _LBL_DB_PATH = os.path.join(_GO_PATH, LBL_NAME)
            _SEQ_DB_PATH = os.path.join(_GO_PATH, SEQ_NAME)

    # check directories
    if not os.path.isdir(_GO_PATH):
        os.mkdir(_GO_PATH)
    if not os.path.isdir(_LBL_DB_PATH):
        os.mkdir(_LBL_DB_PATH)
    if not os.path.isdir(_SEQ_DB_PATH):
        os.mkdir(_SEQ_DB_PATH)

    # only print
    if options.list_available:
        if options.db_type in ("seed", "both"):
            version_file = os.path.join(_SEQ_DB_PATH, "VERSION")
            if os.path.isfile(version_file):
                with open(version_file) as open_version:
                    for line in open_version:
                        db_type, db_version, db_hash = line.strip().split("\t")
                        db_version = find_version(db_type, db_hash, SEED_DB_HASH, db_version)
                        sys.stdout.write(db_type + " Seed Database:\t" + db_version + "\t" + db_hash + "\n")
        if options.db_type in ("label", "both"):
            version_file = os.path.join(_LBL_DB_PATH, "VERSION")
            if os.path.isfile(version_file):
                with open(version_file) as open_version:
                    for line in open_version:
                        db_type, db_version, db_hash = line.strip().split("\t")
                        db_version = find_version(db_type, db_hash, LABEL_DB_HASH, db_version)
                        sys.stdout.write(db_type + " Label Database:\t" + db_version + "\t" + db_hash + "\n")
        sys.exit()

    # sys.stdout.write("\n" + description + "\n")
    sys.stdout.write("\nPython " + str(sys.version).replace("\n", " ") + "\n")
    options.which_bowtie2 = detect_bowtie2_path(options.which_bowtie2, GO_DEP_PATH)
    options.which_blast = detect_blast_path(options.which_blast, GO_DEP_PATH)
    bowtie2_v = detect_bowtie2_version(options.which_bowtie2)
    if bowtie2_v.endswith("N/A"):
        sys.stdout.write("ERROR: Bowtie2 is not available!\n")
        sys.exit()
    blast_v = detect_blast_version(options.which_blast)
    if blast_v.endswith("N/A"):
        sys.stdout.write("ERROR: Blast is not available!\n")
        sys.exit()
    sys.stdout.write("DEPENDENCIES: " + "; ".join([bowtie2_v, blast_v]) + "\n")
    sys.stdout.write("WORKING DIR: " + os.getcwd() + "\n")
    sys.stdout.write(" ".join(["\"" + arg + "\"" if " " in arg else arg for arg in sys.argv]) + "\n\n")
    if not (options.add_organelle_type or options.rm_organelle_type or options.update or options.clean):
        parser.print_help()
        sys.stdout.write("Insufficient arguments!\n")
        sys.exit()

    mutually_exclusive_options = [(options.add_organelle_type, "adding"), (options.rm_organelle_type, "removing"),
                                  (options.update, "updating"), (options.clean, "cleaning")]
    for config_mode1, config_name1 in mutually_exclusive_options:
        for config_mode2, config_name2 in mutually_exclusive_options:
            if config_name1 != config_name2:
                assert not (config_mode1 and config_mode2), \
                    config_name1 + " and " + config_name2 + " removing are mutually exclusive!"

    if options.add_organelle_type:
        options.add_organelle_type = options.add_organelle_type.split(",")
        for sub_type in options.add_organelle_type:
            if sub_type == "all":
                options.add_organelle_type = list(ORGANELLE_TYPE_LIST)
                break
            elif sub_type not in ORGANELLE_TYPE_SET:
                sys.stdout.write("Illegal 'adding' type: " + sub_type + "! "
                                 "Types must be one of all/" + "/".join(ORGANELLE_TYPE_LIST) + "!\n")
                sys.exit()

    if options.rm_organelle_type:
        options.rm_organelle_type = options.rm_organelle_type.split(",")
        for sub_type in options.rm_organelle_type:
            if sub_type == "all":
                options.clean = True
                break
            elif sub_type not in ORGANELLE_TYPE_SET:
                sys.stdout.write("Illegal 'removing' type: " + sub_type + "! "
                                 "Types must be one of all/" + "/".join(ORGANELLE_TYPE_LIST) + "!\n")
                sys.exit()

    if options.use_local:
        if not os.path.isdir(options.use_local):
            raise NotADirectoryError(options.use_local)
        if options.add_organelle_type:
            for sub_type in options.add_organelle_type:
                this_fas_f = os.path.join(options.use_local, SEQ_NAME, sub_type + ".fasta")
                if not os.path.isfile(this_fas_f):
                    sys.stdout.write("File " + this_fas_f + " not available!\n")
                    sys.exit()
                this_fas_f = os.path.join(options.use_local, LBL_NAME, sub_type + ".fasta")
                if not os.path.isfile(this_fas_f):
                    sys.stdout.write("File " + this_fas_f + " not available!\n")
                    sys.exit()
        options.db_version = "customized"
        sys.stdout.write("Use local database: " + options.use_local + "\n")
    else:
        if options.update:
            options.db_version = "latest"
        if options.db_version == "latest":
            remote_quest = get_static_html_context(VERSION_URLS[0], verbose=options.verbose,
                                                   alternative_url_list=VERSION_URLS[1:])
            if remote_quest["status"]:
                options.db_version = remote_quest["content"].strip()
            else:
                sys.stderr.write("Error: " + remote_quest["info"] + "\n")
                sys.stderr.write("Please check your connection to github/gitee!\n")
                sys.stdout.write("\nYou can download the database files from www.github.com/Kinggerm/GetOrganelleDB "
                                 "and install it from from local (flag --use-local)\n")
                sys.exit()
        if options.db_version not in SEED_DB_HASH or options.db_version not in LABEL_DB_HASH:
            sys.stderr.write("GetOrganelle v{} does not support Database v{}\n".
                             format(get_versions(), options.db_version) +
                             "Please upgrade GetOrganelle (recommended) "
                             "or degrade the Database version (not recommended; --use-version)\n")
            sys.exit()

    return options


def write_version_file(version_dict, output_to_file):
    with open(output_to_file, "w") as output_f_handler:
        for organelle_type in ORGANELLE_TYPE_LIST:
            if organelle_type in version_dict:
                this_version = version_dict[organelle_type]
                output_f_handler.write(
                    organelle_type + "\t" + this_version["version"] + "\t" + this_version["sha256"] + "\n")


def rm_files(path_to, file_name_prefix="", file_name_postfix=""):
    for file_to_del in os.listdir(path_to):
        if file_to_del.startswith(file_name_prefix) and file_to_del.endswith(file_name_postfix):
            os.remove(os.path.join(path_to, file_to_del))


def find_version(organelle_type, hash_val, DB_dict, default_version_val="customized"):
    for try_version in sorted(DB_dict, reverse=True):
        if organelle_type in DB_dict[try_version] and hash_val == DB_dict[try_version][organelle_type]["sha256"]:
            return try_version
    else:
        return default_version_val


def initialize_notation_database(which_blast, fasta_f, overwrite=False, verbose=False):
    # blast index
    output_base = remove_db_postfix(fasta_f)
    sys.stdout.write("makeblastdb " + os.path.basename(fasta_f)  + " ... ")
    sys.stdout.flush()
    if overwrite or sum([os.path.exists(output_base + postfix) for postfix in (".nhr", ".nin", ".nsq")]) != 3:
        make_blast_db(input_file=fasta_f, output_base=output_base, which_blast=which_blast, verbose_log=verbose)
        sys.stdout.write("finished\n")
    else:
        sys.stdout.write("skipped\n")


def initialize_seed_database(which_bowtie2, fasta_f, overwrite=False, verbose=False):
    # bowtie index
    new_seed_file = fasta_f + ".modified"
    changed = check_fasta_seq_names(fasta_f, new_seed_file)
    if changed:
        seed_file = new_seed_file
    else:
        seed_file = fasta_f
    output_base = remove_db_postfix(fasta_f) + ".index"
    sys.stdout.write("bowtie2-build " + os.path.basename(fasta_f) + " ... ")
    sys.stdout.flush()
    if overwrite or sum([os.path.exists(output_base + postfix)
                         for postfix in
                         (".1.bt2l", ".2.bt2l", ".3.bt2l", ".4.bt2l", ".rev.1.bt2l", ".rev.2.bt2l")]) != 6:
        build_bowtie2_db(seed_file=seed_file, seed_index_base=output_base, which_bowtie2=which_bowtie2,
                         overwrite=overwrite, random_seed=12345, silent=verbose, verbose_log=verbose)
        sys.stdout.write("finished\n")
    else:
        sys.stdout.write("skipped\n")
    if changed:
        os.remove(seed_file)


def main():
    time_start = time.time()
    description = "get_organelle_config.py " + get_versions() + " is used for setting up default GetOrganelle database."
    options = get_options(description=description)
    existing_seed_db, existing_label_db = get_current_db_versions(options.db_type,
                                                                  seq_db_path=_SEQ_DB_PATH,
                                                                  lbl_db_path=_LBL_DB_PATH,
                                                                  clean_mode=options.clean,
                                                                  check_hash=options.check)
    seed_version_f = os.path.join(_SEQ_DB_PATH, "VERSION")
    label_version_f = os.path.join(_LBL_DB_PATH, "VERSION")
    time_out = 100000

    # Case 1
    if options.clean:
        if options.db_type in ("seed", "both"):
            for rm_o_type in sorted(existing_seed_db):
                rm_files(_SEQ_DB_PATH, file_name_prefix=rm_o_type)
            if os.path.isfile(seed_version_f):
                os.remove(seed_version_f)
        if options.db_type in ("label", "both"):
            for rm_o_type in sorted(existing_label_db):
                rm_files(_LBL_DB_PATH, file_name_prefix=rm_o_type)
            if os.path.isfile(label_version_f):
                os.remove(label_version_f)

    # Case 2
    if options.rm_organelle_type:
        if options.db_type in ("seed", "both"):
            for rm_o_type in options.rm_organelle_type:
                if rm_o_type in existing_seed_db:
                    rm_files(_SEQ_DB_PATH, file_name_prefix=rm_o_type)
                    del existing_seed_db[rm_o_type]
                else:
                    sys.stdout.write("Warning: " + rm_o_type + " Seed Database not found!\n")
                write_version_file(version_dict=existing_seed_db, output_to_file=seed_version_f)
        if options.db_type in ("label", "both"):
            for rm_o_type in options.rm_organelle_type:
                if rm_o_type in existing_label_db:
                    rm_files(_LBL_DB_PATH, file_name_prefix=rm_o_type)
                    del existing_label_db[rm_o_type]
                else:
                    sys.stdout.write("Warning: " + rm_o_type + " Label Database not found!\n")
                write_version_file(version_dict=existing_label_db, output_to_file=label_version_f)

    # Case 3
    if options.update:
        if options.db_type in ("seed", "both"):
            for sub_o_type in ORGANELLE_TYPE_LIST:
                target_output = os.path.join(_SEQ_DB_PATH, sub_o_type + ".fasta")
                if sub_o_type not in existing_seed_db:
                    pass
                else:
                    if options.use_local:
                        update_to_fa = os.path.join(options.use_local, SEQ_NAME, sub_o_type + ".fasta")
                        if not os.path.exists(update_to_fa):
                            sys.stdout.write("Warning: " + update_to_fa + " not available!\n")
                        else:
                            new_hash_val = cal_f_sha256(update_to_fa)
                            if new_hash_val != existing_seed_db[sub_o_type]["sha256"]:
                                # for try_version in sorted(SEED_DB_HASH, reverse=True):
                                #     if sub_o_type in SEED_DB_HASH[try_version] and \
                                #             new_hash_val == SEED_DB_HASH[try_version][sub_o_type]["sha256"]:
                                #         existing_seed_db[sub_o_type] = {"version": try_version, "sha256": new_hash_val}
                                # else:
                                #     existing_seed_db[sub_o_type] = {"version": "customized", "sha256": new_hash_val}
                                existing_seed_db[sub_o_type] = \
                                    {"version": find_version(sub_o_type, new_hash_val, SEED_DB_HASH),
                                     "sha256": new_hash_val}
                                if os.path.realpath(os.path.split(update_to_fa)[0]) != os.path.realpath(_SEQ_DB_PATH):
                                    copy(update_to_fa, _SEQ_DB_PATH)
                                initialize_seed_database(which_bowtie2=options.which_bowtie2,
                                                         fasta_f=target_output, overwrite=True,
                                                         verbose=options.verbose)
                            else:  # match existed
                                # sys.stdout.write("The same " + sub_o_type + " Seed Database exists. Skipped.\n")
                                initialize_seed_database(which_bowtie2=options.which_bowtie2,
                                                         fasta_f=target_output, overwrite=False,
                                                         verbose=options.verbose)
                    else:
                        if existing_seed_db[sub_o_type]["version"] == options.db_version:
                            # sys.stdout.write("The same " + sub_o_type + " Seed Database exists. Skipped.\n")
                            initialize_seed_database(which_bowtie2=options.which_bowtie2,
                                                     fasta_f=target_output, overwrite=False,
                                                     verbose=options.verbose)
                        else:
                            these_urls = [sub_url.format(options.db_version, sub_o_type) for sub_url in seed_url_temp]
                            check_sha256 = SEED_DB_HASH[options.db_version][sub_o_type]["sha256"]
                            status = download_file_with_progress(
                                remote_url=these_urls[0], output_file=target_output, sha256_v=check_sha256,
                                timeout=time_out, alternative_url_list=these_urls[1:], verbose=options.verbose)
                            if not status["status"]:
                                sys.stdout.write(
                                    "Installing %s Seed Database failed: %s\n" % (sub_o_type, status["info"]))
                                continue
                            initialize_seed_database(which_bowtie2=options.which_bowtie2,
                                                     fasta_f=target_output, overwrite=True,
                                                     verbose=options.verbose)
                            existing_seed_db[sub_o_type] = {"version": options.db_version, "sha256": check_sha256}
                write_version_file(version_dict=existing_seed_db, output_to_file=seed_version_f)

        if options.db_type in ("label", "both"):
            for sub_o_type in ORGANELLE_TYPE_LIST:
                target_output = os.path.join(_LBL_DB_PATH, sub_o_type + ".fasta")
                if sub_o_type not in existing_label_db:
                    pass
                else:
                    if options.use_local:
                        update_to_fa = os.path.join(options.use_local, LBL_NAME, sub_o_type + ".fasta")
                        if not os.path.exists(update_to_fa):
                            sys.stdout.write("Warning: " + update_to_fa + " not available!\n")
                        else:
                            new_hash_val = cal_f_sha256(update_to_fa)
                            if new_hash_val != existing_label_db[sub_o_type]["sha256"]:  # match existed
                                # for try_version in sorted(LABEL_DB_HASH, reverse=True):
                                #     if sub_o_type in LABEL_DB_HASH[try_version] and \
                                #             new_hash_val == LABEL_DB_HASH[try_version][sub_o_type]["sha256"]:
                                #         existing_label_db[sub_o_type] = {"version": try_version,
                                #                                          "sha256": new_hash_val}
                                # else:
                                #     existing_label_db[sub_o_type] = {"version": "customized", "sha256": new_hash_val}
                                existing_label_db[sub_o_type] = \
                                    {"version": find_version(sub_o_type, new_hash_val, LABEL_DB_HASH),
                                     "sha256": new_hash_val}
                                if os.path.realpath(os.path.split(update_to_fa)[0]) != os.path.realpath(_LBL_DB_PATH):
                                    copy(update_to_fa, _LBL_DB_PATH)
                                initialize_notation_database(which_blast=options.which_blast,
                                                             fasta_f=target_output, overwrite=True,
                                                             verbose=options.verbose)
                            else:
                                # sys.stdout.write("The same " + sub_o_type + " Seed Database exists. Skipped.\n")
                                initialize_notation_database(which_blast=options.which_blast,
                                                             fasta_f=target_output, overwrite=False,
                                                             verbose=options.verbose)
                    else:
                        if existing_seed_db[sub_o_type]["version"] == options.db_version:
                            # sys.stdout.write("The same " + sub_o_type + " Seed Database exists. Skipped.\n")
                            initialize_notation_database(which_blast=options.which_blast,
                                                         fasta_f=target_output, overwrite=False,
                                                         verbose=options.verbose)
                        else:
                            these_urls = [sub_url.format(options.db_version, sub_o_type) for sub_url in label_url_temp]
                            check_sha256 = LABEL_DB_HASH[options.db_version][sub_o_type]["sha256"]
                            status = download_file_with_progress(
                                remote_url=these_urls[0], output_file=target_output, sha256_v=check_sha256,
                                timeout=time_out, alternative_url_list=these_urls[1:], verbose=options.verbose)
                            if not status["status"]:
                                sys.stdout.write(
                                    "Installing %s Label Database failed: %s\n" % (sub_o_type, status["info"]))
                                continue
                            initialize_notation_database(which_blast=options.which_blast,
                                                         fasta_f=target_output, overwrite=True, verbose=options.verbose)
                            existing_label_db[sub_o_type] = {"version": options.db_version, "sha256": check_sha256}
                write_version_file(version_dict=existing_label_db, output_to_file=label_version_f)

    # Case 4
    if options.add_organelle_type:
        if options.db_type in ("seed", "both"):
            for sub_o_type in options.add_organelle_type:
                target_output = os.path.join(_SEQ_DB_PATH, sub_o_type + ".fasta")
                if options.use_local:
                    update_to_fa = os.path.join(options.use_local, SEQ_NAME, sub_o_type + ".fasta")
                    if not os.path.exists(update_to_fa):
                        sys.stdout.write("Warning: " + update_to_fa + " not available!\n")
                    else:
                        new_hash_val = cal_f_sha256(update_to_fa)
                        # for try_version in sorted(SEED_DB_HASH, reverse=True):
                        #     if sub_o_type in SEED_DB_HASH[try_version] and \
                        #             new_hash_val == SEED_DB_HASH[try_version][sub_o_type]["sha256"]:
                        #         existing_seed_db[sub_o_type] = {"version": try_version, "sha256": new_hash_val}
                        # else:
                        #     existing_seed_db[sub_o_type] = {"version": "customized", "sha256": new_hash_val}
                        existing_seed_db[sub_o_type] = \
                            {"version": find_version(sub_o_type, new_hash_val, SEED_DB_HASH), "sha256": new_hash_val}
                        if os.path.realpath(os.path.split(update_to_fa)[0]) != os.path.realpath(_SEQ_DB_PATH):
                            copy(update_to_fa, _SEQ_DB_PATH)
                        initialize_seed_database(which_bowtie2=options.which_bowtie2,
                                                 fasta_f=target_output, overwrite=True,
                                                 verbose=options.verbose)
                else:
                    these_urls = [sub_url.format(options.db_version, sub_o_type) for sub_url in seed_url_temp]
                    check_sha256 = SEED_DB_HASH[options.db_version][sub_o_type]["sha256"]
                    status = download_file_with_progress(
                        remote_url=these_urls[0], output_file=target_output, sha256_v=check_sha256,
                        timeout=time_out, alternative_url_list=these_urls[1:], verbose=options.verbose)
                    if not status["status"]:
                        sys.stdout.write("Installing %s Seed Database failed: %s\n" % (sub_o_type, status["info"]))
                        continue
                    initialize_seed_database(which_bowtie2=options.which_bowtie2,
                                             fasta_f=target_output, overwrite=True,
                                             verbose=options.verbose)
                    existing_seed_db[sub_o_type] = {"version": options.db_version, "sha256": check_sha256}
                write_version_file(version_dict=existing_seed_db, output_to_file=seed_version_f)

        if options.db_type in ("label", "both"):
            for sub_o_type in options.add_organelle_type:
                target_output = os.path.join(_LBL_DB_PATH, sub_o_type + ".fasta")
                if options.use_local:
                    update_to_fa = os.path.join(options.use_local, LBL_NAME, sub_o_type + ".fasta")
                    if not os.path.exists(update_to_fa):
                        sys.stdout.write("Warning: " + update_to_fa + " not available!\n")
                    else:
                        new_hash_val = cal_f_sha256(update_to_fa)
                        # for try_version in sorted(LABEL_DB_HASH, reverse=True):
                        #     if sub_o_type in LABEL_DB_HASH[try_version] and \
                        #             new_hash_val == LABEL_DB_HASH[try_version][sub_o_type]["sha256"]:
                        #         existing_label_db[sub_o_type] = {"version": try_version,
                        #                                          "sha256": new_hash_val}
                        # else:
                        #     existing_label_db[sub_o_type] = {"version": "customized", "sha256": new_hash_val}
                        existing_label_db[sub_o_type] = \
                            {"version": find_version(sub_o_type, new_hash_val, LABEL_DB_HASH), "sha256": new_hash_val}
                        if os.path.realpath(os.path.split(update_to_fa)[0]) != os.path.realpath(_LBL_DB_PATH):
                            copy(update_to_fa, _LBL_DB_PATH)
                        initialize_notation_database(which_blast=options.which_blast,
                                                     fasta_f=target_output, overwrite=True, verbose=options.verbose)
                else:
                    these_urls = [sub_url.format(options.db_version, sub_o_type) for sub_url in label_url_temp]
                    check_sha256 = LABEL_DB_HASH[options.db_version][sub_o_type]["sha256"]
                    status = download_file_with_progress(
                        remote_url=these_urls[0], output_file=target_output, sha256_v=check_sha256,
                        timeout=time_out, alternative_url_list=these_urls[1:], verbose=options.verbose)
                    if not status["status"]:
                        sys.stdout.write("Installing %s Label Database failed: %s\n" % (sub_o_type, status["info"]))
                        continue
                    initialize_notation_database(which_blast=options.which_blast,
                                                 fasta_f=target_output, overwrite=True, verbose=options.verbose)
                    existing_label_db[sub_o_type] = {"version": options.db_version, "sha256": check_sha256}
                write_version_file(version_dict=existing_label_db, output_to_file=label_version_f)

    sys.stdout.write("\nTotal cost: %.2f s\n" % (time.time() - time_start))


if __name__ == '__main__':
    main()

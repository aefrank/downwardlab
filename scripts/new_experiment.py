#! /usr/bin/python3

import os, sys
import functools as ft
from shutil import rmtree

from scripts.lib.helpers import downwardlab_home, VirtualenvwrapperCLI, chmod_plus_x, add_abort_condition
from scripts.lib.prompt_utils import confirmation_prompt, PyPromptTextAttrs, FormattedText
########################################################################################################

def main(experiment_name):
    '''Create new experiment subdirectory and virtual environment.
    '''
    DL_HOME = downwardlab_home()
    create_experiment_subdir(experiment_name, DL_HOME)
    create_virtualenv(experiment_name, DL_HOME)
    

#################################### experiment directory setup ##################################

@add_abort_condition(lambda rval: rval is None)
def create_experiment_subdir(experiment_name, rootdir=None):
    '''Wraps mkexpdir function in abort condition.
    '''
    return mkexpdir(experiment_name=experiment_name, rootdir=rootdir)

def mkexpdir(experiment_name, rootdir=None):
    '''Create 'experiments/experiment_name' subdirectory.

    User will be prompted to confirm overwrite if experiment already exists.
    '''
    if not rootdir: rootdir = downwardlab_home()
    # create experiments subdirectory in rootdir unless rootdir is already called experiments
    if os.path.basename(rootdir)!="experiments":
        rootdir = os.path.join(rootdir,"experiments")
    # create subdir for this experiment 
    expdir = os.path.join(rootdir,experiment_name)
    try:
        os.makedirs(expdir)    
        return expdir
    except FileExistsError as e:
        if confirm_overwrite(experiment_name, expdir):
            print(f"Overwriting {expdir}/* ...")
            rmtree(expdir)
            os.makedirs(expdir)
            print(f"Done.")
            return expdir
        else:
            print(f"Directory {expdir} was not overwritten.")
            return None

def confirm_overwrite(experiment_name, expdir):
    '''Prompt the user to confirm intent to overwrite previous experiment of same name.
    '''
    from prompt_toolkit import print_formatted_text
    OVERWRITE_WARNING = generate_overwrite_warning(experiment_name, expdir)
    print_formatted_text(OVERWRITE_WARNING)
    return confirmation_prompt(
            prompt=f"Are you sure you want to continue with overwriting the existing data? ('yes'/'no') ",
            color="#ff0000",
            bold=True,
            invalid_response_warning="Invalid response. Please input 'yes' or 'no.'\n",
            max_attempts=3,
            affirmative=('yes',),
            negative=('no',)
        )

def generate_overwrite_warning(experiment_name, expdir):
    warningtxt   = PyPromptTextAttrs(color='#ffff00')
    warninglabel = PyPromptTextAttrs(color='#ff0000', bold=True)
    emphasized   = PyPromptTextAttrs(color='#ff0000', bold=True, underline=True)

    overwrite_warning = FormattedText([
        (warninglabel.to_style_str(), "[WARNING] "),
        (warningtxt.to_style_str(), f"Experiment directory {expdir}/ already exists. Creating a new experiment of this name will "),
        (emphasized.to_style_str(), f"permanently delete"),
        (warningtxt.to_style_str(), f" all existing data in {expdir}/ and "),
        (emphasized.to_style_str(), f"completely reset"),
        (warningtxt.to_style_str(), f" the '{experiment_name}' virtualenv.\n"),
    ])
    return overwrite_warning



###################################### Virtualenv Setup #######################################

def create_virtualenv(experiment_name, DL_HOME):
    create_exp_venv(experiment_name, DL_HOME)
    generate_virtualenvwrapper_hooks(experiment_name, DL_HOME)

def create_exp_venv(experiment_name, DL_HOME):
    '''Create virtualenv and install dependencies, and generate virtualenvwrapper hooks.
    '''
    VirtualenvwrapperCLI.mkvirtualenv(experiment_name, install=f"{DL_HOME}/requirements.txt")


def generate_virtualenvwrapper_hooks(experiment_name, DL_HOME):
    ## DownwardLab virtualenvwrapper hooks
    hookdir = ft.reduce(os.path.join, [os.getenv('WORKON_HOME'),experiment_name, 'bin'])
    hooks = ["preactivate", "postactivate", "predeactivate", "postdeactivate"]
    # Some of the hook files have to be made executable to be run instead of sourced
    EXECUTABLE = ["preactivate"]
    for hook in hooks:
        executable = hook in EXECUTABLE
        write_hook(hookdir, hook, DL_HOME, overwrite=True, executable=executable)


################## Create Virtualenv Hooks ##################

def write_hook(hookdir, hook, *args, overwrite=False, exec='/bin/bash', executable=False):
    hookfile = os.path.join(hookdir, hook)
    permission = 'w' if overwrite else 'a'
    with open(hookfile, permission) as f:
        if executable: # Add shebang
            f.write(f'#!{exec}\n\n')
        f.write(_generate_hook_text(hook, *args))
    if executable: 
        chmod_plus_x(hookfile)

def _generate_hook_text(hook, *hook_args):
    funcs = {
        'preactivate'    : preactivate_text,
        'postactivate'   : postactivate_text,
        'predeactivate'  : predeactivate_text,
        'postdeactivate' : postdeactivate_text
    }
    args = {
        'preactivate'    : None,
        'postactivate'   : 1,
        'predeactivate'  : None,
        'postdeactivate' : None
    }
    if args[hook] is not None:
        return funcs[hook](*hook_args)
    else:
        return funcs[hook]()


################## Hook File Data ##################

def preactivate_text():
    commands = [
        'export _BASEENV_PYTHONPATH="${PYTHONPATH}"',
        'unset PYTHONPATH',
    ]
    string =  '\n'.join(commands)
    return string


def postactivate_text(dlab_rootdir):
    commands = [
        'export _BASEENV_PROJECT_HOME=${PROJECT_HOME}',
        f'export PROJECT_HOME={dlab_rootdir}',  
        '\n',
        'export _BASEENV_PATH=${PATH}',
        'export PATH=${PROJECT_HOME}/VAL:${PATH}',
        '\n',
        'export DOWNWARD_BENCHMARKS=${PROJECT_HOME}/benchmarks' \
        'export DOWNWARD_REPO=${PROJECT_HOME}/fast-downward' \
    ]
    
    string =  '\n'.join(commands)
    return string

def predeactivate_text():
    string = '\nexport PROJECT_HOME=${_BASEENV_PROJECT_HOME}'  \
             '\nunset _BASEENV_PROJECT_HOME'         \
             '\n' \
             '\nexport PATH=$_BASEENV_PATH'   \
             '\nunset _BASEENV_PATH' \
             '\n' \
             '\nunset DOWNWARD_BENCHMARKS' \
             '\nunset DOWNWARD_REPO' \
             '\n'
    return string

def postdeactivate_text():
    commands = [
        'export PYTHONPATH="${_BASEENV_PYTHONPATH}"',
        'unset _BASEENV_PYTHONPATH'
    ]
    string =  '\n'.join(commands)
    return string




#################################################### run main ##########################################################

if __name__ == "__main__":
    main(*sys.argv[1:])
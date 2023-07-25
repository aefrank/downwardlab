#! /usr/bin/python3

import os, sys, shutil
import functools as ft

from scripts.lib.helpers import VirtualenvwrapperCLI, downwardlab_home
from lib.prompt_utils import confirmation_prompt

def delete_experiment(experiment_name):
    CWD = os.getcwd() 
    DL_HOME = downwardlab_home()
    exp_dir = ft.reduce(os.path.join, [DL_HOME,"experiments",experiment_name])

    if not os.path.isdir(exp_dir):
        raise FileNotFoundError(f"No experiment directory '{exp_dir}' exists.") 
    
    if confirmation_prompt(
            prompt=f"Are you sure you want to delete all contents of {exp_dir} and the '{experiment_name}' virtualenv? (yes/no) ", 
            color="#ff0000",
            bold=True,
            invalid_response_warning="Invalid response. Please input 'yes' or 'no.'\n",
            max_attempts=3,
            affirmative=('yes',),
            negative=('no',)
        ):
        _rmexpdir(exp_dir)
        VirtualenvwrapperCLI.rmvirtualenv(experiment_name)
    else:
        print("Aborting...")


def _rmexpdir(experiment_dir):
    ''' Delete experiment directory
    '''
    print(f"Deleting {experiment_dir}...")
    shutil.rmtree(experiment_dir, ignore_errors = True)



if __name__ == "__main__":
   delete_experiment(*sys.argv[1:])